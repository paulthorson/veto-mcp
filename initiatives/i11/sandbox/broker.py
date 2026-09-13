#!/usr/bin/env python3
"""Capability broker: the ONLY host surface extension code can reach.

Security design note — read before modifying:

This module is deliberately small and its module globals contain NOTHING
dangerous: no host secret, no ``Host`` class, no confirmation broker, no
mint. Extension code receives an ``ExtensionContext`` whose methods are
defined HERE, so ``ctx.<method>.__globals__`` exposes only this module's
safe namespace.

The broker reaches the real ``Host`` through a per-load random token
looked up in a module-private registry. The token alone is useless: it is
an unguessable string, and the registry is reachable only through Python
introspection (dunders) — never through plain attribute access. There is
no ``ctx._host`` and no ``broker._host``; ``ctx._broker._host`` does not
exist either.

What this closes (all verified by tests + adversarial suite):
- self-minting confirmations via any plain-attribute path,
- scope escalation / kind downgrade (the manifest is deep-frozen by the
  host; enforcement reads the frozen manifest, never ctx state).

Disclosed residual (see initiatives/i11/README.md): in-process Python
introspection (``__globals__`` / ``__class__`` / ``__closure__`` chains,
``__import__`` tricks) can still reach host internals for a deliberately
adversarial author with source access. That path is controlled by the
registry's human security review (the code is read before publish),
signed packages, and the append-only audit log — and by the roadmap
hardening step of out-of-process execution.
"""

from __future__ import annotations

import secrets
from typing import Any

# token -> Host. Populated at load, removed at unload. The values are
# deliberately typed as Any: importing Host here would create a cycle and
# would also put the Host class in this module's (extension-visible)
# __globals__.
_BROKER_HOSTS: dict[str, Any] = {}


def issue_broker_token(host: Any) -> str:
    """Register a host for one loaded extension; returns its token."""
    token = "bk_" + secrets.token_hex(16)
    _BROKER_HOSTS[token] = host
    return token


def revoke_broker_token(token: str) -> None:
    _BROKER_HOSTS.pop(token, None)


class Broker:
    """Extension-reachable operations, dispatched by token.

    Only the eight brokered operations exist here. There is deliberately
    no reference to the Host object, the confirmation broker, the audit
    writer, or any secret — not as attributes, not as defaults, not as
    closures over them (the host is reached through the token registry).
    """

    def __init__(self, token: str, ext_id: str) -> None:
        self._token = token
        self._ext_id = ext_id

    # -- the complete extension-visible operation set ----------------------
    # Each method resolves the host through the token registry inline.
    # No method returns the Host object, and no attribute holds it:
    # ``broker._host`` does not exist, so there is no plain-attribute
    # path from extension code to the confirmation broker, audit
    # writer, or host secret.
    def data_for(self, scope: str) -> Any:
        host = _BROKER_HOSTS.get(self._token)
        if host is None:
            raise RuntimeError("extension host is no longer available")
        return host._data_for(self._ext_id, scope)

    def fs_for(self) -> Any:
        host = _BROKER_HOSTS.get(self._token)
        if host is None:
            raise RuntimeError("extension host is no longer available")
        return host._fs_for(self._ext_id)

    def http_for(self) -> Any:
        host = _BROKER_HOSTS.get(self._token)
        if host is None:
            raise RuntimeError("extension host is no longer available")
        return host._http_for(self._ext_id)

    def draft_artifact(self, name: str, content: str) -> str:
        host = _BROKER_HOSTS.get(self._token)
        if host is None:
            raise RuntimeError("extension host is no longer available")
        return host._draft_artifact(self._ext_id, name, content)

    def queue_notification(self, title: str, body: str) -> str:
        host = _BROKER_HOSTS.get(self._token)
        if host is None:
            raise RuntimeError("extension host is no longer available")
        return host._queue_notification(self._ext_id, title, body)

    def request_confirmation(self, action_id: str,
                             payload: dict[str, Any]) -> str:
        host = _BROKER_HOSTS.get(self._token)
        if host is None:
            raise RuntimeError("extension host is no longer available")
        return host._request_confirmation(
            self._ext_id, action_id, payload).pending_id

    def run_action(self, action_id: str,
                   confirmation_token: str | None,
                   params: dict[str, Any]) -> dict[str, Any]:
        host = _BROKER_HOSTS.get(self._token)
        if host is None:
            raise RuntimeError("extension host is no longer available")
        return host.run_extension_action(
            self._ext_id, action_id,
            confirmation_token=confirmation_token, **params)

    def audit_view_for(self, limit: int) -> list[dict[str, Any]]:
        host = _BROKER_HOSTS.get(self._token)
        if host is None:
            raise RuntimeError("extension host is no longer available")
        return host.audit.entries_for(self._ext_id, limit=limit)


# ---------------------------------------------------------------------------
# Extension context (the ONLY thing extension code receives)
# ---------------------------------------------------------------------------

class ExtensionContext:
    """Capability-scoped API surface handed to extension code.

    Defined in this safe-globals module so ``ctx.<method>.__globals__``
    exposes nothing dangerous. Deliberately narrow: data(), fs, http,
    draft_artifact(), queue_notification(), request_confirmation(),
    run_action(), audit_view(). No reference to the Host (no ``_host``
    attribute — the context holds a token broker only), no
    mint_confirmation, no audit writes, no secret access. Capability data
    exposed here is derived from the deep-frozen manifest and cannot be
    mutated.
    """

    def __init__(self, broker: Broker, ext_id: str,
                 manifest: Any) -> None:
        self._broker = broker
        self._ext_id = ext_id
        self._manifest = manifest  # deep-frozen; mutation raises TypeError

    @property
    def scopes(self) -> frozenset:
        """Declared data scopes (immutable view)."""
        return frozenset(self._manifest["permissions"]["data"])

    @property
    def action_kinds(self) -> dict[str, str]:
        """Declared action id -> kind (immutable snapshot)."""
        return {a["id"]: a["kind"]
                for a in self._manifest["permissions"]["actions"]}

    # -- data ---------------------------------------------------------------
    def data(self, scope: str) -> Any:
        return self._broker.data_for(scope)

    # -- sandboxed fs / net ---------------------------------------------------
    @property
    def fs(self) -> Any:
        return self._broker.fs_for()

    @property
    def http(self) -> Any:
        return self._broker.http_for()

    # -- drafts (local artifacts only, never sent) ------------------------------
    def draft_artifact(self, name: str, content: str) -> str:
        return self._broker.draft_artifact(name, content)

    # -- notifications: queued as proposals, never sent -------------------------
    def queue_notification(self, title: str, body: str) -> str:
        return self._broker.queue_notification(title, body)

    # -- confirmation: request only; minting is host-only ------------------------
    def request_confirmation(self, action_id: str,
                             **params: Any) -> str:
        """Request human confirmation for a confirm-required action.

        Returns a pending id. The host UI shows the pending request; after
        the human approves, the host mints a single-use token bound to the
        exact params. Call run_action with the same params + token.
        """
        return self._broker.request_confirmation(
            action_id, {"action": action_id, "params": params})

    def run_action(self, action_id: str, confirmation_token: str | None = None,
                   **params: Any) -> dict[str, Any]:
        return self._broker.run_action(action_id, confirmation_token, params)

    def audit_view(self, limit: int = 50) -> list[dict[str, Any]]:
        """Read-only view of this extension's own audit entries."""
        return self._broker.audit_view_for(limit)
