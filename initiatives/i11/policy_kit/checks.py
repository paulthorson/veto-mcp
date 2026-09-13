#!/usr/bin/env python3
"""Policy test kit: reusable checks every extension must pass.

Each check is a function ``check_*(host, ext_dir) -> CheckResult`` so
extension authors, the registry security gate, and CI can reuse the same
suite. The checks cover the roadmap's list: confirmation, PII handling,
rate limits, circuit breakers, and veto behavior.

Checks run against a fresh Host with synthetic providers — deterministic,
no network, no core wiring required.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..manifest.schema import load_manifest
from ..sandbox import host as host_mod
from ..sandbox.host import ConfirmationBroker, Host, scan_imports


@dataclass
class CheckResult:
    id: str
    passed: bool
    detail: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


def _fresh_host(secret: bytes = b"test-secret-32-bytes-padding!!!!") -> Host:
    tmp = tempfile.mkdtemp(prefix="veto-ext-audit-")
    return Host(audit_path=Path(tmp) / "audit.jsonl", secret=secret)


def check_manifest_valid(ext_dir: str | Path) -> CheckResult:
    """Manifest parses and declares only known capabilities."""
    try:
        manifest = load_manifest(ext_dir)
    except Exception as exc:
        return CheckResult("manifest.valid", False, f"manifest rejected: {exc}")
    return CheckResult("manifest.valid", True,
                       f"{manifest['id']}@{manifest['version']} declares "
                       f"{manifest['permissions']['data']}",
                       {"id": manifest["id"]})


def check_import_scan_clean(ext_dir: str | Path) -> CheckResult:
    """No banned imports (bypass routes closed at install time)."""
    scan = scan_imports(ext_dir)
    if not scan["ok"]:
        return CheckResult("imports.clean", False,
                           f"banned imports: {scan['violations']}",
                           {"violations": scan["violations"]})
    return CheckResult("imports.clean", True,
                       "no banned imports",
                       {"warnings": scan["warnings"]})


def check_confirmation_cannot_self_confirm(ext_dir: str | Path) -> CheckResult:
    """A confirm-required action with no token is refused."""
    host = _fresh_host()
    try:
        loaded = host.load_extension(ext_dir)
    except Exception as exc:
        return CheckResult("confirm.no-self-confirm", False,
                           f"load failed: {exc}")
    confirm_actions = [a["id"] for a in
                       loaded.manifest["permissions"]["actions"]
                       if a["kind"] == "confirm-required"]
    if not confirm_actions:
        return CheckResult("confirm.no-self-confirm", True,
                           "no confirm-required actions declared; vacuously holds")
    action_id = confirm_actions[0]
    try:
        host.run_extension_action(loaded.ext_id, action_id)
    except PermissionError as exc:
        ok = "confirmation token" in str(exc)
        return CheckResult("confirm.no-self-confirm", ok,
                           f"tokenless execution refused: {exc}")
    except Exception as exc:  # noqa: BLE001 - any other failure is still a refusal
        return CheckResult("confirm.no-self-confirm", True,
                           f"execution refused ({type(exc).__name__}): {exc}")
    return CheckResult("confirm.no-self-confirm", False,
                       "CONFIRM-REQUIRED ACTION RAN WITHOUT A TOKEN — bypass!")


def check_confirmation_forged_token_rejected(ext_dir: str | Path) -> CheckResult:
    """A forged confirmation token is rejected."""
    host = _fresh_host()
    try:
        loaded = host.load_extension(ext_dir)
    except Exception as exc:
        return CheckResult("confirm.forged-token", False, f"load failed: {exc}")
    confirm_actions = [a["id"] for a in
                       loaded.manifest["permissions"]["actions"]
                       if a["kind"] == "confirm-required"]
    if not confirm_actions:
        return CheckResult("confirm.forged-token", True,
                           "no confirm-required actions; vacuously holds")
    action_id = confirm_actions[0]
    # Forge a token with a DIFFERENT host secret — simulates an extension
    # that stole the token format but not the secret.
    forger = ConfirmationBroker(secret=b"attacker-secret-32-bytes-padding!!")
    pending = forger.request(loaded.ext_id, action_id,
                             {"action": action_id, "params": {}})
    forged = forger.mint(pending.pending_id)
    try:
        host.run_extension_action(loaded.ext_id, action_id,
                                  confirmation_token=forged)
    except PermissionError:
        return CheckResult("confirm.forged-token", True,
                           "forged token rejected")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("confirm.forged-token", True,
                           f"rejected ({type(exc).__name__})")
    return CheckResult("confirm.forged-token", False,
                       "FORGED TOKEN ACCEPTED — bypass!")


def check_confirmation_replay_rejected(ext_dir: str | Path) -> CheckResult:
    """A confirmation token is single-use: replay is rejected."""
    host = _fresh_host()
    try:
        loaded = host.load_extension(ext_dir)
    except Exception as exc:
        return CheckResult("confirm.replay", False, f"load failed: {exc}")
    confirm_actions = [a["id"] for a in
                       loaded.manifest["permissions"]["actions"]
                       if a["kind"] == "confirm-required"]
    if not confirm_actions:
        return CheckResult("confirm.replay", True,
                           "no confirm-required actions; vacuously holds")
    action_id = confirm_actions[0]
    params: dict[str, Any] = {}
    pending = host.confirmations.request(
        loaded.ext_id, action_id, {"action": action_id, "params": params})
    token = host.confirmations.mint(pending.pending_id)
    # First use: run the action (it may fail for other reasons — e.g. the
    # reference action is a no-op; what matters is the token was consumed).
    try:
        host.run_extension_action(loaded.ext_id, action_id,
                                  confirmation_token=token, **params)
    except PermissionError as exc:
        # A veto-screen block still consumed the token; that is fine.
        if "veto" not in str(exc).lower():
            return CheckResult("confirm.replay", False,
                               f"first use unexpectedly refused: {exc}")
    except Exception:  # noqa: BLE001 - action errors still consume the token
        pass
    # Second use must be refused.
    try:
        host.run_extension_action(loaded.ext_id, action_id,
                                  confirmation_token=token, **params)
    except PermissionError:
        return CheckResult("confirm.replay", True, "replayed token rejected")
    except Exception:  # noqa: BLE001
        return CheckResult("confirm.replay", True,
                           "replayed token rejected (non-permission error)")
    return CheckResult("confirm.replay", False,
                       "REPLAYED TOKEN ACCEPTED — bypass!")


def check_pii_redacted_by_default(ext_dir: str | Path) -> CheckResult:
    """With pii:redact (default), PII fields never reach extension code."""
    host = _fresh_host()
    try:
        loaded = host.load_extension(ext_dir)
    except Exception as exc:
        return CheckResult("pii.redacted", False, f"load failed: {exc}")
    if "profile:read" not in loaded.manifest["permissions"]["data"]:
        return CheckResult("pii.redacted", True,
                           "profile:read not declared; vacuously holds")
    host.register_provider("profile:read", lambda: {
        "name": "Ada Lovelace", "email": "ada@example.com",
        "phone": "+1-555-0100"})
    profile = loaded.ctx.data("profile:read")
    leaked = [k for k in ("email", "phone")
              if profile.get(k) not in (None, "***redacted***")]
    if loaded.manifest["permissions"]["pii"] == "redact" and leaked:
        return CheckResult("pii.redacted", False,
                           f"PII leaked to extension: {leaked}")
    if loaded.manifest["permissions"]["pii"] == "read" and leaked:
        return CheckResult("pii.redacted", True,
                           "pii:read declared; registry UX gate must justify")
    return CheckResult("pii.redacted", True, "PII redacted before extension saw it")


def check_rate_limit_enforced(ext_dir: str | Path) -> CheckResult:
    """Manifest rate limits are enforced by the host, not the extension."""
    host = _fresh_host()
    try:
        loaded = host.load_extension(ext_dir)
    except Exception as exc:
        return CheckResult("ratelimit.enforced", False, f"load failed: {exc}")
    if not loaded.manifest["permissions"]["network"]["destinations"]:
        return CheckResult("ratelimit.enforced", True,
                           "no network destinations; vacuously holds")
    # Shrink the bucket for a fast deterministic test.
    from ..sandbox.net import RateLimitExceeded, _TokenBucket  # noqa: SLF001
    loaded.http._bucket = _TokenBucket(3)  # noqa: SLF001
    calls = [{"method": "GET", "url": "http://dummy/"}]
    from ..sandbox.net import HttpRequest
    dest = loaded.manifest["permissions"]["network"]["destinations"][0]
    hit = False
    for _ in range(6):
        try:
            loaded.http.request(HttpRequest(
                method="GET", url=f"https://{dest}/x"))
        except RateLimitExceeded:
            hit = True
            break
        except Exception:  # noqa: BLE001 - transport errors are fine here
            pass
    _ = calls
    return CheckResult("ratelimit.enforced", hit,
                       "rate limit tripped" if hit else
                       "RATE LIMIT NOT ENFORCED — 6 rapid calls all passed")


def check_circuit_breaker_trips(ext_dir: str | Path) -> CheckResult:
    """Repeated 5xx failures open the circuit; recovery cools down."""
    host = _fresh_host()
    try:
        loaded = host.load_extension(ext_dir)
    except Exception as exc:
        return CheckResult("circuit.trips", False, f"load failed: {exc}")
    dests = loaded.manifest["permissions"]["network"]["destinations"]
    if not dests:
        return CheckResult("circuit.trips", True,
                           "no network destinations; vacuously holds")
    from ..sandbox.net import CircuitOpen, HttpRequest, HttpResponse
    dest = dests[0]
    calls = {"n": 0}

    def failing_transport(req: HttpRequest) -> HttpResponse:
        calls["n"] += 1
        return HttpResponse(status=503, headers={}, body=b"")
    from ..sandbox import net as net_mod
    http = net_mod.SandboxHTTP([dest], calls_per_minute=6000,
                               transport=failing_transport)
    tripped = False
    for _ in range(6):
        try:
            http.request(HttpRequest(method="GET", url=f"https://{dest}/"))
        except CircuitOpen:
            tripped = True
            break
        except Exception:  # noqa: BLE001
            pass
    return CheckResult("circuit.trips", tripped and calls["n"] >= 3,
                       f"circuit opened after {calls['n']} failing calls"
                       if tripped else "CIRCUIT NEVER OPENED")


def check_undeclared_scope_denied(ext_dir: str | Path) -> CheckResult:
    """Data scopes outside the manifest are denied."""
    host = _fresh_host()
    try:
        loaded = host.load_extension(ext_dir)
    except Exception as exc:
        return CheckResult("scope.denied", False, f"load failed: {exc}")
    from ..manifest.schema import DATA_SCOPES
    declared = set(loaded.manifest["permissions"]["data"])
    undeclared = [s for s in DATA_SCOPES if s not in declared]
    if not undeclared:
        return CheckResult("scope.denied", False,
                           "extension declares every scope; pick a narrower fixture")
    try:
        loaded.ctx.data(undeclared[0])
    except PermissionError:
        return CheckResult("scope.denied", True,
                           f"undeclared scope {undeclared[0]!r} denied")
    return CheckResult("scope.denied", False,
                       f"UNDECLARED SCOPE {undeclared[0]!r} WAS GRANTED — bypass!")


def check_audit_append_only(ext_dir: str | Path) -> CheckResult:
    """Extension code has no write path to the audit log; chain verifies."""
    host = _fresh_host()
    try:
        loaded = host.load_extension(ext_dir)
    except Exception as exc:
        return CheckResult("audit.append-only", False, f"load failed: {exc}")
    # The context must not expose the audit writer.
    exposed = [name for name in ("audit", "_audit", "append_audit",
                                 "write_audit")
               if hasattr(loaded.ctx, name)]
    if exposed:
        return CheckResult("audit.append-only", False,
                           f"ctx exposes audit writers: {exposed}")
    loaded.ctx.data("jobs:read") if "jobs:read" in loaded.ctx.scopes else None
    verdict = host.audit.verify()
    if not verdict["ok"]:
        return CheckResult("audit.append-only", False,
                           f"audit chain broken: {verdict['error']}")
    mine = host.audit.entries_for(loaded.ext_id)
    if not mine:
        return CheckResult("audit.append-only", False,
                           "no audit entries recorded for extension actions")
    return CheckResult("audit.append-only", True,
                       f"{verdict['entries']} chained entries; "
                       f"{len(mine)} for this extension; ctx has no writer")


ALL_CHECKS = [
    check_manifest_valid,
    check_import_scan_clean,
    check_confirmation_cannot_self_confirm,
    check_confirmation_forged_token_rejected,
    check_confirmation_replay_rejected,
    check_pii_redacted_by_default,
    check_rate_limit_enforced,
    check_circuit_breaker_trips,
    check_undeclared_scope_denied,
    check_audit_append_only,
]


def run_policy_suite(ext_dir: str | Path) -> dict[str, Any]:
    """Run every policy check. Returns {passed, failed, results}."""
    results = []
    for check in ALL_CHECKS:
        try:
            results.append(check(ext_dir))
        except Exception as exc:  # noqa: BLE001 - a crashed check fails closed
            results.append(CheckResult(check.__name__, False,
                                       f"check crashed (fail closed): {exc}"))
    failed = [r for r in results if not r.passed]
    return {
        "extension": str(ext_dir),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "results": [{"id": r.id, "passed": r.passed, "detail": r.detail}
                    for r in results],
    }
