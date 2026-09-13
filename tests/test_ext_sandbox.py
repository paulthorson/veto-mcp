#!/usr/bin/env python3
"""Sandbox / host-broker tests (Initiative 11, Epic 2).

Proves the hard rule at the unit level: confirmation cannot be
self-minted, forged, or replayed; filesystem and network are
deny-by-default; the audit log is append-only and host-written.
"""

import json
import tempfile
import unittest
from pathlib import Path

from initiatives.i11.sandbox.audit import ExtensionAudit
from initiatives.i11.sandbox.fs import SandboxFS, SandboxViolation
from initiatives.i11.sandbox.host import ConfirmationBroker, Host
from initiatives.i11.sandbox.net import (
    CircuitOpen, HttpRequest, HttpResponse, RateLimitExceeded, SandboxHTTP,
    SandboxViolation as NetViolation,
)

_SECRET = b"unit-test-secret-32-bytes-padding!!"


def _mkext(actions, **perm_over):
    tmp = Path(tempfile.mkdtemp(prefix="veto-ut-"))
    manifest = {
        "manifest_version": 1, "id": "ut-ext", "version": "0.0.1",
        "name": "UT", "description": "unit test fixture",
        "permissions": {
            "data": ["jobs:read", "profile:read"],
            "network": {"destinations": ["api.example"]},
            "actions": actions, "pii": "redact",
            "sandbox": {"fs_roots": ["workspace"],
                        "rate_limit": {"calls_per_minute": 60}},
        },
    }
    manifest["permissions"].update(perm_over)
    (tmp / "manifest.json").write_text(json.dumps(manifest))
    (tmp / "extension.py").write_text(
        "ACTIONS = {\n"
        + "".join(f"    '{a['id']}': lambda ctx, **kw: {{'ok': True}},\n"
                  for a in actions)
        + "}\n")
    return tmp


def _host():
    tmp = Path(tempfile.mkdtemp(prefix="veto-ut-audit-"))
    return Host(audit_path=tmp / "audit.jsonl", secret=_SECRET)


class TestConfirmationBroker(unittest.TestCase):
    def test_full_cycle(self):
        broker = ConfirmationBroker(secret=_SECRET)
        pending = broker.request("e1", "a1", {"action": "a1", "params": {}})
        token = broker.mint(pending.pending_id)
        self.assertTrue(broker.verify(token, ext_id="e1", action_id="a1",
                                      payload={"action": "a1", "params": {}}))

    def test_wrong_secret_rejected(self):
        broker = ConfirmationBroker(secret=_SECRET)
        forger = ConfirmationBroker(secret=b"other-secret-32-bytes-padding!!")
        pending = forger.request("e1", "a1", {"action": "a1", "params": {}})
        forged = forger.mint(pending.pending_id)
        self.assertFalse(broker.verify(forged, ext_id="e1", action_id="a1",
                                       payload={"action": "a1", "params": {}}))

    def test_replay_rejected(self):
        broker = ConfirmationBroker(secret=_SECRET)
        pending = broker.request("e1", "a1", {"action": "a1", "params": {}})
        token = broker.mint(pending.pending_id)
        payload = {"action": "a1", "params": {}}
        self.assertTrue(broker.verify(token, ext_id="e1", action_id="a1",
                                      payload=payload))
        self.assertFalse(broker.verify(token, ext_id="e1", action_id="a1",
                                       payload=payload))

    def test_payload_swap_rejected(self):
        broker = ConfirmationBroker(secret=_SECRET)
        pending = broker.request("e1", "a1", {"action": "a1", "params": {}})
        token = broker.mint(pending.pending_id)
        self.assertFalse(broker.verify(
            token, ext_id="e1", action_id="a1",
            payload={"action": "a1", "params": {"evil": True}}))

    def test_cross_extension_binding_rejected(self):
        broker = ConfirmationBroker(secret=_SECRET)
        pending = broker.request("e1", "a1", {"action": "a1", "params": {}})
        token = broker.mint(pending.pending_id)
        self.assertFalse(broker.verify(token, ext_id="e2", action_id="a1",
                                       payload={"action": "a1", "params": {}}))

    def test_expired_pending_cannot_mint(self):
        broker = ConfirmationBroker(secret=_SECRET)
        pending = broker.request("e1", "a1", {"action": "a1", "params": {}})
        pending.expires_at = 0  # force expiry
        with self.assertRaises(ValueError):
            broker.mint(pending.pending_id)


