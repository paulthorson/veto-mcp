#!/usr/bin/env python3
"""Warm-path planner (Initiative 07, epic 5).

Identifies user-provided connections toward a target company — via the
network CRM's warm paths and the referral radar — and DRAFTS outreach for
each path.

**The planner never sends anything.** Drafts are written to the draft
outbox (``draft_outbox.jsonl``) for the user to review, edit, and send
themselves in their own client. There is deliberately no send path in
this module: no function named ``send_*`` exists, and the test suite
asserts that none ever appears.

Honesty rules (hard, inherited from referrals/network_crm):
  * Relationship strength is never inferred or fabricated.
  * Drafts never invent shared history, shared employers, or mutual
    acquaintances — only facts present in the user's own records.
  * An empty network produces an honest empty plan, never invented people.

Stdlib only.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("job-apply-mcp.i07.warm_path")

BASE_DIR = Path(__file__).resolve().parent

#: Draft outbox: every draft the planner produces, for human review.
#: Reassign in tests.
DRAFT_OUTBOX = BASE_DIR / "draft_outbox.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _record_draft(draft: dict[str, Any]) -> dict[str, Any]:
    """Append a draft to the outbox. Review artifact only — never sent."""
    DRAFT_OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    draft = dict(draft)
    draft["draft_id"] = "draft-" + uuid.uuid4().hex[:12]
    draft["created_at"] = _now()
    draft["status"] = "draft"  # terminal: no code path ever changes this
    with DRAFT_OUTBOX.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(draft, ensure_ascii=False) + "\n")
    return draft


def list_drafts() -> list[dict[str, Any]]:
    """Read the draft outbox for human review."""
    drafts: list[dict[str, Any]] = []
    try:
        with DRAFT_OUTBOX.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        drafts.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except FileNotFoundError:
        pass
    return drafts


def plan_warm_path(
    target_company: str,
    *,
    profile: dict[str, Any] | None = None,
    max_paths: int = 5,
    synthetic: bool = False,
) -> dict[str, Any]:
    """Build a warm-path outreach plan toward ``target_company``.

    Returns ranked paths (CRM warm paths first, then referral prospects),
    each with a DRAFT message, the evidence behind it, and an honesty
    checklist. Empty network -> honest empty plan with guidance.
    """
    import network_crm as _crm
    import referrals as _ref

    if not str(target_company or "").strip():
        return {"ok": False, "error": "target_company is required"}

    plans: list[dict[str, Any]] = []

    # 1. CRM warm paths (user's own recorded network).
    try:
        crm_paths = _crm.warm_path_to(target_company)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    for path in crm_paths[:max_paths]:
        contact = {
            "name": path.get("contact_name", ""),
            "company": path.get("path_companies", [""])[-1],
            "position": path.get("contact_role", ""),
        }
        draft_text = _ref.draft_outreach(
            contact,
            job={"company": target_company},
            profile=profile,
            kind="warm",
        )
        record = _record_draft(
            {
                "kind": "crm_warm_path",
                "target_company": target_company,
                "degrees": path.get("degrees"),
                "via": path.get("via"),
                "to": draft_text["to"],
                "subject": draft_text["subject"],
                "body": draft_text["body"],
                "evidence": ["recorded contact", path.get("via", "")],
                "synthetic": synthetic,
            }
        )
        plans.append(
            {
                "source": "network_crm",
                "degrees": path.get("degrees"),
                "contact_name": path.get("contact_name"),
                "via": path.get("via"),
                "draft_id": record["draft_id"],
                "draft": {"subject": record["subject"], "body": record["body"]},
            }
        )

    # 2. Referral-radar prospects at the target company.
    try:
        connections = _ref.load_network()
    except Exception:  # noqa: BLE001 - radar is best-effort
        connections = []
    if connections:
        ranked = _ref.rank_referrals(connections, [target_company], profile)
        for prospect in ranked[:max_paths]:
            if any(
                p.get("contact_name") == prospect.get("name") for p in plans
            ):
                continue
            draft_text = _ref.draft_outreach(
                prospect,
                job={"company": target_company},
                profile=profile,
                kind="warm",
            )
            record = _record_draft(
                {
                    "kind": "referral_prospect",
                    "target_company": target_company,
                    "score": prospect.get("score"),
                    "reasons": prospect.get("reasons"),
                    "to": draft_text["to"],
                    "subject": draft_text["subject"],
                    "body": draft_text["body"],
                    "evidence": prospect.get("evidence", []),
                    "synthetic": synthetic,
                }
            )
            plans.append(
                {
                    "source": "referrals",
                    "contact_name": prospect.get("name"),
                    "score": prospect.get("score"),
                    "reasons": prospect.get("reasons"),
                    "evidence": prospect.get("evidence"),
                    "draft_id": record["draft_id"],
                    "draft": {"subject": record["subject"], "body": record["body"]},
                }
            )
            if len(plans) >= max_paths:
                break

    honesty_checklist = [
        "Every path is derived from your own recorded contacts — none invented.",
        "Drafts claim no shared history, shared employers, or mutual acquaintances.",
        "Relationship strength is not inferred; every contact is labeled 'connection'.",
        "Nothing has been sent. Review each draft, edit in your voice, send it yourself.",
    ]
    if not plans:
        return {
            "ok": True,
            "target_company": target_company,
            "plans": [],
            "honesty_checklist": honesty_checklist,
            "guidance": (
                f"No warm path to {target_company} in your recorded network yet. "
                "Add contacts you actually know with network_crm.add_contact, "
                "log real interactions, and re-run — the planner will never "
                "invent people to fill the gap."
            ),
        }
    return {
        "ok": True,
        "target_company": target_company,
        "plans": plans,
        "honesty_checklist": honesty_checklist,
        "guidance": (
            f"{len(plans)} draft(s) ready for review in the draft outbox. "
            "Nothing has been sent and nothing will be sent by this tool."
        ),
    }


def discard_draft(draft_id: str) -> dict[str, Any]:
    """Remove a draft from the outbox (human rejected it)."""
    kept: list[dict[str, Any]] = []
    found = False
    for draft in list_drafts():
        if draft.get("draft_id") == draft_id:
            found = True
            continue
        kept.append(draft)
    if not found:
        return {"ok": False, "error": f"unknown draft id {draft_id!r}"}
    with DRAFT_OUTBOX.open("w", encoding="utf-8") as fh:
        for draft in kept:
            fh.write(json.dumps(draft, ensure_ascii=False) + "\n")
    return {"ok": True, "discarded": draft_id}
