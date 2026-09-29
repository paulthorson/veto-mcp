#!/usr/bin/env python3
"""Automated UAT acceptance journey for Initiative 10 (Packaging, backup & secure sync).

The user journey: "A user installs Veto, and later their laptop dies - they
reinstall, restore the encrypted backup, and lose nothing the backup covers."

Scoping note (Rule 1, blind QA KICK_BACK 2026-09-16): the backup covers
STABLE SCHEMAS ONLY - files outside the named stable schemas (the legacy
applications.json, scratch files) are listed in the drill report's
``excluded`` field and are NOT covered by a PASS. The Q3 exit gate's
broader gap-audit wording ("any record present before backup and absent
after restore is an unrecoverable record gap") is NOT claimed by this
journey; whether stable-schema-only coverage satisfies the gate still
needs the operator's explicit sign-off.

Traceability note: the repo carries roadmap epics but NO per-story
acceptance criteria, so no story-level criteria are invented here. Every
assertion traces to the epic text, the Proof of value ("install, upgrade,
back up, restore, and remove Veto without an unrecoverable capture gap or
unintended exposure"), or the Q3 exit gate ("install, migration, backup,
and restore with 100% checksum match and no unrecoverable record gap").
The acceptance source is named per method in EPIC_MAP.

All entrypoints are the real shipped ones (same as the E2E suite), run
hermetically under a per-test temp dir with a fake HOME. Nothing touches
the real home directory or the repo tree. ``setup_dependencies`` is never
run here (it downloads packages and takes minutes).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from tests.uat.harness import JourneyCase
from initiatives.i10 import backup, channels, installer, schema_migrate, sync

REPO = Path(__file__).resolve().parent.parent.parent

BACKUP_PASSPHRASE = "uat-backup-passphrase-32-chars!!"
SYNC_PASSPHRASE = "uat-sync-passphrase-long-enough"

EPIC_MAP = {
    "test_e1_install_uninstall_keeps_data_and_purge_needs_exact_confirmation": (
        "E1", "One-command installer", "Roadmap i10 E1 epic text + Proof of value",
    ),
    "test_e2_migration_stamps_idempotent_and_rolls_back": (
        "E2", "Schema migrations", "Roadmap i10 E2 epic text + Q3 exit gate",
    ),
    "test_e3_disaster_recovery_drill_passes_and_bundle_is_encrypted": (
        "E3", "Backup and restore", "Roadmap i10 E3 epic text + Q3 exit gate",
    ),
    "test_e4_sync_is_opt_in_and_two_devices_converge": (
        "E4", "Optional device sync",
        "Roadmap i10 E4 epic text + Proof of value (no unintended exposure)",
    ),
    "test_e5_pwa_installs_and_reads_offline": (
        "E5", "Progressive web app", "Roadmap i10 E5 epic text",
    ),
    "test_e6_release_channel_check_and_promote_never_touches_repo": (
        "E6", "Release channels", "Roadmap i10 E6 epic text",
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _event(i: int, device: str = "a") -> dict:
    """One synthetic job-application outcome record."""
    return {
        "event_id": f"uat-ev-{device}-{i:03d}",
        "application_id": f"uat-job-{i:03d}",
        "event_type": "applied",
        "occurred_at": "2026-09-01T10:00:00",
        "source": "synthetic-fixture",
        "role": "UAT Engineer",
        "provenance": {"actor": "test"},
        "schema_version": "outcome-min-v0",
        "recorded_at": "2026-09-01T10:00:01",
    }


def _fixture_data_dir(root: Path, name: str = "data", n_events: int = 4) -> Path:
    """A realistic Veto data dir: stamped profile + valid outcome records."""
    d = root / name
    (d / "profiles").mkdir(parents=True)
    (d / "profiles" / "profile.json").write_text(
        json.dumps({"schema_version": "profile-v1", "full_name": "UAT User"}),
        encoding="utf-8",
    )
    (d / "outcomes.jsonl").write_text(
        "\n".join(json.dumps(_event(i)) for i in range(n_events)) + "\n",
        encoding="utf-8",
    )
    return d


class Initiative10UATJourney(JourneyCase):
    EPIC_MAP = EPIC_MAP

    def setUp(self) -> None:
        super().setUp()
        self.root = self.workdir
        self.fake_home = self.root / "home"
        self.fake_home.mkdir()
        self.install_root = self.root / "iroot"
        self.record = self.install_root / "install.json"
        patchers = [
            mock.patch.object(Path, "home", return_value=self.fake_home),
            mock.patch.object(installer, "INSTALL_ROOT", self.install_root),
            mock.patch.object(installer, "INSTALL_RECORD", self.record),
            mock.patch.dict(os.environ),
        ]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)
        os.environ.pop("VETO_BACKUP_PASSPHRASE", None)
        os.environ.pop("VETO_SYNC_PASSPHRASE", None)

    def _install(self):
        """Run the real installer against the fake HOME; return the answers."""
        answers = installer.OnboardingAnswers(
            full_name="UAT User",
            email="uat@example.com",
            data_dir=str(self.root / "data"),
            sync_opt_in=False,
            channel="stable",
        )
        installer.write_install_record(answers, install_root=self.install_root)
        installer.install_shim(install_root=self.install_root)
        return answers

    # ------------------------------------------------------------------
    # E1: One-command installer
    # ------------------------------------------------------------------
    def test_e1_install_uninstall_keeps_data_and_purge_needs_exact_confirmation(self):
        """Installing Veto then removing it keeps your saved data; wiping data needs an exact typed confirmation."""
        # The sandbox tmpfs sits below the installer's real 500 MB disk
        # minimum, so only the threshold is lowered for this hermetic run -
        # the disk check itself still executes.
        with mock.patch.object(installer, "MIN_DISK_BYTES", 1):
            checks = installer.check_environment()
            ok = installer.environment_ok(checks)
        names = {c.name for c in checks}
        self.assertTrue({"python", "pip", "disk", "install-dir"} <= names,
                        "installer must check python, pip, disk and install dir")
        self.assertTrue(ok, [c for c in checks if not c.ok])

        answers = self._install()
        data_dir = Path(answers.data_dir)
        record = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(record["channel"], "stable")
        self.assertFalse(record["sync_opt_in"])  # local-only unless opted in
        self.assertEqual(stat.S_IMODE(self.record.stat().st_mode), 0o600)
        shim = self.fake_home / ".local" / "bin" / "veto"
        self.assertTrue(shim.is_file() and os.access(shim, os.X_OK))

        # The user saves something, then removes Veto: the data must survive.
        (data_dir / "my-job-search.txt").write_text("SYNTHETIC - keep me", encoding="utf-8")
        result = installer.uninstall(install_root=self.install_root)
        self.assertFalse(shim.exists(), "launcher shim must be gone")
        self.assertFalse(self.record.exists(), "install record must be gone")
        self.assertTrue((data_dir / "my-job-search.txt").is_file(),
                        "uninstall must not touch saved data")
        self.assertIn(str(shim), result["removed"])

        # A mistyped purge confirmation refuses first - nothing is deleted.
        answers2 = self._install()
        data_dir = Path(answers2.data_dir)
        with self.assertRaises(ValueError):
            installer.uninstall(
                install_root=self.install_root,
                purge_data=True,
                confirm="yes please delete",
                no_backup_ack=True,
            )
        self.assertTrue(data_dir.is_dir(), "refused purge must leave data intact")
        self.assertTrue(self.record.exists(), "refused purge must leave install intact")

        # A purge with the EXACT confirmation succeeds — on a separate temp
        # install so the refusal path above stays intact.
        doom_dir = self.root / "doom-data"
        doom_answers = installer.OnboardingAnswers(
            full_name="UAT User",
            email="uat@example.com",
            data_dir=str(doom_dir),
            sync_opt_in=False,
            channel="stable",
        )
        installer.write_install_record(doom_answers, install_root=self.install_root)
        installer.install_shim(install_root=self.install_root)
        (doom_dir / "doomed.txt").write_text("SYNTHETIC - purge me", encoding="utf-8")
        target = doom_dir.resolve()
        result = installer.uninstall(
            install_root=self.install_root,
            purge_data=True,
            confirm=f"PURGE MY DATA {target}",
            no_backup_ack=True,
        )
        self.assertFalse(doom_dir.exists(),
                         "exact-confirmation purge must delete the data dir")
        self.assertIn(str(target), result["purged_data"])

        # The passphrase -> pre-purge-backup branch: with
        # $VETO_BACKUP_PASSPHRASE set and the exact confirmation (and NO
        # no_backup_ack), purge takes an ENCRYPTED backup of the data dir
        # BEFORE deleting anything, and the backup restores afterwards.
        backup_dir = self.root / "backup-data"
        (backup_dir / "profiles").mkdir(parents=True)
        (backup_dir / "profiles" / "profile.json").write_text(
            json.dumps({"schema_version": "profile-v1", "full_name": "UAT User"}),
            encoding="utf-8",
        )
        (backup_dir / "outcomes.jsonl").write_text(
            json.dumps(_event(0)) + "\n", encoding="utf-8")
        backup_answers = installer.OnboardingAnswers(
            full_name="UAT User",
            email="uat@example.com",
            data_dir=str(backup_dir),
            sync_opt_in=False,
            channel="stable",
        )
        installer.write_install_record(backup_answers, install_root=self.install_root)
        installer.install_shim(install_root=self.install_root)
        backup_target = backup_dir.resolve()
        with mock.patch.dict(os.environ, {"VETO_BACKUP_PASSPHRASE": BACKUP_PASSPHRASE}):
            result = installer.uninstall(
                install_root=self.install_root,
                purge_data=True,
                confirm=f"PURGE MY DATA {backup_target}",
            )
        pre = result["pre_purge_backup"]
        self.assertIsNotNone(
            pre, "purge with a passphrase must take a pre-purge backup")
        pre_path = Path(pre)
        self.assertTrue(pre_path.is_file(), "pre-purge backup file must exist")
        self.assertEqual(pre_path.parent, self.install_root / "backups",
                         "pre-purge backup lives under <install-root>/backups/")
        self.assertFalse(backup_dir.exists(),
                         "purge must still delete the data dir")
        # The pre-purge backup restores: the covered records survive the
        # purge. (Stable schemas only - scratch files are not covered; see
        # the E3 scoping note.)
        restored = self.root / "restored-after-purge"
        backup.restore(pre_path, BACKUP_PASSPHRASE, restored)
        restored_profile = json.loads(
            (restored / "profiles" / "profile.json").read_text(encoding="utf-8"))
        self.assertEqual(restored_profile["full_name"], "UAT User")
        self.assertIn("uat-ev-a-000",
                      (restored / "outcomes.jsonl").read_text(encoding="utf-8"),
                      "the pre-purge backup must restore the covered records")

    # ------------------------------------------------------------------
    # E2: Schema migrations
    # ------------------------------------------------------------------
    def test_e2_migration_stamps_idempotent_and_rolls_back(self):
        """Upgrading Veto's data format stamps the new version, running it again changes nothing, and the upgrade can be undone."""
        data = self.root / "data"
        (data / "profiles").mkdir(parents=True)
        # A profile written before Veto stamped schema versions: no marker.
        (data / "profiles" / "legacy.json").write_text(
            json.dumps({"full_name": "Legacy User", "email": "legacy@example.com"}),
            encoding="utf-8",
        )

        # Migrate: the legacy profile is stamped, and the journal records it.
        self.assertEqual(
            schema_migrate.main(["--data-dir", str(data), "migrate"]), 0)
        stamped = json.loads(
            (data / "profiles" / "legacy.json").read_text(encoding="utf-8"))
        self.assertEqual(stamped["schema_version"], "profile-v1")
        self.assertEqual(stamped["full_name"], "Legacy User")  # data preserved
        marker = json.loads(
            (data / "_schema_versions.json").read_text(encoding="utf-8"))
        self.assertIn("profile", marker)
        self.assertIn("0001_stamp_schema_versions", schema_migrate.applied_ids(data))

        # A second upgrade run changes nothing (idempotent).
        before = (data / "profiles" / "legacy.json").read_text(encoding="utf-8")
        self.assertEqual(
            schema_migrate.main(["--data-dir", str(data), "migrate"]), 0)
        self.assertEqual(
            (data / "profiles" / "legacy.json").read_text(encoding="utf-8"),
            before, "second migration run must not change the data")
        self.assertEqual(
            schema_migrate.main(["--data-dir", str(data), "check"]), 0)

        # Rollback undoes the migration on disk: the stamp is stripped
        # from the profile, the version marker is removed, and the
        # journal records the undo.
        self.assertEqual(
            schema_migrate.main(
                ["--data-dir", str(data), "rollback", "0001_stamp_schema_versions"]
            ), 0)
        self.assertNotIn("0001_stamp_schema_versions", schema_migrate.applied_ids(data))
        unmigrated = json.loads(
            (data / "profiles" / "legacy.json").read_text(encoding="utf-8"))
        self.assertNotIn("schema_version", unmigrated,
                         "rollback must strip the stamp forward added")
        self.assertEqual(unmigrated["full_name"], "Legacy User")
        self.assertFalse((data / "_schema_versions.json").exists(),
                         "rollback must remove the version marker")
        journal = (data / "_migrations.jsonl").read_text(encoding="utf-8")
        self.assertIn("rolled_back", journal)
        # And the migration can be applied again after the rollback.
        self.assertEqual(
            schema_migrate.main(["--data-dir", str(data), "migrate"]), 0)
        self.assertIn("0001_stamp_schema_versions", schema_migrate.applied_ids(data))

    # ------------------------------------------------------------------
    # E3: Backup and restore (the disaster-recovery drill)
    # ------------------------------------------------------------------
    def test_e3_disaster_recovery_drill_passes_and_bundle_is_encrypted(self):
        """Losing your laptop and restoring the encrypted backup brings back every record the backup covers exactly - with 100% checksum match and no missing records among the covered schemas."""
        with mock.patch.dict(os.environ, {"VETO_BACKUP_PASSPHRASE": BACKUP_PASSPHRASE}):
            data = _fixture_data_dir(self.root, n_events=6)
            live_profile = (data / "profiles" / "profile.json").read_text(encoding="utf-8")
            # Files the backup does NOT cover: the legacy applications
            # store and a scratch file. They must show up in
            # report.excluded - the drill's coverage is stable schemas
            # only, and a PASS must never hide that boundary.
            (data / "applications.json").write_text(
                json.dumps([{"id": "legacy-app-1", "role": "SYNTHETIC legacy"}]),
                encoding="utf-8",
            )
            (data / "notes.txt").write_text("SYNTHETIC scratch note\n",
                                            encoding="utf-8")

            # The shipped disaster-recovery drill: back up, restore into a
            # scratch dir, verify 100% checksums, confirm zero record gap.
            report = backup.drill(data, BACKUP_PASSPHRASE)
            self.assertTrue(report.ok, report.detail)
            self.assertEqual(report.checksum_match_pct, 100.0,
                             "Q3 exit gate: 100% checksum match")
            # Scoping decision (needs operator sign-off): the drill's PASS
            # and its zero gap cover stable schemas ONLY. The Q3 exit
            # gate's broader gap-audit wording ("any record present before
            # backup and absent after restore") is NOT claimed here - the
            # excluded files below are the explicit, asserted boundary.
            self.assertIn("applications.json", report.excluded,
                          "legacy applications store must be an asserted exclusion")
            self.assertIn("notes.txt", report.excluded,
                          "scratch files must be an asserted exclusion")
            gaps = {k: v for k, v in report.record_gap.items()} if isinstance(
                report.record_gap, dict) else {}
            self.assertTrue(all(v == 0 for v in gaps.values()),
                            f"no unrecoverable record gap allowed among covered schemas: {gaps}")
            # The live store is never touched by the drill.
            self.assertEqual(
                (data / "profiles" / "profile.json").read_text(encoding="utf-8"),
                live_profile)

            # The backup bundle itself is encrypted: no plaintext of the
            # fixture data is readable without the passphrase.
            archive = self.root / "backup.vetobackup"
            self.assertEqual(
                backup.main(["create", "--data-dir", str(data),
                             "--out", str(archive)]), 0)
            raw = archive.read_bytes()
            self.assertNotIn(b"UAT User", raw, "name must not be readable in the bundle")
            self.assertNotIn(b"uat-ev-a-000", raw,
                             "record ids must not be readable in the bundle")
            self.assertNotIn(b"uat@example", raw)
            self.assertEqual(backup.main(["verify", "--in", str(archive)]), 0)

    # ------------------------------------------------------------------
    # E4: Optional device sync
    # ------------------------------------------------------------------
    def test_e4_sync_is_opt_in_and_two_devices_converge(self):
        """Syncing between devices is off unless you turn it on; two devices end up with the same records while the relay only ever sees scrambled data."""
        with mock.patch.dict(os.environ, {sync.PASSPHRASE_ENV_VAR: SYNC_PASSPHRASE}):
            vault = self.root / "vault"

            def device(name: str, n: int) -> Path:
                d = self.root / f"device-{name}"
                (d / "profiles").mkdir(parents=True)
                (d / "profiles" / "profile.json").write_text(
                    json.dumps({"schema_version": "profile-v1",
                                "updated_at": "2026-09-01T00:00:00"}),
                    encoding="utf-8")
                (d / "outcomes.jsonl").write_text(
                    "\n".join(json.dumps(_event(i, name)) for i in range(n)) + "\n",
                    encoding="utf-8")
                return d

            da = device("a", 3)
            db = device("b", 4)

            # Sync is off by default - nothing leaves the device until the
            # user explicitly opts in.
            self.assertFalse(sync.status(da)["enabled"],
                             "sync must be off unless explicitly enabled")
            self.assertEqual(sync.main(["--data-dir", str(da), "status"]), 0)

            # Explicit opt-in: first device creates the group, second joins.
            self.assertEqual(
                sync.main(["--data-dir", str(da), "enable",
                           "--vault", str(vault), "--init"]), 0)
            self.assertTrue(sync.status(da)["enabled"])
            self.assertEqual(
                sync.main(["--data-dir", str(db), "enable",
                           "--vault", str(vault), "--join"]), 0)

            # Sync rounds until both devices hold the union: 3 + 4 = 7
            # records, no duplicates, none lost.
            for _ in range(3):
                self.assertEqual(sync.main(["--data-dir", str(da), "sync"]), 0)
                self.assertEqual(sync.main(["--data-dir", str(db), "sync"]), 0)
            for d in (da, db):
                ids = {json.loads(line)["event_id"]
                       for line in (d / "outcomes.jsonl").read_text(
                           encoding="utf-8").splitlines() if line.strip()}
                self.assertEqual(len(ids), 7,
                                 "every record must reach every device exactly once")

            # CONFLICT ROUND: both devices edit the same record (divergent
            # content, same event_id) AND diverge the profile with EQUAL
            # updated_at timestamps. Sync must converge deterministically -
            # the equal-timestamp profile case used to flip-flop forever
            # (each round replaced the local profile with the peer's); the
            # tiebreak now picks one winner on both sides.
            conflict_ts = "2026-09-05T00:00:00"  # newer than every envelope so far
            # Written with the product's own profile serialization
            # (indent=2) and the envelope's canonical key order
            # (Envelope.to_bytes uses sort_keys=True), same on both sides.
            (da / "profiles" / "profile.json").write_text(
                json.dumps({"full_name": "Alice",
                            "schema_version": "profile-v1",
                            "updated_at": conflict_ts}, indent=2) + "\n",
                encoding="utf-8")
            (db / "profiles" / "profile.json").write_text(
                json.dumps({"full_name": "Bob",
                            "schema_version": "profile-v1",
                            "updated_at": conflict_ts}, indent=2) + "\n",
                encoding="utf-8")
            conflict_a = _event(900, "a")
            conflict_a["event_id"] = "uat-ev-conflict-000"
            conflict_a["role"] = "Conflict role A"
            conflict_a["recorded_at"] = "2026-09-02T10:00:01"  # newer wins
            conflict_b = _event(900, "b")
            conflict_b["event_id"] = "uat-ev-conflict-000"
            conflict_b["role"] = "Conflict role B"
            conflict_b["recorded_at"] = "2026-09-02T10:00:00"
            with (da / "outcomes.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(conflict_a) + "\n")
            with (db / "outcomes.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(conflict_b) + "\n")
            for _ in range(3):
                self.assertEqual(sync.main(["--data-dir", str(da), "sync"]), 0)
                self.assertEqual(sync.main(["--data-dir", str(db), "sync"]), 0)

            # The conflicting record converges to one deterministic winner
            # (newer recorded_at), exactly once, on both devices.
            def _canonical_records(d: Path) -> list[str]:
                return sorted(
                    json.dumps(json.loads(line), sort_keys=True)
                    for line in (d / "outcomes.jsonl").read_text(
                        encoding="utf-8").splitlines() if line.strip())
            ra, rb = _canonical_records(da), _canonical_records(db)
            self.assertEqual(ra, rb,
                             "both devices must converge to the same records")
            self.assertEqual(len(ra), 8, "7 union records + 1 conflict, no duplicates")
            winners = [json.loads(r) for r in ra
                       if json.loads(r)["event_id"] == "uat-ev-conflict-000"]
            self.assertEqual(len(winners), 1, "conflict resolves to exactly one record")
            self.assertEqual(winners[0]["role"], "Conflict role A",
                             "the newer recorded_at wins the record conflict")

            # The equal-timestamp profiles converge to IDENTICAL bytes on
            # both devices and stay there across another sync round - no
            # flip-flopping.
            pa = (da / "profiles" / "profile.json").read_bytes()
            pb = (db / "profiles" / "profile.json").read_bytes()
            self.assertEqual(pa, pb,
                             "equal-timestamp profiles must converge to identical bytes")
            self.assertEqual(json.loads(pa.decode("utf-8"))["updated_at"], conflict_ts)
            for _ in range(2):
                self.assertEqual(sync.main(["--data-dir", str(da), "sync"]), 0)
                self.assertEqual(sync.main(["--data-dir", str(db), "sync"]), 0)
            self.assertEqual((da / "profiles" / "profile.json").read_bytes(), pa,
                             "converged profile must not change on the next round")
            self.assertEqual((db / "profiles" / "profile.json").read_bytes(), pa,
                             "converged profile must not change on the next round")

            # The vault (shared folder relay) sees ciphertext only.
            vault_text = " ".join(
                p.read_text(encoding="utf-8", errors="replace")
                for p in vault.rglob("*") if p.is_file())
            self.assertNotIn("uat-ev-a-000", vault_text)
            self.assertNotIn("uat-ev-b-000", vault_text)
            self.assertNotIn("uat-ev-conflict-000", vault_text)
            self.assertNotIn("Conflict role A", vault_text)

            # Opting back out returns the device to local-only.
            self.assertEqual(sync.main(["--data-dir", str(da), "disable"]), 0)
            self.assertFalse(sync.status(da)["enabled"])

    # ------------------------------------------------------------------
    # E5: Progressive web app
    # ------------------------------------------------------------------
    def test_e5_pwa_installs_and_reads_offline(self):
        """The phone web app still shows your saved pages with no network."""
        # Scoping note (blind QA KICK_BACK 2026-09-16): "installs to your
        # home screen" was dropped from this claim - the node harness runs
        # against stubbed platform globals, so it cannot exercise a real
        # installability flow (manifest install, beforeinstallprompt). The
        # offline half below IS genuinely tested.
        if not shutil.which("node"):
            self.skipTest("node not available - cannot run the JS runtime PWA harness")
        harness = REPO / "tests" / "i10_pwa_harness.mjs"
        self.assertTrue(harness.is_file(), "the PWA harness must exist in the repo")
        proc = subprocess.run(
            [shutil.which("node"), str(harness)],
            capture_output=True, text=True, timeout=120, cwd=str(REPO))
        self.assertEqual(
            proc.returncode, 0,
            f"PWA installability/offline harness failed:\n{proc.stdout}\n{proc.stderr}")

    # ------------------------------------------------------------------
    # E6: Release channels
    # ------------------------------------------------------------------
    def test_e6_release_channel_check_and_promote_never_touches_repo(self):
        """You can check a new release against your data and promote it, while the repo's own release files stay untouched."""
        data = _fixture_data_dir(self.root, n_events=2)

        channels_dir = REPO / "initiatives" / "i10" / "channels"
        repo_stable = channels_dir / "stable.json"
        repo_preview = channels_dir / "preview.json"
        before = {p: _sha256(p) for p in (repo_stable, repo_preview)
                  if p.is_file()}

        # Promote's manifest writes are redirected to a temp dir: the repo's
        # release files must never be mutated by a promotion.
        manifest_dir = self.root / "manifests"
        manifest_dir.mkdir()
        shutil.copy(repo_preview, manifest_dir / "preview.json")
        with mock.patch.object(
                channels, "_manifest_path",
                lambda channel: manifest_dir / f"{channel}.json"):
            self.assertEqual(channels.main(["check", "--data-dir", str(data)]), 0)
            self.assertTrue(channels.compatibility_ok(
                channels.check_compatibility(data)))
            self.assertEqual(
                channels.main(["promote", "--data-dir", str(data),
                               "--notes", "uat promote"]), 0)
            stable = json.loads(
                (manifest_dir / "stable.json").read_text(encoding="utf-8"))
            preview = json.loads(
                (manifest_dir / "preview.json").read_text(encoding="utf-8"))
            self.assertEqual(stable["channel"], "stable")
            self.assertEqual(stable["version"], preview["version"])
            self.assertEqual(stable["notes"], "uat promote")

        for path, digest in before.items():
            self.assertEqual(_sha256(path), digest,
                             f"promote must never mutate the repo's {path.name}")


if __name__ == "__main__":
    unittest.main()
