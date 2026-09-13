"""Epic 3 — explicit opt-in communication channels.

Gmail plus user-selected WhatsApp, Discord, Messenger, or another approved
channel through explicit skills. User-selected and explicit ONLY:

* No channel is ever enabled by default, by upgrade, or by implication.
* ``enable_channel`` requires an explicit ``confirm=True`` from the user
  (the CLI wizard / web UI passes the user's own confirmation through).
* Every enable/disable is appended to an audit log (JSONL, local-first).
* Every channel carries a full ConnectorManifest: what it can do, why it
  may be blocked, what data it sends, which actions require confirmation.
* WhatsApp / Discord / Messenger are declared as explicit-skill channels:
  they do nothing until the user both selects the channel AND connects the
  corresponding skill. Veto stores no credentials for them.

The Gmail adapter delegates to the existing ``email_sync`` module (which
already gates sending behind ``confirm=True``); this registry adds the
consent layer around it.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from providers._contract import ConnectorManifest

log = logging.getLogger("job-apply-mcp.i09.channels")

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
CONSENT_LOG = BASE_DIR / "channel_consent.jsonl"


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
            "Send a reviewed follow-up draft — only with confirm=True at "
            "the moment of sending.",
        ],
        why_it_may_be_blocked=[
            "Gmail is not connected (no OAuth grant / CLI auth).",
            "Read-only triage needs the gmail skill's search scope; sending "
            "needs its send scope.",
        ],
        what_data_it_sends=[
            "Gmail search queries (recruiter-reply triage) to Google.",
            "Message IDs of opened messages to fetch their bodies.",
            "On confirmed send only: the reviewed draft's to/subject/body "
            "to Gmail's send endpoint.",
        ],
        what_requires_confirmation=[
            "Enabling the channel at all (explicit user opt-in).",
            "Every send: send_followup refuses without confirm=True.",
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
            "Every outbound message, individually, at send time.",
        ],
        official_interface=f"{skill} skill (explicit)",
        interface_basis="Explicit user selection + explicit skill only.",
    )


CHANNELS: dict[str, ChannelSpec] = {}


def _register(spec: ChannelSpec) -> None:
    assert spec.enabled_by_default is False, (
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
# Consent store (append-only, local-first)
# ---------------------------------------------------------------------------


def _append_consent(entry: dict[str, Any]) -> None:
    entry = {"ts": time.time(), **entry}
    try:
        CONSENT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with CONSENT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError as exc:
        log.warning("Could not append channel consent entry: %s", exc)


def consent_history(channel: str | None = None) -> list[dict[str, Any]]:
    """Read the consent audit log (newest last)."""
    if not CONSENT_LOG.exists():
        return []
    entries: list[dict[str, Any]] = []
    try:
        with CONSENT_LOG.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if channel is None or raw.get("channel") == channel:
                    entries.append(raw)
    except OSError:
        return []
    return entries


def is_enabled(channel: str) -> bool:
    """True only if the latest consent entry for the channel is an enable."""
    history = consent_history(channel)
    if not history:
        return False
    return history[-1].get("action") == "enable"


def enabled_channels() -> list[str]:
    """Channels the user has explicitly enabled and not since disabled."""
    return [name for name in CHANNELS if is_enabled(name)]


# ---------------------------------------------------------------------------
# Explicit opt-in / opt-out
# ---------------------------------------------------------------------------


def enable_channel(channel: str, *, confirm: bool = False, via: str = "") -> dict[str, Any]:
    """Enable a channel — ONLY with the user's explicit confirmation.

    ``confirm=True`` must carry the user's own opt-in (the wizard / UI
    passes it through; it is never defaulted). Without it, nothing changes
    and the caller gets instructions.
    """
    name = (channel or "").strip().lower()
    spec = CHANNELS.get(name)
    if spec is None:
        return {
            "ok": False,
            "error": f"unknown_channel: {channel!r}",
            "known_channels": sorted(CHANNELS),
        }
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
    _append_consent({"action": "enable", "channel": name, "via": via})
    log.info("Channel %r enabled via %r", name, via)
    return {"ok": True, "enabled": True, "channel": name}


def disable_channel(channel: str, *, via: str = "") -> dict[str, Any]:
    """Disable a channel immediately; appended to the audit log."""
    name = (channel or "").strip().lower()
    if name not in CHANNELS:
        return {"ok": False, "error": f"unknown_channel: {channel!r}"}
    _append_consent({"action": "disable", "channel": name, "via": via})
    log.info("Channel %r disabled via %r", name, via)
    return {"ok": True, "enabled": False, "channel": name}


def channel_manifest(channel: str) -> ConnectorManifest | None:
    """The proof-of-value declaration for a channel."""
    spec = CHANNELS.get((channel or "").strip().lower())
    return spec.manifest if spec else None


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
                    "first (enable_channel('gmail', confirm=True)); it never "
                    "auto-enables."
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

    def draft_followup(self, application_id: str, kind: str = "check_in") -> dict[str, Any]:
        """Build a follow-up draft. Does NOT send."""
        blocked = self._require_enabled()
        if blocked:
            return blocked
        import email_sync

        return {
            "ok": True,
            "channel": self.name,
            "draft": email_sync.draft_followup(application_id, kind=kind),
        }

    def send_followup(
        self, draft: dict[str, Any], *, confirm: bool = False
    ) -> dict[str, Any]:
        """Send a reviewed draft — refuses without confirm=True.

        Two gates: the channel must be enabled AND the send must be
        confirmed at the moment of action.
        """
        blocked = self._require_enabled()
        if blocked:
            return blocked
        if not confirm:
            return {
                "sent": False,
                "channel": self.name,
                "instructions": (
                    "Not sent. Review the draft, then call send_followup "
                    "with confirm=True. Veto never sends email on its own."
                ),
            }
        import email_sync

        result = email_sync.send_followup(draft, confirm=True)
        result["channel"] = self.name
        return result
