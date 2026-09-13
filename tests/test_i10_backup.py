"""Initiative 10 — backup/restore/drill tests (synthetic fixtures only).

No real user data is touched: every test builds a scratch data directory
with labeled synthetic records.
"""

import json
import tempfile
import unittest
from pathlib import Path

from initiatives.i10 import backup

PASSPHRASE = "synthetic-test-passphrase"


def _event(i: int) -> dict:
    return {
        "event_id": f"synth-event-{i:03d}",
        "application_id": f"synth-job-{i:03d}",
        "event_type": "applied",
        "occurred_at": "2026-09-01T10:00:00",
        "source": "synthetic-fixture",
        "role": "Synthetic Engineer",
        "provenance": {"actor": "test"},
        "schema_version": "outcome-min-v0",
        "recorded_at": "2026-09-01T10:00:01",
    }


def _make_data_dir(root: Path, n_events: int = 5) -> Path:
    d = root / "data"
    (d / "profiles").mkdir(parents=True)
    (d / "outcomes.jsonl").write_text(
        "\n".join(json.dumps(_event(i)) for i in range(n_events)) + "\n",
        encoding="utf-8",
    )
    (d / "outcomes_meta.json").write_text(
        json.dumps({"capture_enabled_at": "2026-09-01T00:00:00"}), encoding="utf-8"
    )
    (d / "applications.json").write_text(
        json.dumps([{"job_id": f"synth-job-{i:03d}"} for i in range(n_events)]),
        encoding="utf-8",
    )
    (d / "profiles" / "profile.json").write_text(
        json.dumps({"schema_version": "profile-v1", "full_name": "Synthetic User"}),
        encoding="utf-8",
    )
    (d / "evidence_store.jsonl").write_text(
        json.dumps({
            "record_id": "synth-ev-001",
            "kind": "note",
            "application_id": "synth-job-000",
            "created_at": "2026-09-01T10:00:00",
            "schema_version": "evidence-v0",
            "title": "synthetic",
        }) + "\n",
        encoding="utf-8",
    )
    return d


class TestBackup(unittest.TestCase):
    def test_create_and_verify_100_percent(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_data_dir(Path(tmp))
            out = Path(tmp) / "b.vetobackup"
            report = backup.create_backup(d, out, PASSPHRASE)
            # 5 events + outcomes_meta + profile + evidence. NOTE: legacy
            # applications.json is NOT a named stable schema, so sync/backup
            # deliberately exclude it (contract-first rule; see caveats).
            self.assertEqual(report.records, 5 + 1 + 1 + 1)
            integrity = backup.verify_backup(out, PASSPHRASE)
            self.assertTrue(integrity.ok)
            self.assertEqual(integrity.checksum_match_pct, 100.0)
            self.assertEqual(integrity.files_ok, integrity.files_checked)

    def test_wrong_passphrase_fails_decryption(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_data_dir(Path(tmp))
            out = Path(tmp) / "b.vetobackup"
            backup.create_backup(d, out, PASSPHRASE)
            with self.assertRaises(ValueError):
                backup.verify_backup(out, "wrong-passphrase")

    def test_short_passphrase_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_data_dir(Path(tmp))
            with self.assertRaises(ValueError):
                backup.create_backup(d, Path(tmp) / "b", "short")

    def test_bundle_header_has_no_user_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_data_dir(Path(tmp))
            out = Path(tmp) / "b.vetobackup"
            backup.create_backup(d, out, PASSPHRASE)
            header, manifest, token = backup._read_bundle(out)
            header_text = json.dumps(header)
            manifest_text = json.dumps(manifest)
            self.assertNotIn("Synthetic Engineer", header_text + manifest_text)
            self.assertNotIn("synth-event", header_text + manifest_text)

    def test_audit_log_has_counts_not_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_data_dir(Path(tmp))
            backup.create_backup(d, Path(tmp) / "b.vetobackup", PASSPHRASE)
            audit = (d / backup.AUDIT_NAME).read_text(encoding="utf-8")
            self.assertIn("backup_created", audit)
            self.assertNotIn("Synthetic Engineer", audit)


class TestRestore(unittest.TestCase):
    def test_full_restore_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_data_dir(Path(tmp))
            out = Path(tmp) / "b.vetobackup"
            backup.create_backup(d, out, PASSPHRASE)
            target = Path(tmp) / "restored"
            report = backup.restore(out, PASSPHRASE, target)
            self.assertEqual(report.verify.checksum_match_pct, 100.0)
            self.assertEqual(
                (target / "outcomes.jsonl").read_text(encoding="utf-8"),
                (d / "outcomes.jsonl").read_text(encoding="utf-8"),
            )

    def test_selective_restore_only_named_schemas(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_data_dir(Path(tmp))
            out = Path(tmp) / "b.vetobackup"
            backup.create_backup(d, out, PASSPHRASE)
            target = Path(tmp) / "restored"
            report = backup.restore(out, PASSPHRASE, target, selective=["outcome-event"])
            self.assertEqual(report.selective, ["outcome-event"])
            self.assertTrue((target / "outcomes.jsonl").exists())
            self.assertFalse((target / "profiles" / "profile.json").exists())

    def test_selective_restore_rejects_unknown_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_data_dir(Path(tmp))
            out = Path(tmp) / "b.vetobackup"
            backup.create_backup(d, out, PASSPHRASE)
            with self.assertRaises(KeyError):
                backup.restore(out, PASSPHRASE, Path(tmp) / "r", selective=["resume-pdf"])


class TestDrill(unittest.TestCase):
    def test_drill_passes_with_zero_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_data_dir(Path(tmp), n_events=12)
            report = backup.drill(d, PASSPHRASE)
            self.assertTrue(report.ok, report.detail)
            self.assertEqual(report.checksum_match_pct, 100.0)
            self.assertTrue(all(v == 0 for v in report.record_gap.values()))

    def test_drill_leaves_live_store_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _make_data_dir(Path(tmp))
            before = sorted(p.name for p in d.iterdir())
            backup.drill(d, PASSPHRASE)
            # Only the audit log may be appended.
            after = sorted(p.name for p in d.iterdir())
            self.assertEqual(set(after) - set(before), {backup.AUDIT_NAME})


if __name__ == "__main__":
    unittest.main()
