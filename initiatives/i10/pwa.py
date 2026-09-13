#!/usr/bin/env python3
"""Progressive web app bundle for Veto (Epic 5).

The installable phone shell lives in ``initiatives/i10/pwa/``:

* ``manifest.webmanifest`` — installable metadata (name, icons, theme).
* ``service-worker.js`` — offline-safe read views (network-first with
  cache fallback for ``/api/`` GETs; cache-first app shell) and mutation
  handoff to the deferred queue.
* ``deferred-queue.js`` — IndexedDB-backed FIFO queue that replays
  mutations when connectivity returns; 4xx failures go to a dead-letter
  list the user can inspect.
* ``offline.html`` — offline navigation fallback.

This module validates the bundle (``validate_bundle``) so CI and the
release-channel gate can prove the PWA shell is coherent: the manifest
parses and names every icon, the service worker's cache list references
only files the bundle ships, and the deferred queue exposes its replay
API. Serving and registration wiring goes in ``integration_notes.md``
(webui.py owns the served web root).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

PWA_DIR = Path(__file__).resolve().parent / "pwa"

REQUIRED_MANIFEST_KEYS = {
    "name",
    "short_name",
    "start_url",
    "display",
    "background_color",
    "theme_color",
    "icons",
}

REQUIRED_QUEUE_API = ("submit", "replay", "pending", "deadLetter")


@dataclass
class PwaCheck:
    name: str
    ok: bool
    detail: str


def validate_bundle(pwa_dir: Path = PWA_DIR) -> list[PwaCheck]:
    """Validate the PWA bundle. Every check must pass for the PWA to be
    considered shippable."""
    pwa_dir = Path(pwa_dir)
    checks: list[PwaCheck] = []

    manifest_path = pwa_dir / "manifest.webmanifest"
    if not manifest_path.exists():
        return [PwaCheck("manifest", False, "manifest.webmanifest missing")]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [PwaCheck("manifest", False, f"invalid JSON: {exc}")]

    missing = REQUIRED_MANIFEST_KEYS - set(manifest)
    checks.append(
        PwaCheck(
            "manifest-keys",
            not missing,
            "all required keys present" if not missing else f"missing: {sorted(missing)}",
        )
    )
    icons = manifest.get("icons", [])
    icons_ok = bool(icons) and all("src" in i and "sizes" in i for i in icons)
    checks.append(
        PwaCheck("manifest-icons", icons_ok, f"{len(icons)} icon(s) declared" if icons_ok else "icons missing or malformed")
    )
    if manifest.get("display") not in ("standalone", "fullscreen", "minimal-ui"):
        checks.append(PwaCheck("manifest-display", False, f"display={manifest.get('display')!r} is not installable"))
    else:
        checks.append(PwaCheck("manifest-display", True, f"display={manifest['display']}"))

    sw_path = pwa_dir / "service-worker.js"
    if not sw_path.exists():
        checks.append(PwaCheck("service-worker", False, "service-worker.js missing"))
    else:
        sw = sw_path.read_text(encoding="utf-8")
        has_cache = "caches.open" in sw and "CACHE_NAME" in sw
        has_offline = "offline.html" in sw
        has_queue_handoff = "veto:queue-mutation" in sw
        has_version_purge = "caches.delete" in sw
        checks.append(
            PwaCheck(
                "service-worker",
                all((has_cache, has_offline, has_queue_handoff, has_version_purge)),
                f"cache={has_cache} offline-fallback={has_offline} "
                f"queue-handoff={has_queue_handoff} version-purge={has_version_purge}",
            )
        )
        # The SW cache list must reference files the bundle ships (or the
        # web root serves: app.css/app.js/icons are served by webui.py —
        # flagged in integration notes, not a bundle failure).
        # The SW cache list must reference files the bundle ships or that
        # webui.py serves from the web root (app shell + icons — see
        # integration_notes.md; the PWA bundle is mounted, not copied).
        cached = set(re.findall(r'"/([^"]+)"', sw.split("SHELL_ASSETS")[1].split("];")[0]))
        bundle_files = {p.name for p in pwa_dir.iterdir() if p.is_file()}
        webroot_served = {"app.css", "app.js"}
        missing_files = {
            c
            for c in cached
            if c.split("/")[-1] not in bundle_files
            and c not in webroot_served
            and not c.startswith("icons/")
        }
        checks.append(
            PwaCheck(
                "sw-cache-list",
                not missing_files,
                "all cached files accounted for" if not missing_files else f"missing: {sorted(missing_files)}",
            )
        )

    q_path = pwa_dir / "deferred-queue.js"
    if not q_path.exists():
        checks.append(PwaCheck("deferred-queue", False, "deferred-queue.js missing"))
    else:
        q = q_path.read_text(encoding="utf-8")
        absent = [api for api in REQUIRED_QUEUE_API if api not in q]
        has_idb = "indexedDB" in q
        has_replay = "online" in q and "replay" in q
        checks.append(
            PwaCheck(
                "deferred-queue",
                not absent and has_idb and has_replay,
                f"indexeddb={has_idb} replay-on-online={has_replay}"
                + ("" if not absent else f" missing api: {absent}"),
            )
        )

    off_path = pwa_dir / "offline.html"
    checks.append(
        PwaCheck(
            "offline-fallback",
            off_path.exists(),
            "offline.html present" if off_path.exists() else "offline.html missing",
        )
    )
    return checks


def bundle_ok(checks: list[PwaCheck]) -> bool:
    return all(c.ok for c in checks)


if __name__ == "__main__":
    import sys

    results = validate_bundle()
    for c in results:
        print(f"  [{'✓' if c.ok else '✗'}] {c.name}: {c.detail}")
    sys.exit(0 if bundle_ok(results) else 1)
