#!/usr/bin/env python3
"""Extension host: capability broker, confirmation gate, and runtime.

This is the enforcement point for the hard rule: **an extension can prove
what it accesses and CANNOT bypass the core confirmation or governance
gates.**

How the guarantees hold:

1. **Frozen capabilities.** The manifest is validated at load; the runtime
   snapshots the capability set. Later manifest edits cannot widen a
   loaded extension.
2. **Brokered powers.** Extension code never receives references to Veto
   core modules. It receives an ``ExtensionContext`` exposing only the
   capabilities its manifest declares (data scopes, fs roots, network
   destinations). Filesystem, network, and data access all run through
   host checks first.
3. **Confirmation cannot be self-minted.** ``request_confirmation()``
   creates a *pending* request. Only host UI code (CLI/web/terminal —
   never extension code) may call ``Host.mint_confirmation()`` after the
   human approves. Tokens are HMAC-bound to (extension, action, payload
   hash, expiry) and single-use; a forged or replayed token is rejected.
4. **Static import scan.** Install/verify rejects extension code that
   imports Veto core modules (``server``, ``compliance``,
   ``apply_queue``, ``browser_apply``) or raw network/subprocess
   primitives — the bypass routes are closed at install time, not just
   at runtime.
5. **Governance veto.** ``confirm-required`` actions additionally pass the
   user's agentic-governance veto screen; a veto blocks even a confirmed
   action. Extensions cannot weaken this — the screen runs in the host.
6. **Host-only audit.** Every brokered action is appended to the
   hash-chained audit log. Extension code gets a read-only view of its
   own entries, never a write handle.
"""

from __future__ import annotations

import ast
import base64
import hashlib
import hmac
import importlib.util
import json
import os
import secrets
import time
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from ..manifest.schema import ManifestError, load_manifest, manifest_summary
from .audit import ExtensionAudit
from .broker import (Broker, ExtensionContext, issue_broker_token,
                     revoke_broker_token)
from .fs import SandboxFS, SandboxViolation as FSSandboxViolation
from .net import SandboxHTTP, SandboxViolation as NetSandboxViolation

SandboxViolation = (FSSandboxViolation, NetSandboxViolation)

# Runtime state defaults to the user's veto dir, never the repo tree.
HOST_KEY_FILE = Path.home() / ".veto" / "extension_host.key"
DEFAULT_AUDIT_PATH = Path.home() / ".veto" / "extensions_audit.jsonl"

#: Imports that let extension code bypass the broker. Rejected at
#: install/verify time — fail closed.
#:
#: Two classes of bypass are closed here:
#: 1. *Host-module reach.* ``initiatives`` (this platform's own package):
#:    importing it would hand extension code ``_host_secret()`` and the
#:    ``Host``/``ConfirmationBroker`` classes — a direct path to forging
#:    confirmation tokens.
#: 2. *Sandbox escape.* ``os``/``pathlib``/``io``/``shutil``/``tempfile``
#:    (raw filesystem outside the declared fs roots, bypassing PII
#:    redaction), ``socket``/``requests``/``httpx``/``urllib*`` (raw
#:    network outside declared destinations), ``subprocess``/``ctypes``/
#:    ``pty``/``multiprocessing`` (process escape), ``sys``/``gc``/
#:    ``inspect``/``importlib`` (runtime introspection toward host
#:    internals).
#: File access for extensions goes exclusively through ``ctx.fs``; network
#: exclusively through ``ctx.http``.
BANNED_IMPORTS = {
    "server", "compliance", "apply_queue", "browser_apply", "cli",
    "dashboard", "webui", "governance",
    "initiatives",
    "socket", "requests", "httpx", "urllib.request", "urllib3",
    "subprocess", "ctypes", "pty", "multiprocessing",
    "os", "sys", "pathlib", "io", "shutil", "tempfile",
    "gc", "inspect", "importlib",
}

