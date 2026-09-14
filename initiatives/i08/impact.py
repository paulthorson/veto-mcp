#!/usr/bin/env python3
"""Initiative 08, Epic 6 — impact feedback.

Tell contributors which product change their accepted contribution
informed, WHEN TRACEABLE. Traceability rule (non-negotiable): only
bundles ACTUALLY CITED in a maintainer's ``record_impact`` entry are
attributed. Uncited bundles are reported plainly as "not yet cited" —
attribution is never invented.

This module extends ``contribute``'s impact loop (``record_impact`` /
``impact_log`` / ``my_impact``) with explicit traceability flags and a
digest renderer suitable for the terminal dashboard, local web UI, and
phone surfaces.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _impact_entries(base_dir: Path | None = None) -> list[dict[str, Any]]:
    import contribute

    if base_dir is not None:
        path = Path(base_dir) / "contributions" / "impact.json"
    else:
        path = Path(contribute.IMPACT_PATH)
    try:
        import json

        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        entries = []
    return entries if isinstance(entries, list) else []


def _local_bundle_ids(base_dir: Path | None = None) -> list[str]:
    import contribute

    if base_dir is not None:
        outbox = Path(base_dir) / "contributions" / "outbox"
    else:
        outbox = Path(contribute.OUTBOX_DIR)
    if not outbox.is_dir():
        return []
    return sorted(p.stem for p in outbox.glob("*.json"))


def contribution_impact_status(
    bundle_id: str, base_dir: Path | None = None
) -> dict[str, Any]:
    """Traceability status for one bundle id.

    ``traceable`` is True ONLY when at least one impact entry cites the
    bundle. Otherwise the bundle is honestly "not yet cited".
    """
    cited_by: list[dict[str, Any]] = []
    for entry in _impact_entries(base_dir):
        if bundle_id in (entry.get("bundle_ids") or []):
            cited_by.append({
                "persona": entry.get("persona"),
                "version": entry.get("version"),
                "change": entry.get("change"),
                "recorded_at": entry.get("recorded_at"),
            })
    return {
        "bundle_id": bundle_id,
        "traceable": bool(cited_by),
        "cited_by": cited_by,
        "headline": (
            f"Bundle {bundle_id} informed "
            + "; ".join(f"{c['persona']} v{c['version']} — {c['change']}"
                        for c in cited_by)
            if cited_by else
            f"Bundle {bundle_id} has not been cited in a product change "
            "yet. Maintainers cite contributions in the impact log when a "
            "change ships — check back after the next release."
        ),
    }


def impact_digest(base_dir: Path | None = None) -> dict[str, Any]:
    """Contributor-facing digest: what did MY contributions change?

    Scans this machine's outbox and links each local bundle to the
    impact entries that cite it. Only cited bundles are attributed.
    """
    local = _local_bundle_ids(base_dir)
    entries = _impact_entries(base_dir)
    per_bundle: dict[str, list[dict[str, Any]]] = {b: [] for b in local}
    for entry in entries:
        for bid in entry.get("bundle_ids") or []:
            if bid in per_bundle:
                per_bundle[bid].append({
                    "persona": entry.get("persona"),
                    "version": entry.get("version"),
                    "change": entry.get("change"),
                    "recorded_at": entry.get("recorded_at"),
                })
    attributed = {b: cites for b, cites in per_bundle.items() if cites}
    pending = [b for b, cites in per_bundle.items() if not cites]
    lines: list[str] = []
    if not local:
        lines.append("No contributed bundles on this machine yet.")
    else:
        lines.append(
            f"{len(local)} contributed bundle(s) on this machine: "
            f"{len(attributed)} traceable to a product change, "
            f"{len(pending)} not yet cited.")
        for bid, cites in sorted(attributed.items()):
            for cite in cites:
                lines.append(
                    f"  • {bid}: informed {cite['persona']} "
                    f"v{cite['version']} — {cite['change']}")
        if pending:
            lines.append(
                "  Not yet cited: " + ", ".join(sorted(pending)))
    return {
        "contributed_bundles": len(local),
        "traceable": len(attributed),
        "pending": len(pending),
        "per_bundle": {
            b: {"traceable": bool(c), "cited_by": c}
            for b, c in per_bundle.items()
        },
        "rendered": "\n".join(lines),
    }
