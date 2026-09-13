#!/usr/bin/env python3
"""Signed packages + curated registry tests (Initiative 11, Epics 5-6)."""

import json
import tempfile
import unittest
from pathlib import Path

from initiatives.i11.manifest.schema import load_manifest
from initiatives.i11.registry.registry import GATES, Registry
from initiatives.i11.signing.sign import (
    InstallRecord, InstallStore, RevocationList, generate_keypair,
    package_hash, sign_package, verify_package,
)

REF_EXT = Path("initiatives/i11/reference/role-radar-digest")
_PRIV, _PUB = generate_keypair()
_OTHER_PRIV, _OTHER_PUB = generate_keypair()


def _copy_ref() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="veto-reg-"))
    import shutil
    shutil.copytree(REF_EXT, tmp / "ext")
    # Drop any signature sidecar so each test controls signing itself.
    (tmp / "ext" / ".veto-signature.json").unlink(missing_ok=True)
    return tmp / "ext"


class TestSigning(unittest.TestCase):
    def test_sign_and_verify(self):
        ext = _copy_ref()
        env = sign_package(ext, publisher="tester", private_key=_PRIV)
        self.assertIn("package_sha256", env)
        self.assertEqual(env["alg"], "ed25519-v1")
        verdict = verify_package(ext, public_key=_PUB)
        self.assertTrue(verdict["ok"], verdict)
        self.assertTrue(verdict["pinned"])

    def test_tamper_detected(self):
        ext = _copy_ref()
        sign_package(ext, publisher="tester", private_key=_PRIV)
        (ext / "extension.py").write_text(
            (ext / "extension.py").read_text() + "\n# tampered\n")
        verdict = verify_package(ext, public_key=_PUB)
        self.assertFalse(verdict["ok"])

    def test_wrong_key_rejected(self):
        ext = _copy_ref()
        sign_package(ext, publisher="tester", private_key=_PRIV)
        verdict = verify_package(ext, public_key=_OTHER_PUB)
        self.assertFalse(verdict["ok"])

    def test_self_asserted_pubkey_flagged_not_pinned(self):
        # Without a pinned key, verification uses the sidecar's embedded
        # pubkey: integrity holds, but provenance is self-asserted.
        ext = _copy_ref()
        sign_package(ext, publisher="tester", private_key=_PRIV)
        verdict = verify_package(ext)
        self.assertTrue(verdict["ok"], verdict)
        self.assertFalse(verdict["pinned"])

    def test_unsigned_package_flagged(self):
        ext = _copy_ref()
        verdict = verify_package(ext, public_key=_PUB)
        self.assertFalse(verdict["ok"])
        self.assertIn("unsigned", verdict["error"])

    def test_hash_deterministic(self):
        ext = _copy_ref()
        self.assertEqual(package_hash(ext), package_hash(ext))


class TestInstallStore(unittest.TestCase):
    def test_pin_and_upgrade_review(self):
        tmp = Path(tempfile.mkdtemp())
        store = InstallStore(tmp / "installed.json")
        store.record_install(InstallRecord(
            ext_id="e1", version="1.0.0", package_sha256="abc",
            publisher="p", installed_at=1))
        # Upgrade without a review is refused.
        bad = store.record_upgrade("e1", "1.1.0", "def", {})
        self.assertFalse(bad["ok"])
        good = store.record_upgrade("e1", "1.1.0", "def", {
            "reviewer": "human", "verdict": "pass",
            "date": "2026-09-13", "notes": "changelog reviewed"})
        self.assertTrue(good["ok"])
        self.assertEqual(store.get("e1")["version"], "1.1.0")
        self.assertEqual(store.get("e1")["upgraded_from"], "1.0.0")


class TestRevocation(unittest.TestCase):
    def test_revoke_blocks(self):
        tmp = Path(tempfile.mkdtemp())
        rev = RevocationList(tmp / "rev.json")
        self.assertFalse(rev.is_revoked("e1", "1.0.0"))
        rev.revoke("e1", "1.0.0", reason="malicious exfiltration",
                   revoked_by="publisher")
        self.assertTrue(rev.is_revoked("e1", "1.0.0"))
        self.assertFalse(rev.is_revoked("e1", "1.0.1"))


class TestRegistry(unittest.TestCase):
    def _registry(self):
        tmp = Path(tempfile.mkdtemp())
        return Registry(tmp / "registry.json",
                        revocations=RevocationList(tmp / "rev.json"))

    def test_submit_runs_automated_gates(self):
        ext = _copy_ref()
        sign_package(ext, publisher="tester", private_key=_PRIV)
        reg = self._registry()
        result = reg.submit(ext, publisher="tester", publisher_pubkey=_PUB)
        self.assertTrue(result["ok"], result)
        gates = result["entry"]["gates"]
        self.assertEqual(gates["compatibility"]["verdict"], "pass")
        self.assertEqual(gates["security"]["verdict"], "pass")
        self.assertEqual(gates["ux"]["verdict"], "pending")
        self.assertEqual(gates["governance"]["verdict"], "pending")
        # Not installable until humans pass ux + governance.
        self.assertFalse(reg.installable("role-radar-digest")["ok"])

    def test_all_gates_pass_makes_installable(self):
        ext = _copy_ref()
        sign_package(ext, publisher="tester", private_key=_PRIV)
        reg = self._registry()
        reg.submit(ext, publisher="tester", publisher_pubkey=_PUB)
        for gate in ("ux", "governance"):
            rec = reg.record_gate("role-radar-digest", gate,
                                  verdict="pass", reviewer="human-reviewer",
                                  notes="reviewed")
            self.assertTrue(rec["ok"])
        installable = reg.installable("role-radar-digest")
        self.assertTrue(installable["ok"], installable)
        self.assertEqual(installable["publisher_pubkey"], _PUB)

    def test_failed_gate_blocks_install(self):
        ext = _copy_ref()
        sign_package(ext, publisher="tester", private_key=_PRIV)
        reg = self._registry()
        reg.submit(ext, publisher="tester", publisher_pubkey=_PUB)
        reg.record_gate("role-radar-digest", "ux", verdict="pass",
                        reviewer="uxr", notes="ok")
        rec = reg.record_gate("role-radar-digest", "governance",
                              verdict="fail", reviewer="reviewer",
                              notes="audit gap")
        self.assertFalse(rec["publishable"])
        self.assertFalse(reg.installable("role-radar-digest")["ok"])

    def test_submit_with_wrong_pinned_key_fails_security_gate(self):
        ext = _copy_ref()
        sign_package(ext, publisher="tester", private_key=_PRIV)
        reg = self._registry()
        result = reg.submit(ext, publisher="tester",
                            publisher_pubkey=_OTHER_PUB)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["entry"]["gates"]["security"]["verdict"],
                         "fail")

    def test_four_gates_exist(self):
        self.assertEqual(tuple(GATES),
                         ("compatibility", "security", "ux", "governance"))


if __name__ == "__main__":
    unittest.main()