PII_FIELD_HINTS = ("email", "e-mail", "phone", "tel", "address", "ssn")


# ---------------------------------------------------------------------------
# Host secret + confirmation tokens
# ---------------------------------------------------------------------------

def _host_secret() -> bytes:
    """Per-install host secret (0600). Extension code never sees this."""
    key_file = Path(os.environ.get("VETO_HOST_KEY_FILE", str(HOST_KEY_FILE)))
    try:
        if key_file.is_file():
            return key_file.read_bytes()
    except OSError:
        pass
    secret = secrets.token_bytes(32)
    try:
        key_file.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(key_file), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(secret)
    except OSError:
        pass
    return secret


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64url(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


@dataclass
class PendingConfirmation:
    pending_id: str
    ext_id: str
    action_id: str
    payload: dict[str, Any]
    payload_sha: str
    created_at: float
    expires_at: float


class ConfirmationBroker:
    """Issues and verifies single-use, HMAC-bound confirmation tokens.

    The extension may *request*; only the host (human-facing UI) may
    *mint*. ``mint`` is never exposed through ``ExtensionContext``.
    """

    TOKEN_TTL_S = 15 * 60

    def __init__(self, secret: bytes | None = None) -> None:
        self._secret = secret if secret is not None else _host_secret()
        self._pending: dict[str, PendingConfirmation] = {}
        self._used_nonces: dict[str, float] = {}  # nonce -> exp (pruned)

    # -- extension-visible -------------------------------------------------
    def request(self, ext_id: str, action_id: str,
                payload: dict[str, Any]) -> PendingConfirmation:
        payload_sha = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()
        pending = PendingConfirmation(
            pending_id="pc_" + secrets.token_hex(8),
            ext_id=ext_id,
            action_id=action_id,
            payload=payload,
            payload_sha=payload_sha,
            created_at=time.time(),
            expires_at=time.time() + self.TOKEN_TTL_S,
        )
        self._pending[pending.pending_id] = pending
        return pending

    # -- host-only ----------------------------------------------------------
    def mint(self, pending_id: str) -> str:
        """Mint a confirmation token. Host UI only — call after the human
        explicitly approves the pending request."""
        pending = self._pending.get(pending_id)
        if pending is None:
            raise ValueError(f"unknown pending confirmation {pending_id!r}")
        if time.time() > pending.expires_at:
            del self._pending[pending_id]
            raise ValueError("pending confirmation expired")
        body = {
            "ext_id": pending.ext_id,
            "action_id": pending.action_id,
            "payload_sha": pending.payload_sha,
            "exp": int(pending.expires_at),
            "nonce": secrets.token_hex(16),
        }
        raw = json.dumps(body, sort_keys=True).encode()
        sig = hmac.new(self._secret, raw, hashlib.sha256).hexdigest()
        del self._pending[pending_id]
        return _b64url(raw) + "." + sig

    def verify(self, token: str, *, ext_id: str, action_id: str,
               payload: dict[str, Any]) -> bool:
        """Verify a token is genuine, unexpired, single-use, and bound to
        this exact (extension, action, payload)."""
        try:
            raw_b64, sig = token.rsplit(".", 1)
            raw = _unb64url(raw_b64)
        except (ValueError, base64.binascii.Error):
            return False
        expected = hmac.new(self._secret, raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, sig):
            return False  # forged or wrong host secret
        try:
            body = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return False
        if not isinstance(body, dict):
            return False  # structurally invalid token body
        now = time.time()
        # Opportunistically prune expired nonces so the replay set
        # cannot grow without bound.
        if len(self._used_nonces) > 1024:
            self._used_nonces = {n: e for n, e in self._used_nonces.items()
                                 if e > now}
        if body.get("nonce") in self._used_nonces:
            return False  # replay
        if now > float(body.get("exp", 0)):
            return False  # expired
        if body.get("ext_id") != ext_id or body.get("action_id") != action_id:
            return False  # bound to a different extension/action
        payload_sha = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()
        if not hmac.compare_digest(str(body.get("payload_sha", "")), payload_sha):
            return False  # payload was swapped after confirmation
        self._used_nonces[body["nonce"]] = float(body.get("exp", 0))
        return True

    def pending_requests(self) -> list[dict[str, Any]]:
        now = time.time()
        return [
            {"pending_id": p.pending_id, "ext_id": p.ext_id,
             "action_id": p.action_id, "payload": p.payload,
             "expires_in_s": max(0, int(p.expires_at - now))}
            for p in self._pending.values() if p.expires_at > now
        ]


# ---------------------------------------------------------------------------
# Static import scan (install-time security gate)
# ---------------------------------------------------------------------------

def scan_imports(ext_dir: str | Path) -> dict[str, Any]:
    """AST-scan extension code for banned imports.

    Returns {ok, violations:[{file, lineno, module}], warnings:[...]}.
    Banned modules are a hard failure; bare ``open()`` calls are a hard
    failure too — extensions must use ``ctx.fs`` so every read/write stays
    inside the declared fs roots and the host's audit trail.
    """
    ext_dir = Path(ext_dir)
    violations: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    # Developer tooling is not extension runtime code and is not scanned:
    # - tests/ and docs/ (author's own tests and docs)
    # - *_snippet.py / wizard_step.py (generated for the HOST integrator
    #   to copy into cli.py / wizard.py / MCP server — they run as host
    #   code, not extension code, and legitimately import host modules)
    # Everything else (*.py at any depth) is runtime code and is scanned.
    skip_names = {"wizard_step.py"}
    for py_file in sorted(ext_dir.rglob("*.py")):
        if ".data" in py_file.parts:
            continue
        rel = str(py_file.relative_to(ext_dir))
        parts = py_file.relative_to(ext_dir).parts
        if parts[0] in ("tests", "docs"):
            continue
        if py_file.name in skip_names or py_file.name.endswith("_snippet.py"):
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"),
                             filename=str(py_file))
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:
            violations.append({"file": str(py_file), "lineno": 0,
                               "module": f"<unparseable: {exc}>"})
            continue
        rel = str(py_file.relative_to(ext_dir))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top in BANNED_IMPORTS:
                        violations.append({"file": rel, "lineno": node.lineno,
                                           "module": alias.name})
            elif isinstance(node, ast.ImportFrom):
                top = (node.module or "").split(".")[0]
                if top in BANNED_IMPORTS:
                    violations.append({"file": rel, "lineno": node.lineno,
                                       "module": node.module})
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "open":
                    violations.append({"file": rel, "lineno": node.lineno,
                                       "module": "open()",
                                       "detail": "bare open() bypasses the "
                                       "fs sandbox; use ctx.fs instead"})
    return {"ok": not violations, "violations": violations,
            "warnings": warnings}


