#!/usr/bin/env python3
"""Versioned resume variants — Epic 1 of Initiative 05.

A **base** resume plus role-specific **branches**, each branch holding
an append-only chain of **versions** with provenance. Any prior version
can be restored byte-for-byte, and every tailored statement in a
version maps to the approved evidence behind it (see
:mod:`initiatives.i05.contracts`).

Storage layout (JSON, atomic tmp+rename writes)::

    resume_variants/<variant_id>.json
        {"variant_id", "branch_name", "job_id", "parent_variant",
         "created_at", "current_version", "versions": [...]}

A version carries ``provenance`` — job id, matched/missing skills, a
``statement_map`` of ``{"statement", "evidence_ids", "link_ids"}``
entries, and an approval flag. Drafts are drafts until
:func:`approve_version` is called; only approved versions may be used
in an application packet.

Honesty contract: versions store rendered text only. They never invent
facts — provenance records *which* evidence justified each statement
so an independent reviewer can trace every claim.
"""

from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contracts import CONTRACT_VERSION

log = logging.getLogger("job-apply-mcp.i05.versions")

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_VARIANTS_DIR = BASE_DIR / "resume_variants"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _safe_name(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", str(name or "")).strip("_")
    return safe[:80] or "variant"


def _dir(variants_dir: Path | None, create: bool = False) -> Path:
    d = Path(variants_dir) if variants_dir else DEFAULT_VARIANTS_DIR
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def _variant_path(variants_dir: Path, variant_id: str) -> Path:
    return variants_dir / f"{_safe_name(variant_id)}.json"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    tmp = path.with_name(
        path.name + f".{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("ignoring unreadable variant file %s: %s", path, exc)
        return None
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------------------
# Branch / version lifecycle
# ---------------------------------------------------------------------------


def create_base(
    profile: dict[str, Any],
    branch_name: str = "base",
    variants_dir: Path | None = None,
) -> dict[str, Any]:
    """Create the base variant from the user's real profile.

    Renders the untailored resume via :mod:`tailor` so the base is
    byte-identical in format to tailored branches. The profile is the
    only fact source — nothing is invented. The first version's
    statement_map records every rendered line as profile-sourced so
    the base is fully traceable from birth.
    """
    import sys

    repo_root = Path(__file__).resolve().parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    import tailor as tailor_mod

    resume_md = tailor_mod.base_resume_md(profile)
    statement_map = [
        {"statement": line.strip(), "evidence_ids": ["profile:base"],
         "link_ids": []}
        for line in resume_md.splitlines()
        if line.strip()
        and not line.strip().startswith("#")
        and "|" not in line
    ]
    provenance = {
        "job_id": "",
        "matched_skills": [],
        "missing_skills": [],
        "statement_map": statement_map,
        "tailor_version": "base",
    }
    return create_variant(
        branch_name=branch_name,
        job_id="",
        parent_variant_id=None,
        initial_resume_md=resume_md,
        initial_cover_letter="",
        provenance=provenance,
        variants_dir=variants_dir,
    )


def create_variant(
    branch_name: str,
    job_id: str = "",
    parent_variant_id: str | None = None,
    initial_resume_md: str = "",
    initial_cover_letter: str = "",
    provenance: dict[str, Any] | None = None,
    variants_dir: Path | None = None,
) -> dict[str, Any]:
    """Create a branch (or the base) and commit its first version.

    ``parent_variant_id`` links a role-specific branch to its parent;
    ``None`` marks the base. Returns the stored variant record.
    """
    d = _dir(variants_dir, create=True)
    variant_id = _new_id("var")
    now = _utcnow()
    version = _make_version(
        resume_md=initial_resume_md,
        cover_letter=initial_cover_letter,
        provenance=provenance,
        parent_version=None,
        created_at=now,
    )
    variant = {
        "variant_id": variant_id,
        "branch_name": _safe_name(branch_name),
        "job_id": str(job_id or ""),
        "parent_variant": parent_variant_id,
        "created_at": now,
        "current_version": version["version_id"],
        "versions": [version],
    }
    _write_json(_variant_path(d, variant_id), variant)
    log.info("variant %s (%s) created", variant_id, branch_name)
    return variant


def _make_version(
    resume_md: str,
    cover_letter: str,
    provenance: dict[str, Any] | None,
    parent_version: str | None,
    created_at: str,
) -> dict[str, Any]:
    prov = dict(provenance or {})
    prov.setdefault("evidence_contract", CONTRACT_VERSION)
    prov.setdefault("approved", False)
    return {
        "version_id": _new_id("ver"),
        "parent_version": parent_version,
        "created_at": created_at,
        "resume_md": resume_md or "",
        "cover_letter": cover_letter or "",
        "provenance": prov,
    }


def commit_version(
    variant_id: str,
    resume_md: str,
    cover_letter: str = "",
    provenance: dict[str, Any] | None = None,
    variants_dir: Path | None = None,
) -> dict[str, Any]:
    """Append a new version to a branch; returns the version record.

    The new version's ``parent_version`` points at the previous head,
    forming the restore chain. Commits start unapproved.
    """
    d = _dir(variants_dir, create=True)
    path = _variant_path(d, variant_id)
    variant = _read_json(path)
    if variant is None:
        raise KeyError(f"unknown variant: {variant_id}")
    head = variant["current_version"]
    version = _make_version(
        resume_md=resume_md,
        cover_letter=cover_letter,
        provenance=provenance,
        parent_version=head,
        created_at=_utcnow(),
    )
    variant["versions"].append(version)
    variant["current_version"] = version["version_id"]
    _write_json(path, variant)
    return version


def get_variant(
    variant_id: str, variants_dir: Path | None = None
) -> dict[str, Any] | None:
    """Load a variant record, or ``None`` when absent/unreadable."""
    d = _dir(variants_dir)
    return _read_json(_variant_path(d, variant_id))


def list_variants(variants_dir: Path | None = None) -> list[dict[str, Any]]:
    """Summaries of all variants: id, branch, job, version count, head."""
    d = _dir(variants_dir)
    if not d.is_dir():
        return []
    out = []
    for path in sorted(d.glob("var_*.json")):
        v = _read_json(path)
        if v is None:
            continue
        out.append(
            {
                "variant_id": v.get("variant_id"),
                "branch_name": v.get("branch_name"),
                "job_id": v.get("job_id"),
                "parent_variant": v.get("parent_variant"),
                "version_count": len(v.get("versions", [])),
                "current_version": v.get("current_version"),
            }
        )
    return out


def get_version(
    variant_id: str,
    version_id: str,
    variants_dir: Path | None = None,
) -> dict[str, Any] | None:
    """Fetch one version by id, or ``None``."""
    variant = get_variant(variant_id, variants_dir)
    if variant is None:
        return None
    for v in variant.get("versions", []):
        if v.get("version_id") == version_id:
            return v
    return None


def history(
    variant_id: str, variants_dir: Path | None = None
) -> list[dict[str, Any]]:
    """Newest-first version summaries for a branch."""
    variant = get_variant(variant_id, variants_dir)
    if variant is None:
        return []
    items = []
    for v in variant.get("versions", []):
        prov = v.get("provenance", {}) or {}
        items.append(
            {
                "version_id": v.get("version_id"),
                "parent_version": v.get("parent_version"),
                "created_at": v.get("created_at"),
                "approved": bool(prov.get("approved")),
                "job_id": prov.get("job_id", ""),
                "is_current": v.get("version_id") == variant.get("current_version"),
            }
        )
    return list(reversed(items))


# ---------------------------------------------------------------------------
# Restore — any prior version, byte-for-byte
# ---------------------------------------------------------------------------


def restore_version(
    variant_id: str,
    version_id: str | None = None,
    variants_dir: Path | None = None,
) -> dict[str, Any]:
    """Return the content of a prior version: ``resume_md``,
    ``cover_letter``, ``provenance``.

    ``version_id=None`` restores the current head. The returned text is
    the exact stored rendering — restore never re-renders or edits.
    Raises :class:`KeyError` for unknown variants/versions.
    """
    variant = get_variant(variant_id, variants_dir)
    if variant is None:
        raise KeyError(f"unknown variant: {variant_id}")
    target = version_id or variant.get("current_version")
    version = get_version(variant_id, target, variants_dir)
    if version is None:
        raise KeyError(f"unknown version {target} in variant {variant_id}")
    return {
        "variant_id": variant_id,
        "version_id": target,
        "resume_md": version.get("resume_md", ""),
        "cover_letter": version.get("cover_letter", ""),
        "provenance": version.get("provenance", {}),
    }


def checkout_version(
    variant_id: str,
    version_id: str,
    variants_dir: Path | None = None,
) -> dict[str, Any]:
    """Point a branch's head at a prior version (restore as current).

    History is append-only: the old head stays in the chain, and the
    checkout is recorded in the variant's audit trail. Returns the
    restored content (same shape as :func:`restore_version`).
    """
    d = _dir(variants_dir, create=True)
    path = _variant_path(d, variant_id)
    variant = _read_json(path)
    if variant is None:
        raise KeyError(f"unknown variant: {variant_id}")
    if get_version(variant_id, version_id, variants_dir) is None:
        raise KeyError(f"unknown version {version_id} in variant {variant_id}")
    previous = variant.get("current_version")
    variant["current_version"] = version_id
    audit = variant.setdefault("audit", [])
    audit.append(
        {
            "action": "checkout",
            "from": previous,
            "to": version_id,
            "at": _utcnow(),
        }
    )
    _write_json(path, variant)
    log.info("variant %s checked out %s (was %s)", variant_id, version_id, previous)
    return restore_version(variant_id, version_id, variants_dir)


# ---------------------------------------------------------------------------
# Approval + claim tracing
# ---------------------------------------------------------------------------


def approve_version(
    variant_id: str,
    version_id: str,
    variants_dir: Path | None = None,
) -> dict[str, Any]:
    """Mark a version approved for use in an application packet.

    Approval is explicit and timestamped; it never alters content.
    """
    d = _dir(variants_dir, create=True)
    path = _variant_path(d, variant_id)
    variant = _read_json(path)
    if variant is None:
        raise KeyError(f"unknown variant: {variant_id}")
    for v in variant.get("versions", []):
        if v.get("version_id") == version_id:
            prov = v.setdefault("provenance", {})
            prov["approved"] = True
            prov["approved_at"] = _utcnow()
            _write_json(path, variant)
            return v
    raise KeyError(f"unknown version {version_id} in variant {variant_id}")


def _norm(text: str) -> str:
    # Fold whitespace/case and strip leading list markers: the claim is
    # the text, not the markdown decoration, so a reviewer pasting a
    # statement with or without its "- " still traces.
    s = re.sub(r"\s+", " ", str(text or "")).strip().lower()
    return re.sub(r"^([-*•]|\d+[.)])\s+", "", s)


def trace_statement(
    variant_id: str,
    version_id: str,
    statement: str,
    variants_dir: Path | None = None,
) -> list[dict[str, str]]:
    """Trace a tailored statement to the evidence behind it.

    Matches ``statement`` against the version's ``provenance``
    ``statement_map`` on exact normalized equality (whitespace/case
    folded). Deliberately NOT fuzzy: a lenient match could claim a
    trace that isn't real, which would defeat the proof-of-value.
    Returns the matching entries ``{"statement", "evidence_ids",
    "link_ids"}`` — empty when the statement is not recorded, which
    itself is a finding: every tailored claim must be traceable.
    """
    version = get_version(variant_id, version_id, variants_dir)
    if version is None:
        raise KeyError(f"unknown version {version_id} in variant {variant_id}")
    needle = _norm(statement)
    if not needle:
        return []
    hits = []
    for entry in (version.get("provenance", {}) or {}).get("statement_map", []) or []:
        recorded = _norm(entry.get("statement", ""))
        if recorded and recorded == needle:
            hits.append(
                {
                    "statement": entry.get("statement", ""),
                    "evidence_ids": list(entry.get("evidence_ids", []) or []),
                    "link_ids": list(entry.get("link_ids", []) or []),
                }
            )
    return hits


def trace_report(
    variant_id: str,
    version_id: str,
    evidence_items: list[dict[str, Any]] | None = None,
    variants_dir: Path | None = None,
) -> dict[str, Any]:
    """Join every statement to the approval status of its evidence.

    ``evidence_items`` are evidence-store records (Initiatives 01–02
    contract, or the studio's own evidence library). Each referenced
    evidence id is classified:

    * ``profile`` — a ``profile:*`` source reference (the user's own
      profile text; the anti-invention anchor);
    * ``approved`` — a known item with ``approved=True``;
    * ``unapproved`` — a known item not yet approved;
    * ``unknown`` — referenced but not found in ``evidence_items``.

    Returns ``{"statements", "unapproved", "unknown"}``. A clean report
    (empty ``unapproved`` and ``unknown``) is the mechanical proof that
    every tailored statement traces to approved evidence.
    """
    version = get_version(variant_id, version_id, variants_dir)
    if version is None:
        raise KeyError(f"unknown version {version_id} in variant {variant_id}")
    by_id = {
        str(i.get("evidence_id")): i for i in (evidence_items or [])
        if isinstance(i, dict)
    }
    statements = []
    unapproved: list[str] = []
    unknown: list[str] = []
    for entry in (version.get("provenance", {}) or {}).get("statement_map", []) or []:
        statuses: dict[str, str] = {}
        for eid in entry.get("evidence_ids", []) or []:
            eid = str(eid)
            if eid.startswith("profile:"):
                statuses[eid] = "profile"
            elif eid in by_id:
                if by_id[eid].get("approved") is True:
                    statuses[eid] = "approved"
                else:
                    statuses[eid] = "unapproved"
                    if eid not in unapproved:
                        unapproved.append(eid)
            else:
                statuses[eid] = "unknown"
                if eid not in unknown:
                    unknown.append(eid)
        statements.append(
            {
                "statement": entry.get("statement", ""),
                "evidence_ids": list(entry.get("evidence_ids", []) or []),
                "link_ids": list(entry.get("link_ids", []) or []),
                "evidence_status": statuses,
            }
        )
    return {
        "statements": statements,
        "unapproved": unapproved,
        "unknown": unknown,
    }


def untraced_statements(
    variant_id: str,
    version_id: str,
    resume_md: str | None = None,
    variants_dir: Path | None = None,
) -> list[str]:
    """Resume lines with no statement_map entry — the trace gaps.

    An independent reviewer runs this to prove the proof-of-value:
    every tailored statement traces to approved evidence. Returns the
    offending lines (headers/contact lines excluded).
    """
    version = get_version(variant_id, version_id, variants_dir)
    if version is None:
        raise KeyError(f"unknown version {version_id} in variant {variant_id}")
    text = resume_md if resume_md is not None else version.get("resume_md", "")
    mapped = {
        _norm(e.get("statement", ""))
        for e in (version.get("provenance", {}) or {}).get("statement_map", []) or []
    }
    gaps = []
    for line in str(text).splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("*") or "|" in s:
            continue
        if _norm(s) not in mapped:
            gaps.append(s)
    return gaps
