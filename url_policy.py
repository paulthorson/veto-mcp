#!/usr/bin/env python3
"""Destination and workspace-path rules for outbound fetches and local files.

Listing fetches, apply-page navigation, and webhook delivery share one
check: only http(s) to a public destination. Saved HTML files and CSV
exports must stay under the repo or the user data directory.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent

ALLOWED_SCHEMES = ("http", "https")

#: Hostnames that must never be contacted, regardless of DNS.
BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
        "metadata",
    }
)

BLOCKED_NETWORKS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)

WEBHOOK_ALLOWED_HOSTS_ENV = "JOB_MCP_WEBHOOK_ALLOWED_HOSTS"
DATA_DIR_ENV = "VETO_DATA_DIR"


class PathDenied(ValueError):
    """A user-supplied path escaped the workspace."""


def user_data_root() -> Path:
    """Directory for machine-local user data (listings, exports, drafts)."""
    override = os.environ.get(DATA_DIR_ENV, "").strip()
    if override:
        return Path(override).expanduser().resolve()
    xdg = os.environ.get("XDG_DATA_HOME", "").strip()
    if xdg:
        return (Path(xdg).expanduser() / "veto").resolve()
    return (Path.home() / ".local" / "share" / "veto").resolve()


def allowed_file_roots() -> tuple[Path, ...]:
    roots = [REPO_ROOT]
    data = user_data_root()
    if data != REPO_ROOT:
        roots.append(data)
    return tuple(roots)


def confine_user_path(path: str | Path, *, purpose: str = "path") -> Path:
    """Resolve ``path`` and require it stay under the repo or user data dir.

    Rejects ``..`` in the supplied path and absolute paths that escape
    the allowed roots. Relative paths resolve under the repository root.
    """
    raw = Path(path)
    expanded = raw.expanduser()
    if ".." in raw.parts or ".." in expanded.parts:
        raise PathDenied(f"{purpose} must not contain '..'")
    if expanded.is_absolute():
        resolved = expanded.resolve()
    else:
        resolved = (REPO_ROOT / expanded).resolve()
    for root in allowed_file_roots():
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise PathDenied(
        f"{purpose} must stay under the workspace or user data directory"
    )


def _parse_ip(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def _ip_is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return any(ip in network for network in BLOCKED_NETWORKS)


def resolve_host_ips(host: str) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve ``host`` to IP addresses. IP literals are returned as-is."""
    literal = _parse_ip(host)
    if literal is not None:
        return [literal]
    infos = socket.getaddrinfo(host, None)
    ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    seen: set[str] = set()
    for info in infos:
        addr = info[4][0]
        if addr in seen:
            continue
        seen.add(addr)
        ip = _parse_ip(addr)
        if ip is not None:
            ips.append(ip)
    return ips


def destination_error(url: str, *, allow_file: bool = False) -> str | None:
    """Return a refusal message if ``url`` must not be fetched, else None."""
    url = (url or "").strip()
    if not url:
        return "Refusing empty URL"
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return f"Refusing invalid URL: {url!r}"
    scheme = (parts.scheme or "").lower()
    if scheme == "file":
        if not allow_file:
            return f"Refusing to fetch non-http(s) URL: {url!r}"
        path = urllib.parse.unquote(parts.path or "")
        if parts.netloc and parts.netloc not in ("", "localhost"):
            return f"Refusing file URL with a host: {url!r}"
        try:
            confine_user_path(path, purpose="local file URL")
        except PathDenied as exc:
            return str(exc)
        return None
    if scheme not in ALLOWED_SCHEMES:
        return f"Refusing to fetch non-http(s) URL: {url!r}"
    host = (parts.hostname or "").rstrip(".").lower()
    if not host:
        return f"Refusing URL with no host: {url!r}"
    if host in BLOCKED_HOSTS or host.endswith(".localhost"):
        return f"Refusing private or metadata destination: {host}"
    try:
        ips = resolve_host_ips(host)
    except (socket.gaierror, OSError, ValueError):
        return f"Refusing URL that could not be resolved: {host}"
    if not ips:
        return f"Refusing URL that could not be resolved: {host}"
    for ip in ips:
        if _ip_is_blocked(ip):
            return f"Refusing private or metadata destination: {host}"
    return None


def webhook_allowed_hosts() -> list[str]:
    raw = os.environ.get(WEBHOOK_ALLOWED_HOSTS_ENV, "")
    return [part.strip().lower() for part in raw.split(",") if part.strip()]


def webhook_error(url: str) -> str | None:
    """Return a refusal message if a webhook URL must not be POSTed to."""
    url = (url or "").strip()
    if not url:
        return "Webhook URL is empty"
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return f"Refusing invalid webhook URL: {url!r}"
    if (parts.scheme or "").lower() != "https":
        return "Webhook URL must use https"
    hosts = webhook_allowed_hosts()
    if not hosts:
        return (
            "Webhook host allowlist is empty; set "
            f"{WEBHOOK_ALLOWED_HOSTS_ENV} to a comma-separated host list"
        )
    host = (parts.hostname or "").rstrip(".").lower()
    if not host or host not in hosts:
        return f"Webhook host {host!r} is not in {WEBHOOK_ALLOWED_HOSTS_ENV}"
    return destination_error(url)