# ---------------------------------------------------------------------------
# PII redaction
# ---------------------------------------------------------------------------

def redact_pii(value: Any) -> Any:
    """Recursively mask PII-hint fields in data handed to extensions."""
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, val in value.items():
            lowered = str(key).lower()
            if any(hint in lowered for hint in PII_FIELD_HINTS):
                out[key] = "***redacted***" if not isinstance(val, str) else "***redacted***"
            else:
                out[key] = redact_pii(val)
        return out
    if isinstance(value, list):
        return [redact_pii(v) for v in value]
    return value


# ---------------------------------------------------------------------------
# Data providers (contract-first seam)
# ---------------------------------------------------------------------------
# Core (or Initiative 09 connectors) register callables here:
#   register_data_provider("jobs:read", lambda: [...])
# The platform defines the interface; the integration sweep wires the
# real providers (see integration_notes.md).

_DATA_PROVIDERS: dict[str, Callable[[], Any]] = {}


def register_data_provider(scope: str, fn: Callable[[], Any]) -> None:
    _DATA_PROVIDERS[scope] = fn


def _default_providers() -> dict[str, Callable[[], Any]]:
    # Synthetic, clearly-labeled fixtures so the platform and its tests
    # run without core wiring. Real providers replace these.
    return {
        "jobs:read": lambda: [{"id": "syn-job-1", "title": "Synthetic fixture role",
                               "company": "Fixture Corp",
                               "_synthetic": True}],
        "applications:read": lambda: [],
        "profile:read": lambda: {"name": "Synthetic User",
                                 "email": "user@example.com",
                                 "_synthetic": True},
        "outcomes:read": lambda: [],
        "lifecycle:read": lambda: [],
        "watches:read": lambda: [],
    }


