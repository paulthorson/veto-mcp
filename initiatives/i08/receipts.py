#!/usr/bin/env python3
"""Initiative 08, Epic 4 — contributor receipts.

A local, hash-chained record per accepted contribution:

- WHAT: bundle hash, scrub ruleset version, byte count, session count.
- WHY: purpose + versioned purpose definition.
- WHEN: timestamp.
- REMOVAL: how to request removal, with honest limits stated per purpose
  ("where possible" — research aggregates cannot be un-published
  per-contributor once published; said plainly, not buried).
- IMPACT POINTER: bundle id linkable to ``record_impact`` entries.

Receipts are LOCAL-ONLY: they live in ``contributions/receipts.jsonl``,
are never transmitted, never appear in the public repo or the public
methodology, and are exportable by the user on demand.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .purposes import REMOVAL_LIMITS


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _contrib_dir(base_dir: Path | None) -> Path:
    if base_dir is not None:
        return Path(base_dir) / "contributions"
    import contribute

    return Path(contribute.CONTRIB_DIR)


def _receipts_path(contrib_dir: Path) -> Path:
    return contrib_dir / "receipts.jsonl"


def _read_receipts(contrib_dir: Path) -> list[dict[str, Any]]:
    path = _receipts_path(contrib_dir)
    receipts: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                receipts.append(json.loads(line))
    except (OSError, ValueError):
        pass
    return receipts


def _receipt_hash(receipt: dict[str, Any]) -> str:
    canonical = json.dumps(receipt, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def issue_receipt(
    *,
    bundle_hash: str,
    outbox_file: str,
    purpose: str,
    purpose_version: str,
    purpose_definition: str,
    scrub_ruleset: str,
    byte_count: int,
    session_count: int,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    """Issue a hash-chained local receipt for an accepted contribution."""
    from .purposes import PURPOSES  # local import: keeps module import light

    if purpose not in PURPOSES:
        raise ValueError(f"Unknown purpose {purpose!r}.")
    contrib_dir = _contrib_dir(base_dir)
    previous = _read_receipts(contrib_dir)
    prev_hash = previous[-1]["receipt_hash"] if previous else "GENESIS"
    receipt = {
        "receipt_id": _receipt_hash({
            "bundle_hash": bundle_hash,
            "issued_at": _utcnow(),
            "prev": prev_hash,
        })[:16],
        "issued_at": _utcnow(),
        "prev_receipt_hash": prev_hash,
        "bundle_hash": bundle_hash,
        "outbox_file": outbox_file,
        "purpose": purpose,
        "purpose_version": purpose_version,
        "purpose_definition": purpose_definition,
        "scrub_ruleset": scrub_ruleset,
        "byte_count": int(byte_count),
        "session_count": int(session_count),
        "removal": {
            "how": (
                "To request removal: reply to your delivery (e.g. comment "
                "on the PR) citing this receipt_id and bundle_hash, or "
                "contact the maintainer with them."
            ),
            "limits": REMOVAL_LIMITS[purpose],
        },
        "impact_pointer": {
            "how": ("Run the impact digest (contribution_impact_digest / "
                    "my-impact) to see which product change this bundle "
                    "informed, when traceable. Only bundles actually cited "
                    "by maintainers are attributed — never invented."),
            "bundle_id": outbox_file.replace(".json", ""),
        },
        "local_only": True,
    }
    receipt["receipt_hash"] = _receipt_hash(
        {k: v for k, v in receipt.items() if k != "receipt_hash"})
    path = _receipts_path(contrib_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(receipt, ensure_ascii=False) + "\n")
    return receipt


def list_receipts(base_dir: Path | None = None) -> dict[str, Any]:
    """List local receipts, newest first (local-only, never transmitted)."""
    contrib_dir = _contrib_dir(base_dir)
    receipts = _read_receipts(contrib_dir)
    return {
        "receipts": list(reversed(receipts)),
        "count": len(receipts),
        "local_only": True,
        "note": ("Receipts never leave this machine. Export one with "
                 "export_receipt(receipt_id) to share it yourself."),
    }


def export_receipt(receipt_id: str,
                   base_dir: Path | None = None) -> dict[str, Any]:
    """Return one receipt for user-driven export (copy/paste, attach)."""
    contrib_dir = _contrib_dir(base_dir)
    for receipt in _read_receipts(contrib_dir):
        if receipt.get("receipt_id") == receipt_id:
            lines = [
                "VETO CONTRIBUTION RECEIPT (local record — you chose to export this)",
                f"receipt_id: {receipt['receipt_id']}",
                f"issued_at: {receipt['issued_at']}",
                f"bundle_hash: {receipt['bundle_hash']}",
                f"outbox_file: {receipt['outbox_file']}",
                f"purpose: {receipt['purpose']} (definition v{receipt['purpose_version']})",
                f"scrub_ruleset: v{receipt['scrub_ruleset']}",
                f"sessions: {receipt['session_count']} | bytes: {receipt['byte_count']}",
                f"removal: {receipt['removal']['how']}",
                f"removal limits: {receipt['removal']['limits']}",
            ]
            return {"receipt": receipt,
                    "rendered": "\n".join(lines)}
    return {"error": f"Unknown receipt {receipt_id!r}."}


def verify_chain(base_dir: Path | None = None) -> dict[str, Any]:
    """Verify the receipt hash chain (tamper-evidence for the local log)."""
    contrib_dir = _contrib_dir(base_dir)
    receipts = _read_receipts(contrib_dir)
    prev = "GENESIS"
    for receipt in receipts:
        if receipt.get("prev_receipt_hash") != prev:
            return {"valid": False,
                    "broken_at": receipt.get("receipt_id")}
        body = {k: v for k, v in receipt.items() if k != "receipt_hash"}
        if _receipt_hash(body) != receipt.get("receipt_hash"):
            return {"valid": False,
                    "broken_at": receipt.get("receipt_id")}
        prev = receipt["receipt_hash"]
    return {"valid": True, "count": len(receipts)}
