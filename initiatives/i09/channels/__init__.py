"""Epic 3 — explicit opt-in communication channels (see registry.py)."""

from initiatives.i09.channels.registry import (
    CHANNELS,
    VALID_VIA_SOURCES,
    GmailChannel,
    authorize_send,
    channel_manifest,
    consent_history,
    consume_approval,
    disable_channel,
    draft_approval_token,
    enable_channel,
    enabled_channels,
    is_enabled,
    request_send_approval,
    rotate_consent_key,
)

__all__ = [
    "CHANNELS",
    "VALID_VIA_SOURCES",
    "GmailChannel",
    "authorize_send",
    "channel_manifest",
    "consent_history",
    "consume_approval",
    "disable_channel",
    "draft_approval_token",
    "enable_channel",
    "enabled_channels",
    "is_enabled",
    "request_send_approval",
    "rotate_consent_key",
]