# ---------------------------------------------------------------------------
# Frozen manifests + capability broker
# ---------------------------------------------------------------------------
# The manifest is the ONLY authority for what an extension may do. It is
# deep-frozen (immutable) at load so extension code can never widen its own
# capabilities at runtime — e.g. ``ctx``-reachable structures cannot be
# mutated to add a data scope or downgrade an action's kind. Every host
# enforcement check reads the frozen manifest, never extension-reachable
# mutable state.

def _freeze(value: Any) -> Any:
    """Recursively convert a manifest to immutable structures."""
    if isinstance(value, dict):
        return MappingProxy({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(v) for v in value)
    return value


class MappingProxy(dict):
    """A dict that raises on any mutation attempt.

    Subclassing dict (rather than types.MappingProxyType) keeps ``isinstance``
    checks and ``.get``/iteration working while ``__setitem__``/``__delitem__``
    fail loudly.
    """

    def __setitem__(self, key: Any, value: Any) -> None:  # type: ignore[override]
        raise TypeError("frozen manifest: mutation denied")

    def __delitem__(self, key: Any) -> None:  # type: ignore[override]
        raise TypeError("frozen manifest: mutation denied")

    def clear(self) -> None:  # type: ignore[override]
        raise TypeError("frozen manifest: mutation denied")

    def pop(self, *args: Any) -> Any:
        raise TypeError("frozen manifest: mutation denied")

    def popitem(self) -> Any:
        raise TypeError("frozen manifest: mutation denied")

    def setdefault(self, *args: Any) -> Any:
        raise TypeError("frozen manifest: mutation denied")

    def update(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        raise TypeError("frozen manifest: mutation denied")


# ---------------------------------------------------------------------------

@dataclass
class LoadedExtension:
    ext_id: str
    dir: Path
    manifest: Any  # deep-frozen (see _freeze); mutation raises TypeError
    module: types.ModuleType
    ctx: ExtensionContext
    fs: SandboxFS
    http: SandboxHTTP
    broker_token: str = ""
    trust: str = "local-unsigned"


class Host:
    """Loads extensions, freezes capabilities, brokers every sensitive op."""

    def __init__(self, audit_path: str | Path | None = None,
                 secret: bytes | None = None) -> None:
        default_audit = Path(os.environ.get("VETO_EXTENSIONS_AUDIT",
                                            str(DEFAULT_AUDIT_PATH)))
        self.audit = ExtensionAudit(audit_path or default_audit)
        self.confirmations = ConfirmationBroker(secret=secret)
        self._loaded: dict[str, LoadedExtension] = {}
        self._providers: dict[str, Callable[[], Any]] = _default_providers()
        self._providers.update(_DATA_PROVIDERS)

    # -- data providers -------------------------------------------------------
    def register_provider(self, scope: str, fn: Callable[[], Any]) -> None:
        self._providers[scope] = fn

    def _data_for(self, ext_id: str, scope: str) -> Any:
        loaded = self._loaded[ext_id]
        # Read the frozen manifest — never extension-reachable mutable state.
        declared = set(loaded.manifest["permissions"]["data"])
        if scope not in declared:
            self.audit.append(ext_id, "data.denied",
                              {"scope": scope, "reason": "not declared"})
            raise PermissionError(
                f"extension {ext_id!r} did not declare data scope {scope!r}")
        fn = self._providers.get(scope)
        if fn is None:
            raise RuntimeError(f"no provider registered for scope {scope!r}")
        try:
            value = fn()
        except Exception as exc:
            raise RuntimeError(f"data provider {scope!r} failed: {exc}") from exc
        if loaded.manifest["permissions"]["pii"] == "redact":
            value = redact_pii(value)
        self.audit.append(ext_id, "data.read",
                          {"scope": scope,
                           "pii": loaded.manifest["permissions"]["pii"]})
        return value

    def _fs_for(self, ext_id: str) -> SandboxFS:
        return self._loaded[ext_id].fs

    def _http_for(self, ext_id: str) -> SandboxHTTP:
        return self._loaded[ext_id].http

    # -- drafts / notifications --------------------------------------------------
    def _draft_artifact(self, ext_id: str, name: str, content: str) -> str:
        loaded = self._loaded[ext_id]
        kinds = {a["kind"] for a in loaded.manifest["permissions"]["actions"]}
        if "draft" not in kinds and "preview" not in kinds:
            raise PermissionError(
                f"extension {ext_id!r} declares no draft/preview action")
        safe = "".join(c if (c.isalnum() or c in "-_.") else "_"
                       for c in name).strip("._") or "draft"
        loaded.fs.write_text(f"drafts/{safe}.md", content)
        self.audit.append(ext_id, "draft.created", {"name": safe})
        return f"drafts/{safe}.md"

    def _queue_notification(self, ext_id: str, title: str, body: str) -> str:
        loaded = self._loaded[ext_id]
        kinds = {a["id"] for a in loaded.manifest["permissions"]["actions"]
                 if a["kind"] == "notify"}
        if not kinds:
            raise PermissionError(
                f"extension {ext_id!r} declares no notify action")
        nid = "nq_" + secrets.token_hex(8)
        # Notifications are proposals: the host notification center shows
        # them; nothing is sent by the extension.
        loaded.fs.write_text(f"notifications/{nid}.json",
                             json.dumps({"title": title, "body": body,
                                         "queued_at": time.time()}))
        self.audit.append(ext_id, "notify.queued",
                          {"id": nid, "title": title,
                           "note": "proposal only; user confirms in host UI"})
        return nid

    # -- confirmation -------------------------------------------------------------
    def _request_confirmation(self, ext_id: str, action_id: str,
                              payload: dict[str, Any]) -> PendingConfirmation:
        loaded = self._loaded[ext_id]
        # Action lookup reads the FROZEN manifest — never the context's
        # mutable surface — so kind-downgrade attempts are inert.
        action = next((a for a in loaded.manifest["permissions"]["actions"]
                       if a["id"] == action_id), None)
        if action is None:
            raise ValueError(f"unknown action {action_id!r}")
        if action["kind"] != "confirm-required":
            raise ValueError(
                f"action {action_id!r} is kind {action['kind']!r}; only "
                "confirm-required actions use the confirmation broker")
        pending = self.confirmations.request(ext_id, action_id, payload)
        self.audit.append(ext_id, "confirm.requested",
                          {"action": action_id, "pending_id": pending.pending_id,
                           "payload_sha": pending.payload_sha})
        return pending

    def _governance_veto_screen(self, ext_id: str, action_id: str,
                                payload: dict[str, Any]) -> list[str]:
        """Defense in depth: run the user's governance veto screen on a
        confirm-required action description. A veto blocks even a confirmed
        action. Never raises; unavailable framework degrades to no-op with
        a warning (deterministic gates below still hold)."""
        try:
            from governance import adapter as _gov
        except Exception:
            return ["governance unavailable; deterministic gates only"]
        try:
            if not _gov.governance_enabled():
                return []
            result = _gov.check_veto(
                domain=getattr(_gov, "GOVERNANCE_DOMAIN", "job-apply"),
                text=(f"Extension {ext_id} requests confirm-required action "
                      f"{action_id} with payload {json.dumps(payload)[:500]}"),
            )
        except Exception as exc:
            return [f"governance screen error (fail-open advisory): {exc}"]
        hits = []
        if isinstance(result, dict):
            hits = result.get("hits", []) or []
            if result.get("vetoed"):
                hits = hits or ["vetoed"]
        elif result:
            hits = ["vetoed"]
        return [str(h) for h in hits]

    # -- loading ---------------------------------------------------------------------
    def verify_extension(self, ext_dir: str | Path) -> dict[str, Any]:
        """Full pre-load verification: manifest + import scan. Fail closed."""
        ext_dir = Path(ext_dir)
        try:
            manifest = load_manifest(ext_dir)
        except ManifestError as exc:
            return {"ok": False, "stage": "manifest", "error": str(exc)}
        scan = scan_imports(ext_dir)
        if not scan["ok"]:
            return {"ok": False, "stage": "import-scan",
                    "error": f"banned imports: {scan['violations']}",
                    "scan": scan}
        entry = ext_dir / "extension.py"
        if not entry.is_file():
            return {"ok": False, "stage": "entrypoint",
                    "error": "missing extension.py entrypoint"}
        return {"ok": True, "manifest": manifest_summary(manifest),
                "scan": scan}

    def load_extension(self, ext_dir: str | Path,
                       trust: str = "local-unsigned") -> LoadedExtension:
        """Verify, freeze capabilities, and load an extension module.

        The module is executed with a globals dict containing ONLY
        ``ctx`` — an ExtensionContext holding a capability broker, never
        the Host itself (no ``ctx._host`` path to the confirmation
        broker). Static bypass routes are closed by the import scan at
        verify time. Capabilities are deep-frozen from the manifest here;
        later manifest edits are inert.
        """
        verdict = self.verify_extension(ext_dir)
        if not verdict["ok"]:
            raise ManifestError(
                f"extension failed verification at stage "
                f"{verdict['stage']}: {verdict.get('error')}")
        ext_dir = Path(ext_dir).resolve()
        manifest = load_manifest(ext_dir)  # re-load post-verify; frozen below
        frozen = _freeze(manifest)  # deep-immutable: later edits inert,
        # and extension code cannot widen its own capabilities at runtime.

        perms = frozen["permissions"]
        fs = SandboxFS(ext_dir, perms["sandbox"]["fs_roots"])
        http = SandboxHTTP(perms["network"]["destinations"],
                           calls_per_minute=perms["sandbox"]["rate_limit"]["calls_per_minute"])

        module = types.ModuleType(f"veto_ext_{frozen['id']}")
        module.__dict__["__veto_extension__"] = True
        spec = importlib.util.spec_from_file_location(
            module.__name__, ext_dir / "extension.py")
        if spec is None or spec.loader is None:
            raise ManifestError("cannot create module spec for extension.py")

        host_self = self
        ext_id = frozen["id"]

        # The extension entrypoint receives exactly one host object: an
        # ExtensionContext holding a token broker — never the Host itself.
        # The broker and context classes live in broker.py, whose module
        # globals contain nothing dangerous.
        broker_token = issue_broker_token(host_self)
        broker = Broker(broker_token, ext_id)
        ctx = ExtensionContext(broker, ext_id, frozen)
        # Register BEFORE exec so re-entrant ctx.data() calls during import
        # resolve; capabilities are already frozen from the manifest.
        self._loaded[ext_id] = LoadedExtension(
            ext_id=ext_id, dir=ext_dir, manifest=frozen, module=module,
            ctx=ctx, fs=fs, http=http, broker_token=broker_token,
            trust=trust)
        module.__dict__["ctx"] = ctx
        try:
            spec.loader.exec_module(module)
        except Exception:
            del self._loaded[ext_id]
            revoke_broker_token(broker_token)
            raise
        self.audit.append(ext_id, "extension.loaded",
                          {"version": frozen["version"], "trust": trust,
                           "capabilities": manifest_summary(frozen)})
        return self._loaded[ext_id]

    def unload_extension(self, ext_id: str) -> None:
        loaded = self._loaded.pop(ext_id, None)
        if loaded is not None:
            revoke_broker_token(loaded.broker_token)
            self.audit.append(ext_id, "extension.unloaded", {})

    # -- action execution ---------------------------------------------------------------
    def run_extension_action(self, ext_id: str, action_id: str,
                             confirmation_token: str | None = None,
                             **kwargs: Any) -> dict[str, Any]:
        """Execute a declared action through the broker.

        - read/draft/preview/notify: run directly (side-effect-free or
          host-mediated).
        - confirm-required: requires a valid, single-use, HMAC-bound
          confirmation token minted by the host AFTER human approval, plus
          a governance veto screen. No token → no execution. Period.
        """
        loaded = self._loaded.get(ext_id)
        if loaded is None:
            raise ValueError(f"extension {ext_id!r} is not loaded")
        action = next((a for a in loaded.manifest["permissions"]["actions"]
                       if a["id"] == action_id), None)
        if action is None:
            self.audit.append(ext_id, "action.denied",
                              {"action": action_id, "reason": "undeclared"})
            raise ValueError(f"action {action_id!r} is not declared")
        fn = getattr(loaded.module, "ACTIONS", {}).get(action_id)
        if not callable(fn):
            raise ValueError(
                f"extension {ext_id!r} declares action {action_id!r} "
                "but extension.py has no matching ACTIONS entry")

        if action["kind"] == "confirm-required":
            if not confirmation_token:
                self.audit.append(ext_id, "action.denied",
                                  {"action": action_id,
                                   "reason": "missing confirmation token"})
                raise PermissionError(
                    f"action {action_id!r} requires a host-minted "
                    "confirmation token; the extension cannot self-confirm")
            payload = {"action": action_id, "params": kwargs}
            if not self.confirmations.verify(
                    confirmation_token, ext_id=ext_id,
                    action_id=action_id, payload=payload):
                self.audit.append(ext_id, "action.denied",
                                  {"action": action_id,
                                   "reason": "invalid/forged/expired/replayed "
                                             "confirmation token"})
                raise PermissionError(
                    f"confirmation token for {action_id!r} is invalid, "
                    "expired, replayed, or bound to a different payload")
            veto_hits = self._governance_veto_screen(ext_id, action_id, payload)
            hard_veto = any(h == "vetoed" for h in veto_hits)
            if hard_veto:
                self.audit.append(ext_id, "action.vetoed",
                                  {"action": action_id, "hits": veto_hits})
                raise PermissionError(
                    f"action {action_id!r} blocked by governance veto; "
                    "only a human clears a veto")
            self.audit.append(ext_id, "action.confirmed",
                              {"action": action_id,
                               "governance_notes": veto_hits})
        else:
            self.audit.append(ext_id, "action.run",
                              {"action": action_id, "kind": action["kind"]})
        try:
            result = fn(loaded.ctx, **kwargs)
        except Exception as exc:
            self.audit.append(ext_id, "action.error",
                              {"action": action_id, "error": str(exc)[:300]})
            raise
        self.audit.append(ext_id, "action.ok", {"action": action_id})
        return {"ok": True, "action": action_id, "result": result}

    # -- inventory ----------------------------------------------------------------------------
    def list_loaded(self) -> list[dict[str, Any]]:
        return [
            {"id": le.ext_id, "version": le.manifest["version"],
             "name": le.manifest["name"], "trust": le.trust,
             "capabilities": manifest_summary(le.manifest)}
            for le in self._loaded.values()
        ]
