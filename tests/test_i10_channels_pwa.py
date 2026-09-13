"""Initiative 10 — release channels + PWA bundle tests (synthetic)."""

import json
import tempfile
import unittest
from pathlib import Path

from initiatives.i10 import channels, pwa


def _data_dir(root: Path) -> Path:
    d = root / "data"
    (d / "profiles").mkdir(parents=True)
    (d / "outcomes.jsonl").write_text(
        json.dumps({
            "event_id": "synth-1",
            "application_id": "synth-job-1",
            "event_type": "applied",
            "occurred_at": "2026-09-01T10:00:00",
            "source": "synthetic-fixture",
            "role": "Synthetic Engineer",
            "provenance": {"actor": "test"},
            "schema_version": "outcome-min-v0",
        }) + "\n",
        encoding="utf-8",
    )
    (d / "profiles" / "profile.json").write_text(
        json.dumps({"schema_version": "profile-v1"}), encoding="utf-8"
    )
    return d


class TestChannels(unittest.TestCase):
    def test_channel_manifests_readable(self):
        versions = channels.current_versions()
        self.assertIn("stable", versions)
        self.assertIn("preview", versions)
        self.assertEqual(
            versions["stable"]["schema_versions"]["outcome-event"], "outcome-min-v0"
        )

    def test_unknown_channel_rejected(self):
        with self.assertRaises(ValueError):
            channels.read_channel("nightly")

    def test_migration_notes_render(self):
        notes = channels.migration_notes("0.0.9", "0.1.0")
        self.assertIn("0.0.9 → 0.1.0", notes)
        self.assertIn("outcome-min-v0", notes)
        self.assertIn("rollback", notes.lower())
        self.assertIn("Back up before upgrading", notes)

    def test_compatibility_checks_pass_on_healthy_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir(Path(tmp))
            results = channels.check_compatibility(d)
            self.assertTrue(results)
            failed = [r.name for r in results if not r.ok]
            self.assertEqual(failed, [], f"failing checks: {failed}")
            self.assertTrue(channels.compatibility_ok(results))

    def test_compatibility_checks_fail_on_corrupt_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir(Path(tmp))
            (d / "outcomes.jsonl").write_text(
                json.dumps({"event_id": "bad", "schema_version": "outcome-min-v0"}) + "\n",
                encoding="utf-8",
            )
            results = channels.check_compatibility(d)
            self.assertFalse(channels.compatibility_ok(results))

    def test_promote_blocked_on_failing_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _data_dir(Path(tmp))
            (d / "outcomes.jsonl").write_text("garbage\n", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                channels.promote_preview_to_stable(d)


class TestPwaBundle(unittest.TestCase):
    def test_bundle_validates(self):
        results = pwa.validate_bundle()
        failed = [(c.name, c.detail) for c in results if not c.ok]
        self.assertEqual(failed, [], f"failing PWA checks: {failed}")
        self.assertTrue(pwa.bundle_ok(results))

    def test_manifest_is_installable(self):
        manifest = json.loads(
            (pwa.PWA_DIR / "manifest.webmanifest").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["display"], "standalone")
        self.assertTrue(manifest["icons"])
        self.assertTrue(manifest["start_url"].startswith("/"))

    def test_deferred_queue_has_replay_api(self):
        q = (pwa.PWA_DIR / "deferred-queue.js").read_text(encoding="utf-8")
        for api in ("submit", "replay", "pending", "deadLetter", "indexedDB"):
            self.assertIn(api, q)


if __name__ == "__main__":
    unittest.main()
