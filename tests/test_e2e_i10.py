#!/usr/bin/env python3
"""E2E retro-validation for Initiative 10 (Packaging & recovery).

Standing rule: nothing ships without E2E. This module exercises the
shipped i10 features through their REAL entrypoints against hermetic temp
dirs (no synthetic installs, no mocked subprocesses for the flows below):

1. Installer lifecycle: the REAL ``check_environment``,
   ``write_install_record``, ``install_shim``, and ``uninstall`` against a
   temp HOME. Asserts the installed tree (record, sentinel, starter
   profile, launcher shim) and the uninstall semantics (data kept unless
   purged with the exact typed confirmation; purge validates first).
   (``setup_dependencies`` — venv creation + pip install — is intentionally
   not run here: it downloads packages and takes minutes. The existing
   unit tests pin its command construction with mocked subprocess.)
2. Schema migration: the REAL ``schema_migrate.main`` CLI against a fixture
   data dir holding a legacy (unmarked) profile. Asserts stamping,
   marker file, journal record, and idempotent re-runs.
3. Backup: the REAL ``backup.main`` CLI (create / verify / restore) with the
   passphrase from ``VETO_BACKUP_PASSPHRASE`` (never argv). Asserts
   byte-level restore fidelity.
4. Sync: the REAL ``sync.main`` CLI (enable --init / --join / sync /
   status / disable) with the passphrase from ``VETO_SYNC_PASSPHRASE``.
   Two devices + one vault dir converge with no record loss.
5. Release channels: the REAL ``channels.main`` CLI (check / promote)
   against a fixture data dir. The promote's manifest write is redirected
   to a temp dir (``_manifest_path`` patched) so the repo's stable.json is
   never mutated by tests.
6. PWA: the REAL node harness (tests/i10_pwa_harness.mjs) via subprocess
   when node is available.

Hermetic: temp dirs everywhere, env vars scoped with mock.patch.dict,
cleanup via addCleanup.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from initiatives.i10 import backup, channels, installer, schema_migrate, sync

REPO_ROOT = Path(__file__).resolve().parent.parent

BACKUP_PASSPHRASE = "e2e-backup-passphrase-32-chars!!"
SYNC_PASSPHRASE = "e2e-sync-passphrase-long-enough"


def _event(i: int, device: str = "a") -> dict:
    return {
        "event_id": f"e2e-ev-{device}-{i:03d}",
        "application_id": f"e2e-job-{i:03d}",
        "event_type": "applied",
        "occurred_at": "2026-09-01T10:00:00",
        "source": "synthetic-fixture",
        "role": "E2E Engineer",
        "provenance": {"actor": "test"},
        "schema_version": "outcome-min-v0",
        "recorded_at": "2026-09-01T10:00:01",
    }


def _fixture_data_dir(root: Path, name: str = "data", n_events: int = 3) -> Path:
    """A realistic data dir: stamped profile + valid outcome events."""
    d = root / name
    (d / "profiles").mkdir(parents=True)
    (d / "profiles" / "profile.json").write_text(
        json.dumps({"schema_version": "profile-v1", "full_name": "E2E User"}),
        encoding="utf-8",
    )
    (d / "outcomes.jsonl").write_text(
        "\n".join(json.dumps(_event(i)) for i in range(n_events)) + "\n",
        encoding="utf-8",
    )
    return d


def _sha256_tree(root: Path) -> dict[str, str]:
    """Map of relative path -> sha256 for every file under root."""
    out = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.sha256(
                p.read_bytes()
            ).hexdigest()
    return out


# ---------------------------------------------------------------------------
# 1. Installer lifecycle (real functions, temp HOME)
# ---------------------------------------------------------------------------


class InstallerLifecycleE2ETests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.fake_home = root / "home"
        self.fake_home.mkdir()
        self.install_root = root / "iroot"
        self.record = self.install_root / "install.json"
        patchers = [
            mock.patch.object(Path, "home", return_value=self.fake_home),
            mock.patch.object(installer, "INSTALL_RECORD", self.record),
            mock.patch.dict(os.environ),
        ]
        for p in patchers:
            p.start()
            self.addCleanup(p.stop)
        os.environ.pop("VETO_BACKUP_PASSPHRASE", None)

    def _install(self):
        answers = installer.OnboardingAnswers(
            full_name="E2E User",
            email="e2e@example.com",
            data_dir=str(Path(self.tmp.name) / "data"),
            sync_opt_in=False,
            channel="stable",
        )
        installer.write_install_record(answers, install_root=self.install_root)
        installer.install_shim(install_root=self.install_root)
        return answers

    def test_environment_checks_pass_for_real(self):
        # The sandbox tmpfs has < 500 MB free, below the installer's real
        # minimum; lower only the threshold for this hermetic run so the
        # disk check itself still executes. Production is untouched.
        with mock.patch.object(installer, "MIN_DISK_BYTES", 1):
            checks = installer.check_environment()
            ok = installer.environment_ok(checks)
            failed = [c for c in checks if not c.ok]
        names = {c.name for c in checks}
        self.assertTrue({"python", "pip", "disk", "install-dir"} <= names)
        self.assertTrue(ok, failed)

    def test_install_writes_real_installed_tree(self):
        answers = self._install()
        data_dir = Path(answers.data_dir)
        # Install record: real JSON with the data dir, kept private.
        record = json.loads(self.record.read_text(encoding="utf-8"))
        self.assertEqual(record["data_dir"], str(data_dir))
        self.assertEqual(record["channel"], "stable")
        self.assertFalse(record["sync_opt_in"])  # local-only default
        self.assertEqual(stat.S_IMODE(self.record.stat().st_mode), 0o600)
        # Data dir sentinel: proves the dir is Veto-managed (purge guard).
        sentinel = data_dir / installer.DATA_SENTINEL
        self.assertTrue(sentinel.is_file())
        # Starter profile stamped profile-v1 so backup/sync/compat accept it.
        profile = json.loads(
            (data_dir / "profiles" / "profile.json").read_text(encoding="utf-8")
        )
        self.assertEqual(profile["schema_version"], "profile-v1")
        self.assertEqual(profile["full_name"], "E2E User")
        # Launcher shim: executable, installer-marked, points at the venv.
        shim = self.fake_home / ".local" / "bin" / "veto"
        self.assertTrue(shim.is_file())
        self.assertTrue(os.access(shim, os.X_OK))
        self.assertIn("written by the installer", shim.read_text(encoding="utf-8"))

    def test_uninstall_removes_install_but_keeps_data(self):
        answers = self._install()
        data_dir = Path(answers.data_dir)
        (data_dir / "user-data.txt").write_text("keep me", encoding="utf-8")
        result = installer.uninstall(install_root=self.install_root)
        shim = self.fake_home / ".local" / "bin" / "veto"
        self.assertFalse(shim.exists())
        self.assertFalse(self.record.exists())
        # Data survives an uninstall.
        self.assertTrue((data_dir / "user-data.txt").is_file())
        self.assertTrue((data_dir / installer.DATA_SENTINEL).is_file())
        self.assertIn(str(shim), result["removed"])

    def test_purge_requires_exact_confirmation_and_removes_data(self):
        answers = self._install()
        data_dir = Path(answers.data_dir)
        # Wrong confirmation: validate-first, nothing deleted.
        with self.assertRaises(ValueError):
            installer.uninstall(
                install_root=self.install_root,
                purge_data=True,
                confirm="yes please delete",
                no_backup_ack=True,
            )
        self.assertTrue(data_dir.is_dir())
        self.assertTrue(self.record.exists())
        # Exact typed confirmation: data gone.
        os.environ["VETO_BACKUP_PASSPHRASE"] = BACKUP_PASSPHRASE
        result = installer.uninstall(
            install_root=self.install_root,
            purge_data=True,
            confirm=f"PURGE MY DATA {data_dir}",
        )
        self.assertFalse(data_dir.exists())
        self.assertTrue(result["pre_purge_backup"])  # encrypted backup taken first
        self.assertTrue(Path(result["pre_purge_backup"]).is_file())


# ---------------------------------------------------------------------------
# 2. Schema migration (real CLI against a legacy fixture data dir)
# ---------------------------------------------------------------------------


class MigrationE2ETests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name) / "data"
        (self.data / "profiles").mkdir(parents=True)
        # Legacy profile: written before the schema_version marker existed.
        (self.data / "profiles" / "legacy.json").write_text(
            json.dumps({"full_name": "Legacy User", "email": "legacy@example.com"}),
            encoding="utf-8",
        )

    def test_migrate_stamps_legacy_profile_and_marker(self):
        rc = schema_migrate.main(["--data-dir", str(self.data), "migrate"])
        self.assertEqual(rc, 0)
        stamped = json.loads(
            (self.data / "profiles" / "legacy.json").read_text(encoding="utf-8")
        )
        self.assertEqual(stamped["schema_version"], "profile-v1")
        self.assertEqual(stamped["full_name"], "Legacy User")  # data preserved
        marker = json.loads(
            (self.data / "_schema_versions.json").read_text(encoding="utf-8")
        )
        self.assertIn("profile", marker)
        # The journal records the applied migration.
        self.assertIn(
            "0001_stamp_schema_versions", schema_migrate.applied_ids(self.data)
        )

    def test_migrate_is_idempotent(self):
        self.assertEqual(
            schema_migrate.main(["--data-dir", str(self.data), "migrate"]), 0
        )
        before = (self.data / "profiles" / "legacy.json").read_text(encoding="utf-8")
        self.assertEqual(
            schema_migrate.main(["--data-dir", str(self.data), "migrate"]), 0
        )
        after = (self.data / "profiles" / "legacy.json").read_text(encoding="utf-8")
        self.assertEqual(before, after)  # second run changes nothing
        self.assertEqual(
            schema_migrate.main(["--data-dir", str(self.data), "check"]), 0
        )


# ---------------------------------------------------------------------------
# 3. Backup: create / verify / restore with byte-level fidelity
# ---------------------------------------------------------------------------


class BackupE2ETests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.data = _fixture_data_dir(root, n_events=5)
        self.archive = root / "backup.vetobackup"
        patcher = mock.patch.dict(
            os.environ, {"VETO_BACKUP_PASSPHRASE": BACKUP_PASSPHRASE}
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_create_verify_restore_round_trip(self):
        original = _sha256_tree(self.data)
        rc = backup.main(
            ["create", "--data-dir", str(self.data), "--out", str(self.archive)]
        )
        self.assertEqual(rc, 0)
        self.assertTrue(self.archive.is_file())

        rc = backup.main(["verify", "--in", str(self.archive)])
        self.assertEqual(rc, 0)

        restored = Path(self.tmp.name) / "restored"
        rc = backup.main(
            ["restore", "--in", str(self.archive), "--data-dir", str(restored)]
        )
        self.assertEqual(rc, 0)
        # Byte-level fidelity for the backed-up files. backup_audit.jsonl
        # is deliberately excluded from backups (see backup module docs)
        # and written fresh by the restore itself as an audit trail.
        restored_tree = _sha256_tree(restored)
        restored_tree.pop("backup_audit.jsonl", None)
        self.assertEqual(restored_tree, original)

    def test_wrong_passphrase_fails_verification(self):
        rc = backup.main(
            ["create", "--data-dir", str(self.data), "--out", str(self.archive)]
        )
        self.assertEqual(rc, 0)
        with mock.patch.dict(
            os.environ, {"VETO_BACKUP_PASSPHRASE": "a-completely-wrong-passphrase!!"}
        ):
            rc = backup.main(["verify", "--in", str(self.archive)])
        self.assertNotEqual(rc, 0)  # integrity failure, nonzero exit


# ---------------------------------------------------------------------------
# 4. Sync: two devices + one vault converge with no loss
# ---------------------------------------------------------------------------


class SyncE2ETests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        patcher = mock.patch.dict(os.environ, {sync.PASSPHRASE_ENV_VAR: SYNC_PASSPHRASE})
        patcher.start()
        self.addCleanup(patcher.stop)

    def _device(self, name: str, n: int) -> Path:
        d = self.root / f"data-{name}"
        (d / "profiles").mkdir(parents=True)
        (d / "profiles" / "profile.json").write_text(
            json.dumps({"schema_version": "profile-v1", "updated_at": "2026-09-01T00:00:00"}),
            encoding="utf-8",
        )
        (d / "outcomes.jsonl").write_text(
            "\n".join(json.dumps(_event(i, name)) for i in range(n)) + "\n",
            encoding="utf-8",
        )
        return d

    def test_two_devices_converge_through_real_cli(self):
        vault = self.root / "vault"
        da = self._device("a", 3)
        db = self._device("b", 4)
        self.assertEqual(
            sync.main(
                ["--data-dir", str(da), "enable", "--vault", str(vault), "--init"]
            ),
            0,
        )
        self.assertEqual(
            sync.main(
                ["--data-dir", str(db), "enable", "--vault", str(vault), "--join"]
            ),
            0,
        )
        self.assertEqual(sync.main(["--data-dir", str(da), "sync"]), 0)
        self.assertEqual(sync.main(["--data-dir", str(db), "sync"]), 0)
        self.assertEqual(sync.main(["--data-dir", str(da), "sync"]), 0)
        # Union of 3 + 4 events on both devices, no duplicates, no loss.
        for d in (da, db):
            ids = {
                json.loads(line)["event_id"]
                for line in (d / "outcomes.jsonl").read_text(
                    encoding="utf-8"
                ).splitlines()
                if line.strip()
            }
            self.assertEqual(len(ids), 7)
        # Vault host sees ciphertext only.
        vault_text = " ".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in vault.rglob("*") if p.is_file()
        )
        self.assertNotIn("e2e-ev-a-000", vault_text)

    def test_disable_returns_to_local_only(self):
        vault = self.root / "vault"
        da = self._device("a", 2)
        self.assertEqual(
            sync.main(
                ["--data-dir", str(da), "enable", "--vault", str(vault), "--init"]
            ),
            0,
        )
        self.assertTrue(sync.status(da)["enabled"])
        self.assertEqual(sync.main(["--data-dir", str(da), "disable"]), 0)
        self.assertFalse(sync.status(da)["enabled"])
        self.assertEqual(sync.main(["--data-dir", str(da), "status"]), 0)


# ---------------------------------------------------------------------------
# 5. Release channels: check + promote through the real CLI
# ---------------------------------------------------------------------------


class ReleaseChannelsE2ETests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = _fixture_data_dir(self.root, n_events=2)
        # Redirect manifest writes to a temp dir: the repo's stable.json is
        # never mutated by tests. Copy the real preview manifest there.
        self.manifest_dir = self.root / "manifests"
        self.manifest_dir.mkdir()
        shutil.copy(
            REPO_ROOT / "initiatives" / "i10" / "channels" / "preview.json",
            self.manifest_dir / "preview.json",
        )
        patcher = mock.patch.object(
            channels,
            "_manifest_path",
            lambda channel: self.manifest_dir / f"{channel}.json",
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_check_passes_on_valid_data_dir(self):
        self.assertEqual(
            channels.main(["check", "--data-dir", str(self.data)]), 0
        )
        self.assertTrue(
            channels.compatibility_ok(channels.check_compatibility(self.data))
        )

    def test_promote_copies_preview_to_stable_when_checks_pass(self):
        rc = channels.main(
            ["promote", "--data-dir", str(self.data), "--notes", "e2e promote"]
        )
        self.assertEqual(rc, 0)
        stable = json.loads(
            (self.manifest_dir / "stable.json").read_text(encoding="utf-8")
        )
        preview = json.loads(
            (self.manifest_dir / "preview.json").read_text(encoding="utf-8")
        )
        self.assertEqual(stable["channel"], "stable")
        self.assertEqual(stable["version"], preview["version"])
        self.assertEqual(stable["notes"], "e2e promote")

    def test_promote_blocked_on_failing_checks(self):
        bad = self.root / "bad-data"
        (bad / "profiles").mkdir(parents=True)
        (bad / "outcomes.jsonl").write_text("not json at all\n", encoding="utf-8")
        self.assertEqual(channels.main(["check", "--data-dir", str(bad)]), 1)
        with self.assertRaises(RuntimeError):
            channels.promote_preview_to_stable(bad, notes="must not land")
        self.assertFalse((self.manifest_dir / "stable.json").exists())


# ---------------------------------------------------------------------------
# 6. PWA: real node harness against the real service worker
# ---------------------------------------------------------------------------


class PWAHarnessE2ETests(unittest.TestCase):
    def test_node_harness_passes(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available — cannot run the JS runtime harness")
        harness = REPO_ROOT / "tests" / "i10_pwa_harness.mjs"
        proc = subprocess.run(
            [node, str(harness)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"node PWA harness failed:\n{proc.stdout}\n{proc.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
