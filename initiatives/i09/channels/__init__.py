"""Epic 3 — explicit opt-in communication channels (see registry.py)."""

from initiatives.i09.channels.registry import (
    CHANNELS,
    GmailChannel,
    channel_manifest,
    consent_history,
    disable_channel,
    enable_channel,
    enabled_channels,
    is_enabled,
)

__all__ = [
    "CHANNELS",
    "GmailChannel",
    "channel_manifest",
    "consent_history",
    "disable_channel",
    "enable_channel",
    "enabled_channels",
    "is_enabled",
]
