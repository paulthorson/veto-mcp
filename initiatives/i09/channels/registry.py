"""Epic 3 — explicit opt-in communication channels.

Gmail plus user-selected WhatsApp, Discord, Messenger, or another approved
channel through explicit skills. User-selected and explicit ONLY:

* No channel is ever enabled by default, by upgrade, or by implication.
* ``enable_channel`` requires an explicit ``confirm=True`` from the user
  (the CLI wizard / web UI passes the user's own confirmation through).
* Every enable/disable is appended to a local-first audit log (JSONL),
  written 0o600 with fsync, HMAC-signed with a machine-local key, and read
  back with integrity verification. Tampered or malformed entries are
  loudly logged and never trusted (fail closed).
* Every channel carries a full ConnectorManifest: what it can do, why it
  may be blocked, what data it sends, which actions require confirmation.
* WhatsApp / Discord / Messenger are declared as explicit-skill channels:
  they do nothing until the user both selects the channel AND connects the
  corresponding skill. Veto stores no credentials for them.

The Gmail adapter delegates to the existing ``email_sync`` module; this
registry adds the consent layer and the interactive send-approval boundary
around it.

Interactive send approval (the send boundary)
---------------------------------------------
A caller-asserted boolean can never authorize a send. Every send — through
``GmailChannel.send_followup`` OR through ``email_sync.send_followup``
directly — must pass ``authorize_send`` here first:

1. APPROVE (interactive): ``request_send_approval(draft)`` presents the
   ACTUAL recipient, subject, and body to the user on the terminal and
   requires them to type ``send``. Only a genuine interactive approval
   writes an approval record to the HMAC-signed consent log. The record
   binds ``nonce + content_hash(to/subject/body) + timestamp`` — approval
   evidence is bound to a human approval EVENT, not to content alone.
2. SEND: ``authorize_send`` accepts ONLY (a) an ``approval_id`` naming a
   valid, fresh, unconsumed approval record for the EXACT draft being sent,
   or (b) a fresh unconsumed approval record already on file for that exact
   content. Otherwise — including when the caller passes ``confirm=True``
   or a self-minted token — it falls back to the interactive prompt when a
   TTY is present, and REFUSES when there is none (agents, scripts, MCP
   servers: fail closed, no user to ask).
3. CONSUME: ``consume_approval`` marks the record single-use (in-process
   set plus an ``approval_consumed`` log entry) immediately before the
   transport is attempted. Replays, content-substituted drafts, and expired
   approvals (TTL 15 minutes) are refused.

``draft_approval_token`` remains as a pure CONTENT DIGEST (deterministic
SHA-256 of the canonicalized draft) for display and reconciliation. It is
NOT proof of approval and the send path never accepts it as such — anyone
can compute it, which is exactly why it authorizes nothing.

``confirm=True`` (registry and ``email_sync``) is DEPRECATED as an
authorization signal: it is now a no-op that still routes through the
interactive approval above. It is kept in signatures only so existing
callers fail closed with instructions instead of a TypeError.

Recovery: if the machine-local integrity key is lost, every stored
consent/approval entry becomes unverifiable and the registry fails closed
(channels read as disabled, sends refused). The re-keying procedure is
documented in ``RECOVERY.md`` next to this module; the key-loss ERROR log
points at it.

VETO STATUS: this module was reworked under Rule 1 review case
``init-09-comms-rereview`` (KICK_BACK re-raised: self-mintable token +
caller-asserted confirm + direct-call bypass). The rework implements the
interactive send boundary described above. The veto still needs Paul's
explicit clearance after re-review — disclosure does not clear it.
See ``DECISIONS.md`` for the mechanism choice record.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from providers._contract import ConnectorManifest

log = logging.getLogger("job-apply-mcp.i09.channels")


def _resolve_base_dir() -> Path:
    """Repo root for this registry — fails loudly on an unexpected layout.

    The consent store must never be silently written "somewhere else" if
    this module is relocated; if the on-disk layout does not match the
    expected ``<root>/initiatives/i09/channels/registry.py`` shape, raise
    at import time rather than guessing.
    """
    here = Path(__file__).resolve()
    base = here.parent.parent.parent.parent  # channels/i09/initiatives/<root>
    expected = (base / "initiatives" / "i09" / "channels" / "registry.py").resolve()
    if expected != here:
        raise RuntimeError(
            "channels.registry: unexpected module layout — expected "
            f"{expected}, this file is {here}. Refusing to resolve the "
            "consent-store location rather than writing it elsewhere."
        )
    return base


BASE_DIR = _resolve_base_dir()
CONSENT_LOG = BASE_DIR / "channel_consent.jsonl"

# The opt-in source must be enumerable so the audit log distinguishes a
# genuine wizard/UI opt-in from a hardcoded string.
VALID_VIA_SOURCES = frozenset({"cli-wizard", "web-ui", "api"})

# Interactive send approvals expire this long after the user typed "send".
# Short enough that a stale approval cannot be weaponized later; long
# enough for a wizard preview → approve → send round-trip.
APPROVAL_TTL_SECONDS = 15 * 60

RECOVERY_DOC = "initiatives/i09/channels/RECOVERY.md"


def _consent_log() -> Path:
    return CONSENT_LOG


def _consent_key_path() -> Path:
    # Sibling of the consent log so tests that redirect CONSENT_LOG into a
    # temp dir get an isolated key automatically.
    return _consent_log().with_name("channel_consent.key")


def _canonical_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")


# ---------------------------------------------------------------------------
# Machine-local integrity key (generated once, 0o600, never hardcoded)
# ---------------------------------------------------------------------------


def _load_or_create_key() -> bytes:
    """Return the machine-local HMAC key, generating it once if needed.

    The key is random per machine, stored 0o600 next to the consent log,
    and never appears in code. Losing the key invalidates old entries on
    read (fail closed), which is the safe direction — see RECOVERY.md for
    the re-keying procedure.
    """
    key_path = _consent_key_path()
    try:
        raw = key_path.read_bytes()
        if len(raw) >= 32:
            return raw
        raise ValueError(f"consent key too short ({len(raw)} bytes)")
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as exc:
        log.error("Consent key unreadable (%s); refusing to write.", exc)
        raise OSError(f"consent key unreadable: {exc}") from exc

    key = secrets.token_bytes(32)
    try:
        key_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OSError(f"cannot create consent dir: {exc}") from exc
    try:
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        # Lost the race with another process; read the winner's key.
        return _load_or_create_key()
    except OSError as exc:
        raise OSError(f"cannot create consent key: {exc}") from exc
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, key)
        os.fsync(fd)
    finally:
        os.close(fd)
    return key


def rotate_consent_key() -> dict[str, Any]:
    """Rotate the machine-local integrity key (recovery operation).

    Archives the current key next to the consent log and forces a fresh
    key to be generated on next use. THIS INVALIDATES EVERYTHING SIGNED
    WITH THE OLD KEY: all channel consents read as disabled and all
    pending send approvals are void until the user re-enables channels
    and re-approves sends. That is the documented, fail-closed recovery
    path — see RECOVERY.md.
    """
    key_path = _consent_key_path()
    backup: str | None = None
    try:
        if key_path.exists():
            backup = str(
                key_path.with_name(
                    f"channel_consent.key.{int(time.time())}.bak"
                )
            )
            os.rename(key_path, backup)
            os.chmod(backup, 0o600)
    except OSError as exc:
        log.error("Key rotation failed: %s", exc)
        return {"ok": False, "error": f"key_rotation_failed: {exc}"}
    log.warning(
        "Consent integrity key rotated (backup: %s). All prior consent and "
        "approval entries are now unverifiable by design; channels must be "
        "re-enabled by the user. See %s.",
        backup, RECOVERY_DOC,
    )
    return {
        "ok": True,
        "backup": backup,
        "warning": (
            "All existing consent and send-approval entries are now "
            "unverifiable and treated as absent (fail closed). Re-enable "
            f"channels explicitly. Full procedure: {RECOVERY_DOC}."
        ),
    }


# ---------------------------------------------------------------------------
# Channel declarations
# ---------------------------------------------------------------------------


@dataclass
class ChannelSpec:
    """Static declaration for one channel."""

    name: str
    skill: str  # connected skill that powers it, "" if built-in
    manifest: ConnectorManifest
    enabled_by_default: bool = False  # invariant: always False


def _gmail_manifest() -> ConnectorManifest:
    return ConnectorManifest(
        name="gmail",
        connector_type="channel",
        what_it_can_do=[
            "Scan the connected Gmail account for recruiter replies and "
            "classify them (delegates to email_sync).",
            "Draft follow-up emails from application records (draft only).",
            "Send a reviewed follow-up draft — only after a genuine "
            "interactive user approval bound to the exact draft content "
            "(see request_send_approval).",
        ],
        why_it_may_be_blocked=[
            "Gmail is not connected (no OAuth grant / CLI auth).",
            "Read-only triage needs the gmail skill's search scope; sending "
            "needs its send scope.",
            "No interactive user approval for this exact draft (refused "
            "without a TTY to ask on).",
            "The approval record is missing, expired, already used, or bound "
            "to different content.",
        ],
        what_data_it_sends=[
            "Gmail search queries (recruiter-reply triage) to Google.",
            "Message IDs of opened messages to fetch their bodies.",
            "On interactively-approved send only: the approved draft's "
            "to/subject/body to Gmail's send endpoint.",
        ],
        what_requires_confirmation=[
            "Enabling the channel at all (explicit user opt-in).",
            "Every send: an interactive user approval (typed at the "
            "terminal) bound to the exact draft content. Caller-asserted "
            "confirm flags and self-computed tokens are NOT sufficient.",
            "Stage updates proposed from classified replies are "
            "proposal-only until the user confirms.",
        ],
        official_interface="Gmail API via the connected gmail skill",
        interface_basis="User's own OAuth grant; Veto stores no password.",
    )


def _skill_channel_manifest(
    name: str, skill: str, description: str
) -> ConnectorManifest:
    return ConnectorManifest(
        name=name,
        connector_type="channel",
        what_it_can_do=[
            f"{description} — once the user selects this channel AND "
            f"connects the '{skill}' skill.",
            "Today: declaration only. No messages are read or sent until "
            "the skill is connected and the channel is explicitly enabled.",
        ],
        why_it_may_be_blocked=[
            f"The '{skill}' skill is not connected.",
            "The channel was never explicitly enabled (it never auto-"
            "enables).",
            "No approved message template exists for job-search outreach "
            "on this channel yet.",
        ],
        what_data_it_sends=[
            "Nothing today: without a connected skill and explicit "
            "enablement, this channel performs no network calls.",
        ],
        what_requires_confirmation=[
            f"Connecting the '{skill}' skill.",
            "Enabling the channel (explicit opt-in).",
            "Every outbound message, individually, at send time — via an "
            "interactive user approval.",
        ],
        official_interface=f"{skill} skill (explicit)",
        interface_basis="Explicit user selection + explicit skill only.",
    )


CHANNELS: dict[str, ChannelSpec] = {}


def _register(spec: ChannelSpec) -> None:
    # Explicit raise (not assert): asserts vanish under `python -O`, and
    # this invariant is load-bearing.
    if spec.enabled_by_default is not False:
        raise ValueError(
            f"channel {spec.name!r} must never be enabled by default"
        )
    CHANNELS[spec.name] = spec


_register(ChannelSpec(name="gmail", skill="gmail", manifest=_gmail_manifest()))
_register(
    ChannelSpec(
        name="whatsapp",
        skill="whatsapp",
        manifest=_skill_channel_manifest(
            "whatsapp", "whatsapp", "WhatsApp messaging"
        ),
    )
)
_register(
    ChannelSpec(
        name="discord",
        skill="discord",
        manifest=_skill_channel_manifest("discord", "discord", "Discord messaging"),
    )
)
_register(
    ChannelSpec(
        name="messenger",
        skill="messenger",
        manifest=_skill_channel_manifest(
            "messenger", "messenger", "Messenger messaging"
        ),
    )
)


# ---------------------------------------------------------------------------
# Consent store (append-only, local-first, integrity-protected)
# ---------------------------------------------------------------------------


def _append_consent(entry: dict[str, Any]) -> None:
    """Append one consent entry. Raises OSError on ANY write failure.

    Entries are HMAC-signed with the machine-local key, written 0o600,
    fsync'd before close. Callers translate failures into failed
    operations — a consent write that did not land must never be reported
    as success.
    """
    body = {"ts": time.time(), **entry}
    key = _load_or_create_key()
    body["mac"] = hmac.new(
        key, _canonical_bytes(body), hashlib.sha256
    ).hexdigest()
    line = (json.dumps(body, sort_keys=True) + "\n").encode("utf-8")

    path = _consent_log()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OSError(f"cannot create consent dir: {exc}") from exc
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    except OSError as exc:
        raise OSError(f"cannot open consent log: {exc}") from exc
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, line)
        os.fsync(fd)
    except OSError as exc:
        raise OSError(f"cannot write consent log: {exc}") from exc
    finally:
        os.close(fd)


def _verify_entry(raw: Any, key: bytes | None) -> tuple[dict[str, Any] | None, str]:
    """Return (entry, problem). problem == "" means verified OK."""
    if not isinstance(raw, dict):
        return None, "not an object"
    mac = raw.get("mac")
    if not isinstance(mac, str):
        return None, "missing signature"
    if key is None:
        return None, "no key available to verify signature"
    body = {k: v for k, v in raw.items() if k != "mac"}
    expected = hmac.new(key, _canonical_bytes(body), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, mac):
        return None, "signature mismatch (tampered or foreign key)"
    return raw, ""


def _read_consent() -> tuple[list[dict[str, Any]], bool]:
    """Read and verify the consent log.

    Returns (verified_entries, integrity_ok). Malformed lines and
    tampered entries are LOUDLY logged (ERROR) and never trusted;
    integrity_ok is False when anything at all failed verification, which
    callers treat as fail-closed.
    """
    path = _consent_log()
    if not path.exists():
        return [], True
    entries: list[dict[str, Any]] = []
    integrity_ok = True
    try:
        key: bytes | None = _load_or_create_key()
    except OSError as exc:
        log.error(
            "CONSENT INTEGRITY: cannot load machine key (%s); "
            "treating existing consent data as unverifiable — all channels "
            "read as disabled and pending send approvals are void. "
            "Recovery procedure: %s.",
            exc, RECOVERY_DOC,
        )
        return [], False
    try:
        with path.open(encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    integrity_ok = False
                    log.error(
                        "CONSENT INTEGRITY: malformed JSON on line %d of %s; "
                        "line ignored, store treated as untrusted.",
                        lineno, path,
                    )
                    continue
                entry, problem = _verify_entry(raw, key)
                if entry is None:
                    integrity_ok = False
                    log.error(
                        "CONSENT INTEGRITY: line %d of %s rejected (%s); "
                        "entry ignored, store treated as untrusted.",
                        lineno, path, problem,
                    )
                    continue
                entries.append(entry)
    except OSError as exc:
        log.error("CONSENT INTEGRITY: cannot read consent log: %s", exc)
        return [], False
    return entries, integrity_ok


def consent_history(
    channel: str | None = None, *, with_integrity: bool = False
) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], bool]:
    """Read the consent audit log (newest last).

    Only integrity-verified entries are returned. Verification failures
    are logged loudly at ERROR by the reader.

    With ``with_integrity=True`` returns ``(entries, integrity_ok)`` so
    callers can distinguish "no consents on file" from "the store failed
    verification" — the plain list form cannot tell those apart.
    """
    entries, integrity_ok = _read_consent()
    if channel is not None:
        entries = [e for e in entries if e.get("channel") == channel]
    if with_integrity:
        return entries, integrity_ok
    return entries


def is_enabled(channel: str) -> bool:
    """True only if the verified latest consent entry is an enable.

    Fail closed: if the consent store cannot be integrity-verified, the
    channel is treated as NOT enabled regardless of what the log claims.
    """
    entries, integrity_ok = _read_consent()
    if not integrity_ok:
        log.error(
            "CONSENT INTEGRITY: store failed verification; treating "
            "channel %r as disabled (fail closed). Recovery: %s.",
            channel, RECOVERY_DOC,
        )
        return False
    history = [
        e
        for e in entries
        if e.get("channel") == channel
        and e.get("action") in ("enable", "disable")
    ]
    if not history:
        return False
    return history[-1].get("action") == "enable"


def enabled_channels() -> list[str]:
    """Channels the user has explicitly enabled and not since disabled."""
    return [name for name in CHANNELS if is_enabled(name)]


# ---------------------------------------------------------------------------
# Explicit opt-in / opt-out
# ---------------------------------------------------------------------------


def _validate_via(via: str) -> str | None:
    """Return an error message when ``via`` is not an enumerated source."""
    if via not in VALID_VIA_SOURCES:
        return (
            f"invalid_via: {via!r} is not a recognized opt-in source; "
            f"expected one of {sorted(VALID_VIA_SOURCES)}"
        )
    return None


def enable_channel(
    channel: str, *, confirm: bool = False, via: str = ""
) -> dict[str, Any]:
    """Enable a channel — ONLY with the user's explicit confirmation.

    ``confirm=True`` must carry the user's own opt-in (the wizard / UI
    passes it through; it is never defaulted). Without it, nothing changes
    and the caller gets instructions.

    A consent write that does not land is an enable FAILURE: the result
    reports ok False and the channel is not enabled.

    NOTE (residual product question, for Paul): channel *enablement* is
    still a caller-asserted boolean + enumerated ``via`` source. The
    interactive send boundary below means a rogue enable alone can never
    cause a send, but whether enablement itself should be interactive is
    undecided — see DECISIONS.md.
    """
    name = (channel or "").strip().lower()
    spec = CHANNELS.get(name)
    if spec is None:
        return {
            "ok": False,
            "error": f"unknown_channel: {channel!r}",
            "known_channels": sorted(CHANNELS),
        }
    via_error = _validate_via(via)
    if via_error:
        return {"ok": False, "enabled": False, "channel": name, "error": via_error}
    if not confirm:
        return {
            "ok": False,
            "enabled": False,
            "channel": name,
            "instructions": (
                f"Enabling {name!r} is an explicit opt-in. Review its "
                "declaration (manifest) first, then call enable_channel "
                "with confirm=True — or use the guided wizard, which asks "
                "you directly. Nothing was enabled."
            ),
            "manifest": spec.manifest.to_dict(),
        }
    try:
        _append_consent({"action": "enable", "channel": name, "via": via})
    except OSError as exc:
        log.error("Channel %r NOT enabled: consent write failed: %s", name, exc)
        return {
            "ok": False,
            "enabled": False,
            "channel": name,
            "error": f"consent_write_failed: {exc}",
        }
    log.info("Channel %r enabled via %r", name, via)
    return {"ok": True, "enabled": True, "channel": name}


def disable_channel(channel: str, *, via: str = "") -> dict[str, Any]:
    """Disable a channel immediately; appended to the audit log.

    A consent write that does not land is reported as a FAILURE — the
    caller must not believe the disable was recorded when it was not.
    """
    name = (channel or "").strip().lower()
    if name not in CHANNELS:
        return {"ok": False, "error": f"unknown_channel: {channel!r}"}
    via_error = _validate_via(via)
    if via_error:
        return {"ok": False, "enabled": True, "channel": name, "error": via_error}
    try:
        _append_consent({"action": "disable", "channel": name, "via": via})
    except OSError as exc:
        log.error("Channel %r disable NOT recorded: %s", name, exc)
        return {
            "ok": False,
            "enabled": True,
            "channel": name,
            "error": f"consent_write_failed: {exc}",
        }
    log.info("Channel %r disabled via %r", name, via)
    return {"ok": True, "enabled": False, "channel": name}


def channel_manifest(channel: str) -> ConnectorManifest | None:
    """The proof-of-value declaration for a channel."""
    spec = CHANNELS.get((channel or "").strip().lower())
    return spec.manifest if spec else None


# ---------------------------------------------------------------------------
# Interactive send approval (the send boundary)
# ---------------------------------------------------------------------------


def _canonical_draft(draft: dict[str, Any]) -> bytes:
    """Canonical bytes of the (to, subject, body) triple being approved."""
    return _canonical_bytes(
        {
            "to": str(draft.get("to") or "").strip(),
            "subject": str(draft.get("subject") or "").strip(),
            "body": str(draft.get("body") or "").strip(),
        }
    )


def _content_hash(draft: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_draft(draft)).hexdigest()


def draft_approval_token(draft: dict[str, Any]) -> str:
    """Content digest of a draft: SHA-256 of the canonicalized payload.

    This is a DISPLAY / reconciliation helper only — it is deterministic
    and computable by anyone, so it is NOT proof of approval and the send
    path NEVER accepts it as authorization. Genuine approval evidence is
    the ``send_approval`` record written by ``request_send_approval``
    (nonce + content hash + timestamp, HMAC-signed into the consent log).
    """
    return _content_hash(draft)


def _stdin_is_tty() -> bool:
    """True when a human is plausibly at the terminal.

    Split out (not inlined) so tests can simulate both sides of the
    interactive boundary deterministically.
    """
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


def _approval_input(prompt: str) -> str:
    """Read one line for the approval prompt. Split out for tests."""
    return input(prompt)


def _present_draft(draft: dict[str, Any], channel: str) -> None:
    """Show the exact payload awaiting approval on the terminal."""
    to = str(draft.get("to") or "").strip()
    subject = str(draft.get("subject") or "").strip()
    body = str(draft.get("body") or "").strip()
    shown_body = body if len(body) <= 4000 else body[:4000] + "\n[…body truncated…]"
    print(f"\n=== Veto send approval ({channel}) ===")
    print(f"To:      {to or '(no recipient)'}")
    print(f"Subject: {subject or '(no subject)'}")
    print("--- body ---")
    print(shown_body)
    print("--- end body ---")


def request_send_approval(
    draft: dict[str, Any], *, channel: str = "gmail"
) -> dict[str, Any]:
    """Interactively ask the user to approve sending ``draft``.

    Presents the actual recipient/subject/body on the terminal and requires
    the user to type ``send``. On a genuine approval, writes a
    ``send_approval`` record (nonce + content hash + timestamp, HMAC-signed
    into the consent log) and returns ``{"ok": True, "approval_id": nonce}``.

    Fails closed: no TTY (agents, scripts, MCP servers), EOF, a declined
    answer, or an approval-write failure all return ``ok False`` and write
    no approval record. Nothing about this function's return value can be
    forged by a caller — only the interactive prompt itself mints records.
    """
    content_hash = _content_hash(draft)
    if not _stdin_is_tty():
        return {
            "ok": False,
            "approved": False,
            "error": "not_interactive",
            "instructions": (
                "Not sent. Sending requires a genuine interactive user "
                "approval, but there is no terminal to ask on (non-TTY "
                "stdin). Run from an interactive terminal, or obtain an "
                "approval_id via request_send_approval on a terminal first."
            ),
        }
    _present_draft(draft, channel)
    try:
        answer = _approval_input(
            'Type "send" to approve sending this exact message, '
            "anything else to abort: "
        )
    except (EOFError, KeyboardInterrupt):
        log.info("Send approval aborted (no input).")
        return {
            "ok": False,
            "approved": False,
            "error": "approval_aborted",
            "instructions": "Not sent. No approval was given.",
        }
    if answer.strip().lower() != "send":
        log.info("Send approval declined by user.")
        return {
            "ok": False,
            "approved": False,
            "error": "approval_declined",
            "instructions": "Not sent. The user did not approve this send.",
        }
    nonce = secrets.token_hex(16)
    try:
        _append_consent(
            {
                "action": "send_approval",
                "channel": channel,
                "nonce": nonce,
                "content_hash": content_hash,
            }
        )
    except OSError as exc:
        log.error("Send approval NOT recorded: %s", exc)
        return {
            "ok": False,
            "approved": False,
            "error": f"approval_write_failed: {exc}",
        }
    log.info("Send approval recorded (nonce %s…, channel %s).", nonce[:8], channel)
    return {
        "ok": True,
        "approved": True,
        "approval_id": nonce,
        "content_hash": content_hash,
        "channel": channel,
    }


# In-process single-use enforcement: an approval_id consumed here cannot be
# reused even if its ``approval_consumed`` log entry failed to persist.
_CONSUMED_APPROVALS: set[str] = set()


def _validate_approval(approval_id: str, content_hash: str) -> str | None:
    """None when the approval record authorizes this exact content.

    Returns an error code otherwise: the record must exist, be bound to
    ``content_hash``, be fresher than APPROVAL_TTL_SECONDS, and be unused.
    Any consent-store integrity failure fails closed.
    """
    entries, integrity_ok = _read_consent()
    if not integrity_ok:
        return "consent_store_unverifiable"
    match: dict[str, Any] | None = None
    for entry in entries:
        if entry.get("action") == "send_approval" and entry.get("nonce") == approval_id:
            match = entry  # newest wins; log is oldest-first
    if match is None:
        return "no_such_approval"
    if match.get("content_hash") != content_hash:
        return "approval_content_mismatch"
    try:
        age = time.time() - float(match.get("ts", 0))
    except (TypeError, ValueError):
        return "approval_malformed"
    if age < 0 or age > APPROVAL_TTL_SECONDS:
        return "approval_expired"
    for entry in entries:
        if (
            entry.get("action") == "approval_consumed"
            and entry.get("nonce") == approval_id
        ):
            return "approval_already_used"
    if approval_id in _CONSUMED_APPROVALS:
        return "approval_already_used"
    return None


def _find_unconsumed_approval(content_hash: str) -> str | None:
    """Newest fresh, unconsumed approval_id for this exact content, if any.

    Lets a caller that obtained an interactive approval (e.g. the wizard's
    preview → approve step) send without threading the approval_id through
    every layer. Safe: such a record can only exist if the user genuinely
    approved this exact content within the TTL, and it is still single-use.
    """
    entries, integrity_ok = _read_consent()
    if not integrity_ok:
        return None
    now = time.time()
    consumed = {
        e.get("nonce")
        for e in entries
        if e.get("action") == "approval_consumed"
    }
    best: str | None = None
    for entry in entries:  # oldest-first; keep newest match
        if entry.get("action") != "send_approval":
            continue
        if entry.get("content_hash") != content_hash:
            continue
        nonce = entry.get("nonce")
        if not nonce or nonce in consumed or nonce in _CONSUMED_APPROVALS:
            continue
        try:
            age = now - float(entry.get("ts", 0))
        except (TypeError, ValueError):
            continue
        if 0 <= age <= APPROVAL_TTL_SECONDS:
            best = nonce
    return best


_APPROVAL_REFUSALS = {
    "consent_store_unverifiable": (
        "Not sent. The consent store failed integrity verification, so no "
        f"approval can be trusted. Recovery procedure: {RECOVERY_DOC}."
    ),
    "no_such_approval": (
        "Not sent. No user approval record exists for this send. "
        "Approvals are created only by an interactive user approval — "
        "self-computed tokens and caller-asserted flags are not accepted."
    ),
    "approval_content_mismatch": (
        "Not sent. The approval record is bound to different content — the "
        "draft changed after the user approved it (or was never approved). "
        "Re-present the draft and obtain a fresh approval."
    ),
    "approval_expired": (
        "Not sent. The user approval expired "
        f"({APPROVAL_TTL_SECONDS // 60}-minute TTL). Re-present the draft "
        "and obtain a fresh approval."
    ),
    "approval_already_used": (
        "Not sent. This approval was already used — approvals are "
        "single-use. Obtain a fresh approval for another send."
    ),
    "approval_malformed": (
        "Not sent. The approval record is malformed and cannot be trusted."
    ),
}


def authorize_send(
    draft: dict[str, Any],
    *,
    channel: str = "gmail",
    approval_id: str | None = None,
) -> tuple[str | None, dict[str, Any] | None]:
    """The send boundary. Returns ``(approval_id, None)`` or
    ``(None, refusal_dict)``.

    ``approval_id`` names a ``send_approval`` record minted by
    ``request_send_approval``. Without one, a fresh unconsumed record for
    this exact content is accepted; otherwise the interactive prompt runs
    (TTY only) and a non-interactive caller is refused. There is no
    parameter combination by which a caller can authorize its own send.
    """
    content_hash = _content_hash(draft)
    if approval_id is not None:
        problem = _validate_approval(approval_id, content_hash)
        if problem is None:
            return approval_id, None
        return None, {
            "sent": False,
            "channel": channel,
            "error": problem,
            "instructions": _APPROVAL_REFUSALS[problem],
        }
    found = _find_unconsumed_approval(content_hash)
    if found is not None:
        return found, None
    res = request_send_approval(draft, channel=channel)
    if res.get("ok"):
        return res["approval_id"], None
    return None, {
        "sent": False,
        "channel": channel,
        "error": res.get("error", "approval_required"),
        "instructions": res.get("instructions", "Not sent: no user approval."),
    }


def consume_approval(approval_id: str, *, channel: str = "gmail") -> None:
    """Mark an approval single-use, immediately before the send attempt.

    The in-process mark is applied first (always effective); the
    ``approval_consumed`` log entry is best-effort and LOUD on failure.
    Callers consume BEFORE attempting the transport: a failed send does
    not refund the approval (fail closed — the attempt may have gone out).
    """
    _CONSUMED_APPROVALS.add(approval_id)
    try:
        _append_consent(
            {"action": "approval_consumed", "channel": channel, "nonce": approval_id}
        )
    except OSError as exc:
        log.error(
            "APPROVAL: approval %r marked consumed in-process, but the "
            "consumed marker failed to persist (%s). In-process reuse is "
            "still blocked; a restarted process could theoretically see the "
            "unconsumed record within its TTL — treat sends after log "
            "failures as suspect.",
            approval_id, exc,
        )


# ---------------------------------------------------------------------------
# Gmail adapter (delegates to email_sync; consent-gated here)
# ---------------------------------------------------------------------------


class GmailChannel:
    """Consent-gated adapter over the existing email_sync module."""

    name = "gmail"

    def _require_enabled(self) -> dict[str, Any] | None:
        if not is_enabled(self.name):
            return {
                "ok": False,
                "error": "channel_not_enabled",
                "instructions": (
                    "The gmail channel is not enabled. Enable it explicitly "
                    "first (enable_channel('gmail', confirm=True, "
                    "via='cli-wizard')); it never auto-enables."
                ),
            }
        return None

    def scan_recruiter_emails(
        self, query: str = "", max_n: int = 50
    ) -> dict[str, Any]:
        """Classify recruiter replies — read-only triage."""
        blocked = self._require_enabled()
        if blocked:
            return blocked
        import email_sync

        return {
            "ok": True,
            "channel": self.name,
            "results": email_sync.scan_recruiter_emails(query, max_n=max_n),
        }

    def draft_followup(
        self, application_id: str, kind: str = "check_in"
    ) -> dict[str, Any]:
        """Build a follow-up draft and its content digest. Does NOT send.

        The wizard / UI shows ``draft`` to the user; the user then approves
        via ``request_send_approval`` (interactive), which returns the
        ``approval_id`` the send step requires. ``approval_token`` here is
        a content digest for display/reconciliation only — it authorizes
        nothing.
        """
        blocked = self._require_enabled()
        if blocked:
            return blocked
        import email_sync

        draft = email_sync.draft_followup(application_id, kind=kind)
        return {
            "ok": True,
            "channel": self.name,
            "draft": draft,
            "approval_token": draft_approval_token(draft),
        }

    def send_followup(
        self,
        draft: dict[str, Any],
        *,
        confirm: bool = False,
        approval_token: str | None = None,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        """Send a reviewed draft — only with a genuine user approval.

        Gates, all fail closed:
        1. the channel must be explicitly enabled (verified consent log);
        2. ``authorize_send`` must yield an approval: either ``approval_id``
           naming a valid, fresh, unconsumed interactive approval for this
           exact draft, or a fresh unconsumed approval already on file —
           otherwise the interactive prompt runs (TTY) or the send is
           refused (no TTY).

        ``confirm`` and ``approval_token`` are DEPRECATED: they authorize
        nothing. Passing them only routes through the same interactive
        approval — a caller cannot self-assert its way to a send. The
        actual send (and approval consumption) happens inside
        ``email_sync.send_followup``, which enforces the identical
        boundary for direct callers.
        """
        blocked = self._require_enabled()
        if blocked:
            return {"sent": False, **blocked}
        if confirm:
            log.warning(
                "GmailChannel.send_followup: confirm= is deprecated and is "
                "not proof of approval; an interactive user approval is "
                "still required."
            )
        if approval_token is not None:
            log.warning(
                "GmailChannel.send_followup: approval_token is deprecated — "
                "it is a content digest, not proof of approval, and is "
                "ignored for authorization."
            )
        import email_sync

        # Copy: never mutate the delegated module's result dict in place.
        result = dict(email_sync.send_followup(draft, approval_id=approval_id))
        result["channel"] = self.name
        return result
