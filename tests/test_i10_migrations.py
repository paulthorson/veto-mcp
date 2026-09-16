"""Initiative 10 — migration framework tests (synthetic fixtures)."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from initiatives.i10 import schema_migrate
from initiatives.i10.schema_migrate import Migration, MigrationError, MigrationRunner


def _data_dir_with_legacy_profile(tmp: str) -> Path:
    d = Path(tmp)
    (d / "profiles").mkdir()
    # Legacy wizard-written profile: no schema_version marker.
    (d / "profiles" / "profile.json").write_text(
        json.dumps({"full_name": "Test User"}), encoding="utf-8"
    )
    return d


class TestMigrationLifecycle(unittest.TestCase):
    def test_discover_finds_migrations_in_order(self):
        migs = schema_migrate.discover_migrations()
        self.assertTrue(migs)
        ids = [m.migration_id for m in migs]
        self.assertEqual(ids, sorted(ids))

    def test_migrate_applies_and_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir_with_legacy_profile(tmp)
            runner = schema_migrate.MigrationRunner(d)
            self.assertEqual(runner.status()["pending"], ["0001_stamp_schema_versions"])
            results = runner.migrate()
            self.assertTrue(all(r["applied"] for r in results))
            # Journal recorded.
            journal = schema_migrate.journal_records(d)
            self.assertEqual(journal[0]["action"], "applied")
            # Profile now stamped.
            profile = json.loads((d / "profiles" / "profile.json").read_text(encoding="utf-8"))
            self.assertEqual(profile["schema_version"], "profile-v1")
            # check_all (compatibility suite) passes.
            for r in runner.check_all():
                self.assertTrue(r["ok"], r)

    def test_migrate_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir_with_legacy_profile(tmp)
            runner = schema_migrate.MigrationRunner(d)
            runner.migrate()
            self.assertEqual(runner.migrate(), [])

    def test_rollback_appends_record_and_allows_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir_with_legacy_profile(tmp)
            runner = schema_migrate.MigrationRunner(d)
            runner.migrate()
            result = runner.rollback("0001_stamp_schema_versions")
            self.assertTrue(result["rolled_back"])
            journal = schema_migrate.journal_records(d)
            actions = [r["action"] for r in journal]
            self.assertEqual(actions, ["applied", "rolled_back"])  # history preserved
            self.assertEqual(runner.status()["applied"], [])
            # Re-run works after rollback.
            runner.migrate()
            self.assertEqual(runner.status()["applied"], ["0001_stamp_schema_versions"])

    def test_rollback_unknown_migration_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = schema_migrate.MigrationRunner(Path(tmp))
            with self.assertRaises(schema_migrate.MigrationError):
                runner.rollback("9999_nope")

    def test_rollback_unapplied_migration_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            runner = schema_migrate.MigrationRunner(Path(tmp))
            with self.assertRaises(schema_migrate.MigrationError):
                runner.rollback("0001_stamp_schema_versions")

    def test_dry_run_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir_with_legacy_profile(tmp)
            runner = schema_migrate.MigrationRunner(d)
            runner.migrate(dry_run=True)
            self.assertFalse((d / "_migrations.jsonl").exists())
            self.assertFalse((d / "_backups").exists())
            self.assertEqual(runner.status()["applied"], [])


def _fake_migration(migration_id, *, forward, verify, backward=None):
    """Build a synthetic Migration for probe tests (discovery patched)."""
    module = SimpleNamespace(
        forward=forward,
        verify=verify,
        backward=backward or (lambda data_dir: {}),
    )
    return Migration(
        migration_id=migration_id,
        from_version={},
        to_version={},
        module=module,
        path=Path(f"{migration_id}.py"),
    )


class TestReviewerProbes(unittest.TestCase):
    """Adversarial probes from the blind review (Rule 1 veto findings)."""

    def test_probe_dry_run_of_verify_failing_migration_signals_failure(self):
        state = {"fail": True}

        def forward(data_dir):
            (Path(data_dir) / "dryrun_touched.json").write_text("{}")
            return {"touched": True}

        def verify(data_dir):
            if state["fail"]:
                return {"ok": False, "problems": ["deliberate verify failure"]}
            return {"ok": True, "problems": []}

        fake = _fake_migration("9999_verify_probe", forward=forward, verify=verify)
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir_with_legacy_profile(tmp)
            runner = MigrationRunner(d)
            with patch.object(
                schema_migrate, "discover_migrations", return_value=[fake]
            ):
                # Failing verify MUST produce a failing dry-run signal.
                with self.assertRaises(MigrationError) as ctx:
                    runner.migrate(dry_run=True)
                self.assertIn("9999_verify_probe", str(ctx.exception))
                # The real data dir is untouched: no journal, no backup,
                # no forward side effects.
                self.assertFalse((d / "_migrations.jsonl").exists())
                self.assertFalse((d / "_backups").exists())
                self.assertFalse((d / "dryrun_touched.json").exists())
                profile = json.loads(
                    (d / "profiles" / "profile.json").read_text(encoding="utf-8")
                )
                self.assertNotIn("schema_version", profile)

                # A passing dry run reports a real would_pass and writes nothing.
                state["fail"] = False
                results = runner.migrate(dry_run=True)
                self.assertEqual(len(results), 1)
                r = results[0]
                self.assertFalse(r["applied"])
                self.assertTrue(r["dry_run"])
                self.assertTrue(r["verify"]["dry_run"])
                self.assertTrue(r["verify"]["would_pass"])
                self.assertEqual(r["verify"]["problems"], [])
                self.assertFalse((d / "_migrations.jsonl").exists())
                self.assertFalse((d / "dryrun_touched.json").exists())
                self.assertEqual(runner.status()["applied"], [])

    def test_probe_failed_verify_journals_attempt_and_rerun_recovers(self):
        state = {"fail": True}

        def forward(data_dir):
            (Path(data_dir) / "touched.json").write_text("{}")
            return {"touched": ["touched.json"]}

        def verify(data_dir):
            if state["fail"]:
                return {"ok": False, "problems": ["boom"]}
            return {"ok": True, "problems": []}

        fake = _fake_migration("9999_partial_probe", forward=forward, verify=verify)
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir_with_legacy_profile(tmp)
            runner = MigrationRunner(d)
            with patch.object(
                schema_migrate, "discover_migrations", return_value=[fake]
            ):
                with self.assertRaises(MigrationError) as ctx:
                    runner.migrate()
                self.assertIn("failed verify", str(ctx.exception))

                # Status distinguishes attempted-but-failed from never-attempted.
                status = runner.status()
                self.assertEqual(status["applied"], [])
                self.assertIn("9999_partial_probe", status["pending"])
                self.assertIn("9999_partial_probe", status["failed_attempts"])

            # The attempt is journaled with forward's detail and the failure.
            records = schema_migrate.journal_records(d)
            failed = [r for r in records if r["action"] == "attempt_failed"]
            self.assertEqual(len(failed), 1)
            self.assertEqual(failed[0]["migration_id"], "9999_partial_probe")
            self.assertEqual(failed[0]["detail"], {"touched": ["touched.json"]})
            self.assertIn("boom", failed[0]["error"])

            # Partial application is visible...
            self.assertTrue((d / "touched.json").exists())
            # ...but the pre-migration snapshot predates it (backup before
            # mutation): the snapshot must NOT contain touched.json.
            snapshots = sorted((d / "_backups").iterdir())
            self.assertTrue(snapshots)
            self.assertFalse((snapshots[0] / "touched.json").exists())

            with patch.object(
                schema_migrate, "discover_migrations", return_value=[fake]
            ):
                # Re-run after the underlying issue is fixed recovers cleanly.
                state["fail"] = False
                results = runner.migrate()
                self.assertTrue(results[0]["applied"])
                status = runner.status()
                self.assertEqual(status["applied"], ["9999_partial_probe"])
                self.assertEqual(status["failed_attempts"], [])

    def test_probe_backup_snapshot_created_before_forward_mutates(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir_with_legacy_profile(tmp)
            runner = MigrationRunner(d)
            self.assertFalse((d / "_backups").exists())
            runner.migrate()  # real 0001
            snapshots = sorted((d / "_backups").iterdir())
            self.assertTrue(snapshots, "no backup snapshot was created")
            for snap in snapshots:
                self.assertTrue(snap.is_dir())
            # The snapshot holds PRE-migration content: the profile must not
            # yet carry the schema_version marker forward() adds.
            snap_profile = json.loads(
                (snapshots[0] / "profiles" / "profile.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertNotIn("schema_version", snap_profile)
            # The snapshot name is recorded on the applied journal record.
            applied = [
                r
                for r in schema_migrate.journal_records(d)
                if r["action"] == "applied"
            ]
            self.assertEqual(len(applied), 1)
            self.assertEqual(applied[0]["snapshot"], snapshots[0].name)

    def test_probe_corrupt_journal_line_survives_with_explicit_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir_with_legacy_profile(tmp)
            runner = MigrationRunner(d)
            runner.migrate()  # one valid journal record
            journal = d / "_migrations.jsonl"
            with journal.open("a", encoding="utf-8") as fh:
                fh.write("{this is not valid json\n")
            # The runner survives: status/pending/check_all all work...
            status = runner.status()
            self.assertEqual(status["applied"], ["0001_stamp_schema_versions"])
            self.assertEqual(status["pending"], [])
            self.assertEqual(runner.pending(), [])
            for r in runner.check_all():
                self.assertTrue(r["ok"], r)
            # ...and the corruption is surfaced explicitly, not silent.
            self.assertEqual(status["journal_corrupt_lines"], 1)
            warnings = schema_migrate.journal_warnings(d)
            self.assertEqual(len(warnings), 1)
            self.assertEqual(warnings[0]["line"], 2)

    def test_probe_duplicate_migration_id_rejected_loudly(self):
        module_src = (
            'MIGRATION_ID = "dup_probe_id"\n'
            "FROM_VERSION = {}\n"
            "TO_VERSION = {}\n"
            "def forward(data_dir): return {}\n"
            "def backward(data_dir): return {}\n"
            'def verify(data_dir): return {"ok": True}\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            mig_dir = Path(tmp)
            (mig_dir / "0001_a.py").write_text(module_src, encoding="utf-8")
            (mig_dir / "0002_b.py").write_text(module_src, encoding="utf-8")
            with patch.object(schema_migrate, "MIGRATIONS_DIR", mig_dir):
                with self.assertRaises(MigrationError) as ctx:
                    schema_migrate.discover_migrations()
            self.assertIn("dup_probe_id", str(ctx.exception))
            self.assertIn("Duplicate", str(ctx.exception))

    def test_probe_deleted_migration_file_raises_migration_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir_with_legacy_profile(tmp)
            runner = MigrationRunner(d)
            runner.migrate()  # 0001 applied
            self.assertEqual(runner.status()["applied"], ["0001_stamp_schema_versions"])
            # Simulate the migration module file being deleted afterwards.
            with tempfile.TemporaryDirectory() as empty_mig_dir:
                with patch.object(
                    schema_migrate, "MIGRATIONS_DIR", Path(empty_mig_dir)
                ):
                    with self.assertRaises(MigrationError) as ctx:
                        runner.check_all()
            self.assertIn("0001_stamp_schema_versions", str(ctx.exception))


class TestRollbackHonesty(unittest.TestCase):
    """0001.backward must strip exactly what forward stamped."""

    def test_rollback_unstamps_profiles_it_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir_with_legacy_profile(tmp)
            runner = MigrationRunner(d)
            runner.migrate()
            profile = json.loads(
                (d / "profiles" / "profile.json").read_text(encoding="utf-8")
            )
            self.assertEqual(profile["schema_version"], "profile-v1")
            result = runner.rollback("0001_stamp_schema_versions")
            self.assertIn("profile.json", result["detail"]["unstamped_profiles"])
            profile = json.loads(
                (d / "profiles" / "profile.json").read_text(encoding="utf-8")
            )
            self.assertNotIn("schema_version", profile)
            self.assertFalse((d / "_schema_versions.json").exists())

    def test_rollback_preserves_preexisting_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "profiles").mkdir()
            # Profile already carried the marker before this migration ran.
            (d / "profiles" / "profile.json").write_text(
                json.dumps({"full_name": "Test User", "schema_version": "profile-v1"}),
                encoding="utf-8",
            )
            runner = MigrationRunner(d)
            runner.migrate()
            runner.rollback("0001_stamp_schema_versions")
            # backward must not strip a marker it did not add.
            profile = json.loads(
                (d / "profiles" / "profile.json").read_text(encoding="utf-8")
            )
            self.assertEqual(profile["schema_version"], "profile-v1")
            self.assertFalse((d / "_schema_versions.json").exists())


class TestFailureAccounting(unittest.TestCase):
    """RE-review findings: failure accounting must never go silent."""

    def test_verify_raising_journals_attempt_failed_and_raises_migration_error(self):
        """A verify() that RAISES must be journaled as attempt_failed and
        wrapped in MigrationError — never a raw exception with a [] journal.
        """
        def forward(data_dir):
            (Path(data_dir) / "touched.json").write_text("{}")
            return {"touched": True}

        def verify(data_dir):
            raise RuntimeError("deliberate verify blowup")

        fake = _fake_migration("9999_verify_raises", forward=forward, verify=verify)
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir_with_legacy_profile(tmp)
            runner = MigrationRunner(d)
            with patch.object(
                schema_migrate, "discover_migrations", return_value=[fake]
            ):
                with self.assertRaises(MigrationError) as ctx:
                    runner.migrate()
                self.assertIn("9999_verify_raises", str(ctx.exception))
                # A wrapped MigrationError, not the raw RuntimeError from verify.
                self.assertIs(type(ctx.exception), MigrationError)
                # Status distinguishes it from never-attempted.
                status = runner.status()
                self.assertEqual(status["applied"], [])
                self.assertIn("9999_verify_raises", status["pending"])
                self.assertIn("9999_verify_raises", status["failed_attempts"])
            # The journal is NOT []: the attempt is journaled.
            records = schema_migrate.journal_records(d)
            failed = [r for r in records if r["action"] == "attempt_failed"]
            self.assertEqual(len(failed), 1)
            self.assertEqual(failed[0]["migration_id"], "9999_verify_raises")
            self.assertIn("verify raised RuntimeError", failed[0]["error"])
            self.assertIn("deliberate verify blowup", failed[0]["error"])
            self.assertEqual(failed[0]["detail"], {"touched": True})
            # The pre-forward snapshot exists for recovery (data corrupted by
            # forward, then verify raised).
            snapshots = sorted((d / "_backups").iterdir())
            self.assertTrue(snapshots)
            self.assertFalse((snapshots[0] / "touched.json").exists())

    def test_rollback_failure_snapshots_and_journals_rollback_failed(self):
        """A backward() that corrupts then raises must: leave a pre-backward
        snapshot, journal a rollback_failed record, and raise MigrationError
        (never a raw RuntimeError with only the original applied record).
        """
        def forward(data_dir):
            return {}

        def verify(data_dir):
            return {"ok": True}

        def backward(data_dir):
            # Corrupts data, THEN blows up — the worst case.
            (Path(data_dir) / "corrupted.json").write_text("{}")
            raise RuntimeError("deliberate backward blowup")

        fake = _fake_migration(
            "9999_rollback_fails",
            forward=forward,
            verify=verify,
            backward=backward,
        )
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir_with_legacy_profile(tmp)
            runner = MigrationRunner(d)
            with patch.object(
                schema_migrate, "discover_migrations", return_value=[fake]
            ):
                runner.migrate()
                with self.assertRaises(MigrationError) as ctx:
                    runner.rollback("9999_rollback_fails")
                self.assertIn("9999_rollback_fails", str(ctx.exception))
                self.assertIn("snapshot", str(ctx.exception))
                # A wrapped MigrationError, not the raw RuntimeError from backward.
                self.assertIs(type(ctx.exception), MigrationError)
            # A pre-backward snapshot exists; it predates the corruption.
            rollback_snaps = [
                p
                for p in (d / "_backups").iterdir()
                if p.name.endswith("9999_rollback_fails-rollback")
            ]
            self.assertEqual(len(rollback_snaps), 1)
            self.assertFalse((rollback_snaps[0] / "corrupted.json").exists())
            # The failure is journaled (journal != [applied] alone).
            records = schema_migrate.journal_records(d)
            failed = [r for r in records if r["action"] == "rollback_failed"]
            self.assertEqual(len(failed), 1)
            self.assertEqual(failed[0]["migration_id"], "9999_rollback_fails")
            self.assertIn("backward raised RuntimeError", failed[0]["error"])
            self.assertIn("snapshot", failed[0])
            self.assertEqual(failed[0]["snapshot"], rollback_snaps[0].name)
            # The migration stays applied: the rollback did not complete.
            self.assertEqual(runner.status()["applied"], ["9999_rollback_fails"])

    def test_successful_rollback_records_snapshot(self):
        """A successful rollback carries the pre-backward snapshot name on
        the rolled_back journal record and in the result."""
        fake = _fake_migration(
            "9999_ok_rollback",
            forward=lambda dd: {},
            verify=lambda dd: {"ok": True},
            backward=lambda dd: {},
        )
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir_with_legacy_profile(tmp)
            runner = MigrationRunner(d)
            with patch.object(
                schema_migrate, "discover_migrations", return_value=[fake]
            ):
                runner.migrate()
                result = runner.rollback("9999_ok_rollback")
            self.assertTrue(result["rolled_back"])
            self.assertIn("snapshot", result)
            records = schema_migrate.journal_records(d)
            rolled = [r for r in records if r["action"] == "rolled_back"]
            self.assertEqual(len(rolled), 1)
            self.assertEqual(rolled[0]["snapshot"], result["snapshot"])


if __name__ == "__main__":
    unittest.main()