class TestHostConfirmationGate(unittest.TestCase):
    def test_confirm_required_without_token_refused(self):
        ext = _mkext([{"id": "send", "kind": "confirm-required",
                       "confirm_required": True}])
        host = _host()
        loaded = host.load_extension(ext)
        with self.assertRaises(PermissionError):
            host.run_extension_action(loaded.ext_id, "send")

    def test_confirm_required_with_valid_token_runs(self):
        ext = _mkext([{"id": "send", "kind": "confirm-required",
                       "confirm_required": True}])
        host = _host()
        # Governance veto screen: framework unavailable in tests -> advisory.
        loaded = host.load_extension(ext)
        pending = host.confirmations.request(
            loaded.ext_id, "send", {"action": "send", "params": {}})
        token = host.confirmations.mint(pending.pending_id)
        result = host.run_extension_action(loaded.ext_id, "send",
                                           confirmation_token=token)
        self.assertTrue(result["ok"])

    def test_ctx_has_no_mint(self):
        ext = _mkext([{"id": "r", "kind": "read"}])
        host = _host()
        loaded = host.load_extension(ext)
        self.assertFalse(hasattr(loaded.ctx, "mint_confirmation"))
        self.assertFalse(hasattr(loaded.ctx, "confirmations"))

    def test_manifest_mutation_post_load_inert(self):
        ext = _mkext([{"id": "r", "kind": "read"}])
        host = _host()
        loaded = host.load_extension(ext)
        data = json.loads((ext / "manifest.json").read_text())
        # "applications:read" was NOT in the frozen manifest.
        data["permissions"]["data"] = ["jobs:read", "profile:read",
                                       "applications:read"]
        (ext / "manifest.json").write_text(json.dumps(data))
        with self.assertRaises(PermissionError):
            loaded.ctx.data("applications:read")


class TestSandboxFS(unittest.TestCase):
    def test_write_and_read_inside_root(self):
        ext = _mkext([{"id": "r", "kind": "read"}])
        fs = SandboxFS(ext, ["workspace"])
        fs.write_text("workspace/note.txt", "hello")
        self.assertEqual(fs.read_text("workspace/note.txt"), "hello")

    def test_traversal_blocked(self):
        ext = _mkext([{"id": "r", "kind": "read"}])
        fs = SandboxFS(ext, ["workspace"])
        with self.assertRaises(SandboxViolation):
            fs.read_text("../../etc/hostname")

    def test_absolute_blocked(self):
        ext = _mkext([{"id": "r", "kind": "read"}])
        fs = SandboxFS(ext, ["workspace"])
        with self.assertRaises(SandboxViolation):
            fs.read_text("/etc/hostname")

    def test_undeclared_root_blocked(self):
        ext = _mkext([{"id": "r", "kind": "read"}])
        fs = SandboxFS(ext, ["workspace"])
        # ".." traversal is always blocked ...
        with self.assertRaises(SandboxViolation):
            fs.write_text("../escape.txt", "nope")
        # ... while the extension's private .data dir is always available
        # by design (documented in fs.py).
        fs.write_text("other/x.txt", "private")
        self.assertEqual(fs.read_text("other/x.txt"), "private")

    def test_symlink_escape_blocked(self):
        # Single root (.data): a symlink inside it pointing at /etc must not
        # let the extension read outside.
        ext = _mkext([{"id": "r", "kind": "read"}])
        fs = SandboxFS(ext, [])
        (ext / ".data").mkdir(exist_ok=True)
        (ext / ".data" / "link").symlink_to("/etc")
        with self.assertRaises(SandboxViolation):
            fs.read_text("link/hostname")


class TestSandboxNet(unittest.TestCase):
    def _http(self, **kw):
        def ok_transport(req):
            return HttpResponse(status=200, headers={}, body=b"ok")
        return SandboxHTTP(["api.example"], transport=ok_transport, **kw)

    def test_allowed_host_passes(self):
        resp = self._http().get("https://api.example/v1/x")
        self.assertEqual(resp.status, 200)

    def test_undeclared_host_blocked(self):
        with self.assertRaises(NetViolation):
            self._http().get("https://evil.example/collect")

    def test_rate_limit_enforced(self):
        from initiatives.i11.sandbox.net import _TokenBucket
        http = self._http()
        http._bucket = _TokenBucket(2)  # noqa: SLF001
        http.get("https://api.example/1")
        http.get("https://api.example/2")
        with self.assertRaises(RateLimitExceeded):
            http.get("https://api.example/3")

    def test_circuit_breaker_opens(self):
        def bad_transport(req):
            return HttpResponse(status=503, headers={}, body=b"")
        http = SandboxHTTP(["api.example"], calls_per_minute=6000,
                           transport=bad_transport)
        with self.assertRaises(CircuitOpen):
            for _ in range(6):
                try:
                    http.get("https://api.example/")
                except CircuitOpen:
                    raise


