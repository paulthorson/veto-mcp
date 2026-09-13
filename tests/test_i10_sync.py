"""Initiative 10 — opt-in sync tests (synthetic fixtures only).

Sync is local-only by default; these tests prove opt-in behavior,
envelope opacity to the vault host, pairing-code agreement, and
deterministic merge with no record loss.
"""

import json
import tempfile
import unittest
from pathlib import Path

from initiatives.i10 import backup, sync

PASSPHRASE = "synthetic-sync-passphrase"


def _event(i: int, device: str = "a") -> dict:
    return {
        "event_id": f"synth-ev-{device}-{i:03d}",
        "application_id": f"synth-job-{i:03d}",
        "event_type": "applied",
        "occurred_at": "2026-09-01T10:00:00",
        "source": "synthetic-fixture",
        "role": "Synthetic Engineer",
        "provenance": {"actor": "test"},
        "schema_version": "outcome-min-v0",
        "recorded_at": "2026-09-01T10:00:01",
    }


def _data_dir(root: Path, device: str, n: int = 3) -> Path:
    d = root / f"data-{device}"
    (d / "profiles").mkdir(parents=True)
    (d / "outcomes.jsonl").write_text(
        "\n".join(json.dumps(_event(i, device)) for i in range(n)) + "\n",
        encoding="utf-8",
    )
    (d / "profiles" / "profile.json").write_text(
        json.dumps({"schema_version": "profile-v1", "updated_at": "2026-09-01T00:00:00"}),
        encoding="utf-8",
    )
    return d


class TestOptIn(unittest.TestCase):
    def test_sync_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir(Path(tmp), "a")
            self.assertFalse(sync.status(d)["enabled"])
            with self.assertRaises(RuntimeError):
                sync.sync_round(d, PASSPHRASE)

    def test_enable_requires_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir(Path(tmp), "a")
            result = sync.enable(d, PASSPHRASE, str(Path(tmp) / "vault"))
            self.assertTrue(result["enabled"])
            self.assertTrue(sync.status(d)["enabled"])
            self.assertRegex(result["pairing_code"], r"^(\w+-){5}\w+$")

    def test_disable_returns_to_local_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir(Path(tmp), "a")
            sync.enable(d, PASSPHRASE, str(Path(tmp) / "vault"))
            sync.disable(d)
            self.assertFalse(sync.status(d)["enabled"])


class TestPairing(unittest.TestCase):
    def test_same_passphrase_same_pairing_code(self):
        import base64
        import os

        salt = os.urandom(16)
        k1 = sync.derive_sync_key(PASSPHRASE, salt)
        k2 = sync.derive_sync_key(PASSPHRASE, salt)
        self.assertEqual(sync.pairing_code(k1), sync.pairing_code(k2))

    def test_different_passphrase_different_code(self):
        import base64
        import os

        salt = os.urandom(16)
        k1 = sync.derive_sync_key(PASSPHRASE, salt)
        k2 = sync.derive_sync_key("another-synthetic-passphrase", salt)
        self.assertNotEqual(sync.pairing_code(k1), sync.pairing_code(k2))


class TestSyncRound(unittest.TestCase):
    def test_two_devices_converge_with_no_loss(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            da = _data_dir(root, "a", n=3)
            db = _data_dir(root, "b", n=4)
            sync.enable(da, PASSPHRASE, str(vault))
            sync.enable(db, PASSPHRASE, str(vault))

            ra = sync.sync_round(da, PASSPHRASE)
            self.assertEqual(ra["peers_merged"], 0)  # first device: no peers yet
            rb = sync.sync_round(db, PASSPHRASE)
            self.assertEqual(rb["peers_merged"], 1)
            ra2 = sync.sync_round(da, PASSPHRASE)
            self.assertEqual(ra2["peers_merged"], 1)

            for d in (da, db):
                ids = {
                    json.loads(line)["event_id"]
                    for line in (d / "outcomes.jsonl").read_text(encoding="utf-8").splitlines()
                    if line.strip()
                }
                self.assertEqual(len(ids), 7)  # 3 + 4, union, no dupes

    def test_vault_sees_ciphertext_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            da = _data_dir(root, "a")
            sync.enable(da, PASSPHRASE, str(root / "vault"))
            sync.sync_round(da, PASSPHRASE)
            blobs = list((root / "vault").glob("*.vetosync"))
            self.assertTrue(blobs)
            raw = blobs[0].read_bytes()
            self.assertNotIn(b"Synthetic Engineer", raw)
            self.assertNotIn(b"synth-ev-a", raw)

    def test_wrong_passphrase_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            da = _data_dir(root, "a")
            sync.enable(da, PASSPHRASE, str(root / "vault"))
            with self.assertRaises(ValueError):
                sync.sync_round(da, "wrong-synthetic-passphrase")

    def test_audit_log_has_counts_not_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            da = _data_dir(root, "a")
            sync.enable(da, PASSPHRASE, str(root / "vault"))
            sync.sync_round(da, PASSPHRASE)
            audit = (da / sync.AUDIT_NAME).read_text(encoding="utf-8")
            self.assertNotIn("Synthetic Engineer", audit)


class TestMerge(unittest.TestCase):
    def test_newer_remote_record_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            da = _data_dir(root, "a", n=1)
            env = sync.Envelope(
                device_id="peer1",
                sequence=1,
                created_at="2026-09-02T00:00:00",
                schema_versions={},
                datasets={
                    "outcome-event": {
                        "outcomes.jsonl": [
                            {**_event(0, "a"), "recorded_at": "2026-09-02T00:00:00", "role": "Updated Role"}
                        ]
                    }
                },
            )
            report = sync.merge_envelope(da, env, "local")
            self.assertTrue(report["merged"])
            rec = json.loads((da / "outcomes.jsonl").read_text(encoding="utf-8").strip())
            self.assertEqual(rec["role"], "Updated Role")

    def test_own_envelope_not_merged(self):
        with tempfile.TemporaryDirectory() as tmp:
            da = _data_dir(Path(tmp), "a", n=1)
            env = sync.Envelope("local", 1, "2026-09-02T00:00:00", {}, {})
            self.assertFalse(sync.merge_envelope(da, env, "local")["merged"])


if __name__ == "__main__":
    unittest.main()
