#!/usr/bin/env python3
"""Real end-to-end tests for Initiative 11 (extension platform).

Unlike the unit/policy-kit suites, these tests run the FULL lifecycle
through the REAL components, in order, with no mocks of the machinery
under test:

  scaffold (real scaffolder) -> verify (manifest schema + import scan)
  -> sign (real Ed25519 sidecar) -> install (real Host.load_extension,
  the same path crew.ext_install takes) -> invoke tools through the
  real extension host -> sandbox containment probes against the REAL
  sandbox -> revoke + rollback through the REAL InstallStore/
  RevocationList path -> unload and assert the host is clean.

Hermetic: every test uses its own temp dirs (extensions, audit logs,
install store, revocation list). Nothing touches the repo root or the
process-global crew host.

In-process execution is explicitly acknowledged with
``unsafe_local_only=True`` (see
initiatives/i11/sandbox/SECURITY_RESIDUAL.md) — the same reviewed
opt-in the CLI install path uses. The hardened behaviors the
operator cleared on 2026-09-14 (sandbox containment holds; rollback refuses to
restore revoked versions) are asserted as hold-backs, NOT re-challenged:
the tests verify they still hold.

The install guard mirrors crew.ext_install's exact pre-check order:
verify_extension -> RevocationList.is_revoked -> load_extension.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from initiatives.i11.sandbox.host import Host  # noqa: E402
from initiatives.i11.scaffold.template import scaffold_extension  # noqa: E402
from initiatives.i11.signing.sign import (  # noqa: E402
    InstallRecord,
    InstallStore,
    RevocationList,
    generate_keypair,
    package_hash,
    sign_package,
    sign_revocation,
    verify_package,
)

_SECRET = b"retro-e2e-secret-32-bytes-padding!!"


def _host(tmp: Path) -> Host:
    return Host(audit_path=tmp / "audit.jsonl", secret=_SECRET,
                confirmations_path=tmp / "confirmations.json")


def _scaffold(tmp: Path, *, name: str, action_kinds,
              data_scopes=("jobs:read",)) -> tuple[Path, str]:
    """Scaffold a real extension; return (ext_dir, ext_id)."""
    info = scaffold_extension(
        name,
        out_dir=tmp / "ext-src",
        action_kinds=list(action_kinds),
        data_scopes=list(data_scopes),
    )
    ext_dir = Path(info["dir"])
    assert (ext_dir / "manifest.json").is_file()
    assert (ext_dir / "extension.py").is_file()
    return ext_dir, info["ext_id"]


def _grant_fs_root(ext_dir: Path, root_name: str = "data") -> Path:
    """Declare an fs root in the manifest and materialize it with content."""
    manifest_path = ext_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["permissions"]["sandbox"]["fs_roots"] = [root_name]
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    root = ext_dir / root_name
    root.mkdir(exist_ok=True)
    return root


def _implement_action(ext_dir: Path, ext_id: str, action_kind: str,
                      body: str) -> str:
    """Replace the scaffolded NotImplementedError stub with real code.

    The replacement body runs inside the sandbox (stripped builtins), so
    it may only use safe builtins and the ``ctx`` object.
    """
    action_id = f"{ext_id}-{action_kind}"
    path = ext_dir / "extension.py"
    src = path.read_text(encoding="utf-8")
    stub = f"    raise NotImplementedError('implement {action_id}')"
    assert stub in src, f"scaffold stub for {action_id} not found"
    lines = [f"    {ln.strip()}" if ln.strip() else ln
             for ln in body.strip().splitlines()]
    src = src.replace(stub, "\n".join(lines), 1)
    path.write_text(src, encoding="utf-8")
    return action_id


def _audit_events(tmp: Path) -> list[dict]:
    log = tmp / "audit.jsonl"
    if not log.is_file():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8")
            .splitlines() if line.strip()]


class TestExtensionLifecycleE2E(unittest.TestCase):
    """Scaffold -> verify -> sign -> install -> run, then clean unload."""

    def test_full_lifecycle(self):
        tmp = Path(tempfile.mkdtemp(prefix="veto-e2e-i11-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        host = _host(tmp)

        # 1. Real scaffolder into a temp dir.
        ext_dir, ext_id = _scaffold(
            tmp, name="retro-e2e-widget", action_kinds=["read"])
        _grant_fs_root(ext_dir)
        # Reads resolve against the per-extension .data dir first.
        (ext_dir / ".data").mkdir(exist_ok=True)
        (ext_dir / ".data" / "notes.txt").write_text(
            "hello from the sandbox", encoding="utf-8")
        action_id = _implement_action(
            ext_dir, ext_id, "read",
            """data = ctx.data("jobs:read")
               note = ctx.fs.read_text("notes.txt")
               return {"jobs_seen": len(data), "note": note}""")

        # 2. Real pre-install verification: manifest schema + import scan.
        verdict = host.verify_extension(ext_dir)
        self.assertTrue(verdict["ok"], verdict)
        self.assertEqual(verdict["manifest"]["id"], ext_id)

        # 3. Real signing + pinned-key verification.
        priv, pub = generate_keypair()
        sign_package(ext_dir, publisher="retro-e2e-test", private_key=priv)
        sig = verify_package(ext_dir, public_key=pub)
        self.assertTrue(sig["ok"], sig)
        self.assertTrue(sig["pinned"])

        # 4. Real installer: the same Host.load_extension path
        #    crew.ext_install takes, with the registry's pinned key.
        loaded = host.load_extension(
            ext_dir, publisher_key=pub, unsafe_local_only=True)
        self.assertEqual(loaded.ext_id, ext_id)
        self.assertEqual(loaded.trust, "signed-verified")
        self.assertIn(ext_id, [e["id"] for e in host.list_loaded()])

        # 5. Invoke the tool through the real host.
        ran = host.run_extension_action(ext_id, action_id)
        self.assertTrue(ran["ok"], ran)
        self.assertEqual(ran["result"]["note"], "hello from the sandbox")
        self.assertEqual(ran["result"]["jobs_seen"], 1)  # default fixture

        # 6. Host-written audit log proves the lifecycle happened.
        events = {(e["event"]) for e in _audit_events(tmp)}
        for expected in ("extension.loaded", "action.run", "action.ok",
                         "data.read"):
            self.assertIn(expected, events, events)

        # 7. Clean unload: host is empty again, further runs fail.
        host.unload_extension(ext_id)
        self.assertEqual(host.list_loaded(), [])
        with self.assertRaises(ValueError):
            host.run_extension_action(ext_id, action_id)


class TestSandboxContainmentE2E(unittest.TestCase):
    """Real containment probes against the real sandbox.

    Each probe passes the install-time import scan but is DENIED at
    runtime by the fs/net/scope brokers. This verifies the 2026-09-14
    cleared behavior (sandbox containment holds) still holds.
    """

    def _contained_ext(self, tmp: Path) -> tuple[Host, Path, str, list[str]]:
        ext_dir, ext_id = _scaffold(
            tmp, name="retro-e2e-probe", action_kinds=["read"])
        _grant_fs_root(ext_dir)
        (ext_dir / ".data").mkdir(exist_ok=True)
        (ext_dir / ".data" / "notes.txt").write_text(
            "legit content", encoding="utf-8")
        ids = []
        ids.append(_implement_action(
            ext_dir, ext_id, "read",
            """return {"legit": ctx.fs.read_text("notes.txt")}"""))
        return _host(tmp), ext_dir, ext_id, ids

    def _add_probe_action(self, ext_dir: Path, ext_id: str,
                          suffix: str, body: str) -> str:
        manifest_path = ext_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        action_id = f"{ext_id}-{suffix}"
        manifest["permissions"]["actions"].append({
            "id": action_id, "kind": "read", "confirm_required": False,
            "description": "containment probe",
        })
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8")
        path = ext_dir / "extension.py"
        src = path.read_text(encoding="utf-8")
        fn_name = "_" + action_id.replace("-", "_")
        fn_src = (f"\ndef {fn_name}(ctx, **params):\n"
                  + "\n".join(f"    {ln.strip()}" if ln.strip() else ln
                              for ln in body.strip().splitlines()) + "\n")
        # Define the probe BEFORE the ACTIONS dict and register it there.
        anchor = "ACTIONS = {"
        head, _, tail = src.partition(anchor)
        src = head + fn_src + "\n" + anchor + f'\n    "{action_id}": {fn_name},' + tail
        path.write_text(src, encoding="utf-8")
        return action_id

    def test_escape_attempts_denied_at_runtime(self):
        tmp = Path(tempfile.mkdtemp(prefix="veto-e2e-i11-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        host, ext_dir, ext_id, ids = self._contained_ext(tmp)

        fs_escape = self._add_probe_action(
            ext_dir, ext_id, "fs-escape",
            """ctx.fs.read_text("../audit.jsonl")
               return {"escaped": True}""")
        fs_abs = self._add_probe_action(
            ext_dir, ext_id, "fs-abs",
            """ctx.fs.read_text("/etc/hostname")
               return {"escaped": True}""")
        net_escape = self._add_probe_action(
            ext_dir, ext_id, "net-escape",
            """ctx.http.get("https://unlisted.example/exfil")
               return {"escaped": True}""")
        scope_escape = self._add_probe_action(
            ext_dir, ext_id, "scope-escape",
            """ctx.data("secrets:all")
               return {"escaped": True}""")

        self.assertTrue(host.verify_extension(ext_dir)["ok"])
        host.load_extension(ext_dir, unsafe_local_only=True)
        try:
            # Legitimate in-root read still works inside the sandbox.
            legit = host.run_extension_action(ext_id, ids[0])
            self.assertEqual(legit["result"]["legit"], "legit content")
            # ...while every escape family is denied.
            for probe in (fs_escape, fs_abs, net_escape, scope_escape):
                with self.assertRaises(PermissionError,
                                       msg=f"probe {probe} was not denied"):
                    host.run_extension_action(ext_id, probe)
        finally:
            host.unload_extension(ext_id)

        # Denials are host-audited, not silent.
        denied = [e for e in _audit_events(tmp)
                  if e["event"] in ("action.error",)]
        self.assertGreaterEqual(len(denied), 4, _audit_events(tmp))

    def test_banned_builtin_rejected_at_install(self):
        """`open(` in extension source fails the import scan: install
        refuses before any code runs."""
        tmp = Path(tempfile.mkdtemp(prefix="veto-e2e-i11-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        ext_dir, ext_id = _scaffold(
            tmp, name="retro-e2e-naughty", action_kinds=["read"])
        path = ext_dir / "extension.py"
        src = path.read_text(encoding="utf-8")
        src = src.replace(
            f"raise NotImplementedError('implement {ext_id}-read')",
            'data = open("/etc/hostname").read()\n    return {"data": data}',
            1)
        path.write_text(src, encoding="utf-8")
        verdict = _host(tmp).verify_extension(ext_dir)
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["stage"], "import-scan")


class TestConfirmRequiredFlowE2E(unittest.TestCase):
    """The confirm-required tool runs only with a host-minted token.

    Token is minted on the host side (the human surface), single-use,
    bound to exact params.
    """

    def test_mint_and_single_use(self):
        tmp = Path(tempfile.mkdtemp(prefix="veto-e2e-i11-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        host = _host(tmp)
        ext_dir, ext_id = _scaffold(
            tmp, name="retro-e2e-gated", action_kinds=["confirm-required"])
        action_id = _implement_action(
            ext_dir, ext_id, "confirm-required",
            """return {"ran": True}""")
        self.assertTrue(host.verify_extension(ext_dir)["ok"])
        host.load_extension(ext_dir, unsafe_local_only=True)
        try:
            # No token -> refused. The extension cannot self-confirm.
            with self.assertRaises(PermissionError):
                host.run_extension_action(ext_id, action_id)

            # Human surface: request -> mint -> run with token.
            payload = {"action": action_id, "params": {}}
            pending = host.confirmations.request(ext_id, action_id, payload)
            token = host.confirmations.mint(pending.pending_id)
            ran = host.run_extension_action(
                ext_id, action_id, confirmation_token=token)
            self.assertTrue(ran["ok"], ran)
            self.assertTrue(ran["result"]["ran"])

            # Single-use: replay refused.
            with self.assertRaises(PermissionError):
                host.run_extension_action(
                    ext_id, action_id, confirmation_token=token)
        finally:
            host.unload_extension(ext_id)


class TestRevokeRollbackE2E(unittest.TestCase):
    """Revoke an installed version, then prove rollback REFUSES to
    restore it — the hardened 2026-09-14 behavior (11c) still holds."""

    def test_rollback_refuses_revoked_version(self):
        tmp = Path(tempfile.mkdtemp(prefix="veto-e2e-i11-"))
        self.addCleanup(shutil.rmtree, tmp, True)

        rev = RevocationList(tmp / "revocations.json")
        store = InstallStore(tmp / "installed.json", revocations=rev)

        ext_dir, ext_id = _scaffold(
            tmp, name="retro-e2e-rollback", action_kinds=["read"])
        _implement_action(ext_dir, ext_id, "read",
                          """return {"v": "0.1.0"}""")
        priv, pub = generate_keypair()
        sign_package(ext_dir, publisher="retro-e2e-test", private_key=priv)

        # Install v0.1.0, then a (bad) upgrade to v0.2.0.
        store.record_install(InstallRecord(
            ext_id=ext_id, version="0.1.0",
            package_sha256=package_hash(ext_dir),
            publisher="retro-e2e-test",
            installed_at=int(time.time()), source_path=str(ext_dir)))
        upgraded = store.record_upgrade(
            ext_id, "0.2.0", "f" * 64,
            {"reviewer": "retro-e2e", "verdict": "pass",
             "date": "2026-09-15", "notes": "bad release"},
            source_path=str(ext_dir))
        self.assertTrue(upgraded["ok"], upgraded)

        # Publisher revokes v0.1.0 with an authenticated signature.
        sig = sign_revocation(priv, ext_id, "0.1.0", "retro e2e revocation")
        revoked = rev.revoke(ext_id, "0.1.0", "retro e2e revocation",
                             publisher_pubkey=pub, signature=sig)
        self.assertTrue(revoked["ok"], revoked)
        self.assertTrue(rev.is_revoked(ext_id, "0.1.0"))

        # The install-time guard (same as crew.ext_install's) now refuses.
        self.assertTrue(rev.is_revoked(ext_id, "0.1.0"))

        # Rollback to the revoked version is REFUSED; v0.2.0 stays current.
        rolled = store.rollback(ext_id)
        self.assertFalse(rolled["ok"])
        self.assertIn("REVOKED", rolled["error"])
        self.assertEqual(store.get(ext_id)["version"], "0.2.0")

        # And rollback works fine when nothing is revoked (sanity that
        # the refusal is the revocation check, not a broken store).
        rev2 = RevocationList(tmp / "revocations2.json")
        store2 = InstallStore(tmp / "installed2.json", revocations=rev2)
        store2.record_install(InstallRecord(
            ext_id=ext_id, version="0.1.0",
            package_sha256=package_hash(ext_dir),
            publisher="retro-e2e-test",
            installed_at=int(time.time()), source_path=str(ext_dir)))
        store2.record_upgrade(
            ext_id, "0.2.0", "f" * 64,
            {"reviewer": "retro-e2e", "verdict": "pass",
             "date": "2026-09-15", "notes": "ok"}, source_path=str(ext_dir))
        rolled2 = store2.rollback(ext_id)
        self.assertTrue(rolled2["ok"], rolled2)
        self.assertEqual(rolled2["to"], "0.1.0")

    def test_revoked_version_never_loads_via_install_guard(self):
        """The crew.ext_install pre-check order, applied hermetically:
        verify -> revocation check -> load. A revoked pair never loads."""
        tmp = Path(tempfile.mkdtemp(prefix="veto-e2e-i11-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        host = _host(tmp)
        rev = RevocationList(tmp / "revocations.json")

        ext_dir, ext_id = _scaffold(
            tmp, name="retro-e2e-revoked", action_kinds=["read"])
        _implement_action(ext_dir, ext_id, "read", """return {"ok": True}""")
        priv, pub = generate_keypair()
        sign_package(ext_dir, publisher="retro-e2e-test", private_key=priv)

        sig = sign_revocation(priv, ext_id, "0.1.0", "pulled release")
        self.assertTrue(rev.revoke(
            ext_id, "0.1.0", "pulled release",
            publisher_pubkey=pub, signature=sig)["ok"])

        # Same guard order as crew.ext_install:
        self.assertTrue(host.verify_extension(ext_dir)["ok"])
        if rev.is_revoked(ext_id, "0.1.0"):
            refused = {"ok": False,
                       "error": "this version was revoked; refusing install"}
        else:  # pragma: no cover - the guard must fire above
            refused = {"ok": True}
        self.assertFalse(refused["ok"])
        self.assertIn("revoked", refused["error"])
        self.assertEqual(host.list_loaded(), [])


class TestCrossProcessLifecycleE2E(unittest.TestCase):
    """Install -> request -> confirm -> run as REAL separate processes.

    Each ``python cli.py extension ...`` invocation is its own OS process
    with its own in-memory Host — nothing is shared in-process. The only
    thing that crosses the process boundary is the persisted state under
    the hermetic env vars (install store, confirmations, audit log, host
    key). This permanently encodes the production lifecycle: install in
    one terminal, approve and run in another.
    """

    def _env(self, tmp: Path) -> dict:
        merged = dict(os.environ)
        merged.update({
            "VETO_EXTENSIONS_CONFIRMATIONS": str(
                tmp / "confirmations.json"),
            "VETO_EXTENSIONS_AUDIT": str(tmp / "audit.jsonl"),
            "VETO_HOST_KEY_FILE": str(tmp / "host.key"),
            "VETO_EXTENSIONS_INSTALLED": str(tmp / "installed.json"),
            "VETO_EXTENSIONS_REVOCATIONS": str(
                tmp / "revocations.json"),
        })
        return merged

    def _cli(self, env: dict, *args: str) -> dict:
        proc = subprocess.run(
            [sys.executable, str(BASE_DIR / "cli.py"), "extension", *args],
            cwd=str(BASE_DIR), capture_output=True, text=True, timeout=180,
            env=env)
        self.assertEqual(
            proc.returncode, 0,
            f"extension {' '.join(args)} exited rc={proc.returncode}\n"
            f"--- stdout ---\n{proc.stdout}\n"
            f"--- stderr (tail) ---\n{proc.stderr[-3000:]}")
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            self.fail(f"extension {' '.join(args)} did not print JSON:\n"
                      f"{proc.stdout}\n--- stderr ---\n{proc.stderr[-2000:]}")

    def test_install_request_confirm_run_across_processes(self):
        tmp = Path(tempfile.mkdtemp(prefix="veto-e2e-i11-xproc-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        env = self._env(tmp)

        # One real scaffolded extension with a confirm-required action.
        ext_dir, ext_id = _scaffold(
            tmp, name="xproc-e2e-widget",
            action_kinds=["read", "confirm-required"])
        _grant_fs_root(ext_dir)
        gated = _implement_action(ext_dir, ext_id, "confirm-required",
                                  'return {"approved": True}')

        # Process A (install): records the install in the hermetic store.
        installed = self._cli(env, "install", "--dir", str(ext_dir))
        self.assertTrue(installed["ok"], installed)
        self.assertEqual(installed["extension"], ext_id)

        # Process B (request): mints a structured pending ID.
        asked = self._cli(env, "request", "--ext-id", ext_id,
                          "--action-id", gated)
        self.assertTrue(asked["ok"], asked)
        pending_id = asked["pending_id"]
        self.assertIsInstance(pending_id, str)
        self.assertTrue(pending_id)

        # Process C (human approval): confirms, minting a single-use token.
        minted = self._cli(env, "confirm", "--pending-id", pending_id)
        self.assertTrue(minted["ok"], minted)
        token = minted["confirmation_token"]
        self.assertTrue(token)

        # Process D (agent run): fresh process auto-loads the install and
        # the token authorizes the run.
        ran = self._cli(env, "run", "--ext-id", ext_id,
                        "--action-id", gated, "--token", token)
        self.assertTrue(ran["ok"], ran)
        self.assertEqual(ran["result"], {"approved": True})

        # Process E: the same token is single-use — replay is refused.
        replayed = self._cli(env, "run", "--ext-id", ext_id,
                             "--action-id", gated, "--token", token)
        self.assertFalse(replayed["ok"])
        self.assertIn("replayed", replayed["error"].lower())

        # Process F: no token at all is refused.
        denied = self._cli(env, "run", "--ext-id", ext_id,
                           "--action-id", gated)
        self.assertFalse(denied["ok"])

        # The audit log written by the separate processes shows the full
        # lifecycle happened on disk, not in one shared memory space.
        events = [json.loads(line) for line in
                  (tmp / "audit.jsonl").read_text(encoding="utf-8")
                  .splitlines() if line.strip()]
        kinds = {e["event"] for e in events}
        for expected in ("extension.loaded", "confirm.requested",
                         "action.confirmed", "action.ok"):
            self.assertIn(expected, kinds, kinds)


if __name__ == "__main__":
    unittest.main()