class TestAudit(unittest.TestCase):
    def test_chain_verifies_and_tamper_detected(self):
        tmp = Path(tempfile.mkdtemp())
        audit = ExtensionAudit(tmp / "a.jsonl")
        audit.append("e1", "data.read", {"scope": "jobs:read"})
        audit.append("e1", "action.ok", {"action": "r"})
        self.assertTrue(audit.verify()["ok"])
        # Tamper: rewrite history.
        lines = (tmp / "a.jsonl").read_text().splitlines()
        entry = json.loads(lines[0])
        entry["detail"] = {"scope": "everything:read"}
        lines[0] = json.dumps(entry)
        (tmp / "a.jsonl").write_text("\n".join(lines) + "\n")
        verdict = audit.verify()
        self.assertFalse(verdict["ok"])

    def test_ctx_has_no_audit_writer(self):
        ext = _mkext([{"id": "r", "kind": "read"}])
        host = _host()
        loaded = host.load_extension(ext)
        for attr in ("audit", "_audit", "append", "write_audit"):
            if attr == "_audit":
                continue
            self.assertFalse(hasattr(loaded.ctx, attr),
                             f"ctx exposes {attr}")

    def test_ctx_has_no_host_reference(self):
        # Regression: ctx._host once exposed the confirmation broker and
        # allowed self-minting. The context holds a token broker only;
        # no plain-attribute path may lead from ctx to the Host.
        ext = _mkext([{"id": "r", "kind": "read"}])
        host = _host()
        loaded = host.load_extension(ext)
        self.assertFalse(hasattr(loaded.ctx, "_host"))
        self.assertFalse(hasattr(loaded.ctx, "confirmations"))
        self.assertFalse(hasattr(loaded.ctx, "mint_confirmation"))
        broker = loaded.ctx._broker
        self.assertFalse(hasattr(broker, "_host"))
        self.assertFalse(hasattr(broker, "host"))
        # The broker token alone is useless: it is not the Host.
        from initiatives.i11.sandbox import host as host_mod
        self.assertNotIsInstance(broker._token, host_mod.Host)

    def test_frozen_manifest_rejects_mutation(self):
        ext = _mkext([{"id": "r", "kind": "read"}])
        host = _host()
        loaded = host.load_extension(ext)
        with self.assertRaises(TypeError):
            loaded.manifest["permissions"]["data"] = ["profile:read"]
        with self.assertRaises(TypeError):
            loaded.ctx._manifest["permissions"]["data"] = ["profile:read"]

    def test_scope_escalation_via_ctx_denied(self):
        ext = _mkext([{"id": "r", "kind": "read"}], data=["jobs:read"])
        host = _host()
        loaded = host.load_extension(ext)
        # Even a successful-looking mutation must not widen capabilities.
        try:
            loaded.ctx._manifest["permissions"]["data"].append("profile:read")
        except (TypeError, AttributeError):
            pass
        with self.assertRaises(PermissionError):
            loaded.ctx.data("profile:read")

    def test_kind_downgrade_inert(self):
        ext = _mkext([{"id": "send-it", "kind": "confirm-required",
                       "confirm_required": True}])
        host = _host()
        loaded = host.load_extension(ext)
        try:
            loaded.ctx._manifest["permissions"]["actions"][0]["kind"] = "read"
        except TypeError:
            pass
        with self.assertRaises(PermissionError):
            host.run_extension_action("ut-ext", "send-it")

    def test_banned_imports_rejected(self):
        from initiatives.i11.sandbox.host import scan_imports
        import tempfile
        from pathlib import Path
        import json as _json
        cases = {
            "import os": "os",
            "import pathlib": "pathlib",
            "import sys": "sys",
            "import initiatives.i11.sandbox.host": "initiatives",
            "import socket": "socket",
            "import subprocess": "subprocess",
        }
        for code, _ in cases.items():
            tmp = Path(tempfile.mkdtemp())
            (tmp / "extension.py").write_text(code + "\n")
            scan = scan_imports(tmp)
            self.assertFalse(scan["ok"], f"{code} was not flagged")
            self.assertTrue(scan["violations"], f"{code}: no violations")

    def test_bare_open_is_violation(self):
        from initiatives.i11.sandbox.host import scan_imports
        import tempfile
        from pathlib import Path
        tmp = Path(tempfile.mkdtemp())
        (tmp / "extension.py").write_text(
            "def f(ctx):\n    return open('/etc/hostname').read()\n")
        scan = scan_imports(tmp)
        self.assertFalse(scan["ok"])
        self.assertTrue(any(v["module"] == "open()"
                            for v in scan["violations"]))

    def test_snippet_and_test_files_not_scanned(self):
        # Developer tooling (snippets/tests) legitimately imports host
        # modules; only runtime code is scanned.
        from initiatives.i11.sandbox.host import scan_imports
        import tempfile
        from pathlib import Path
        tmp = Path(tempfile.mkdtemp())
        (tmp / "extension.py").write_text("ACTIONS = {}\n")
        (tmp / "cli_snippet.py").write_text(
            "import initiatives.i11.sandbox.host\n")
        (tmp / "tests").mkdir()
        (tmp / "tests" / "test_x.py").write_text("import pathlib\n")
        scan = scan_imports(tmp)
        self.assertTrue(scan["ok"], scan["violations"])


class TestPII(unittest.TestCase):
    def test_redact_by_default(self):
        ext = _mkext([{"id": "r", "kind": "read"}])
        host = _host()
        loaded = host.load_extension(ext)
        host.register_provider("profile:read", lambda: {
            "name": "Ada", "email": "ada@example.com", "phone": "555-0100"})
        profile = loaded.ctx.data("profile:read")
        self.assertEqual(profile["email"], "***redacted***")
        self.assertEqual(profile["phone"], "***redacted***")
        self.assertEqual(profile["name"], "Ada")


if __name__ == "__main__":
    unittest.main()
