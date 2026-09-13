#!/usr/bin/env python3
"""Evidence library — Epic 2 of Initiative 05.

Reusable achievements, portfolio links, metrics, and approved phrasing,
each tied to a source fact. Items satisfy the Initiatives 01–02
evidence-store contract (see :mod:`initiatives.i05.contracts`); until
those teams land, this library is the studio's evidence source of
record.

Hard rules:

* **Never invent.** :func:`build_from_profile` derives drafts ONLY from
  the user's real profile. :func:`add_item` records caller-supplied
  text verbatim with its source — it never generates content.
* **Approval gates use.** Items start as drafts (``approved=False``).
  Only ``approved=True`` items may back a tailored statement (see
  :func:`contracts.approved_evidence`). Editing an approved item's text
  resets approval — approval is of the exact wording.
* Storage is a single JSON file with atomic tmp+rename writes, inside a
  gitignored directory (evidence text is the user's personal data).

Portfolio links come from the profile's own URL fields; metrics are
bullets containing numbers, quoted verbatim.
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

from .contracts import CONTRACT_VERSION, normalize_evidence

log = logging.getLogger("job-apply-mcp.i05.evidence_library")

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_LIBRARY_DIR = BASE_DIR / "evidence_library"
_LIBRARY_FILE = "library.json"

KINDS = ("achievement", "metric", "portfolio_link", "approved_phrase")

_NUMBER_RE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return f"ev_{uuid.uuid4().hex[:12]}"


def _lib_path(library_dir: Path | None, create: bool) -> Path:
    d = Path(library_dir) if library_dir else DEFAULT_LIBRARY_DIR
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d / _LIBRARY_FILE


def _load(library_dir: Path | None) -> dict[str, Any]:
    path = _lib_path(library_dir, create=False)
    if not path.is_file():
        return {"schema": CONTRACT_VERSION, "items": []}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("ignoring unreadable evidence library %s: %s", path, exc)
        return {"schema": CONTRACT_VERSION, "items": []}
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return {"schema": CONTRACT_VERSION, "items": []}
    return data


def _save(library_dir: Path | None, payload: dict[str, Any]) -> None:
    path = _lib_path(library_dir, create=True)
    tmp = path.with_name(
        path.name + f".{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# CRUD + approval
# ---------------------------------------------------------------------------


def add_item(
    kind: str,
    text: str,
    source: str,
    library_dir: Path | None = None,
) -> dict[str, Any]:
    """Record a new evidence item as a draft (``approved=False``).

    ``text`` is stored verbatim — this function never generates or
    embellishes content. ``source`` names the profile fact it came from
    (e.g. ``experience[0].bullets[2]``); empty source is rejected.
    Raises :class:`ValueError` on contract violations.
    """
    text = str(text or "").strip()
    source = str(source or "").strip()
    if not text:
        raise ValueError("evidence text must not be empty")
    if not source:
        raise ValueError("evidence source must name the profile fact")
    item = normalize_evidence(
        {
            "evidence_id": _new_id(),
            "kind": kind,
            "text": text,
            "source": source,
            "approved": False,
            "created_at": _utcnow(),
            "used_in": [],
        }
    )
    lib = _load(library_dir)
    lib["items"].append(item)
    _save(library_dir, lib)
    return item


def get_item(
    evidence_id: str, library_dir: Path | None = None
) -> dict[str, Any] | None:
    """Fetch one item by id, or ``None``."""
    for item in _load(library_dir)["items"]:
        if item.get("evidence_id") == evidence_id:
            return item
    return None


def list_items(
    kind: str | None = None,
    approved_only: bool = False,
    library_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """List items, optionally filtered by kind and approval."""
    out = []
    for item in _load(library_dir)["items"]:
        if kind is not None and item.get("kind") != kind:
            continue
        if approved_only and item.get("approved") is not True:
            continue
        out.append(item)
    return out


def approve_item(
    evidence_id: str, library_dir: Path | None = None
) -> dict[str, Any]:
    """Approve an item's exact current text for use in tailoring.

    Raises :class:`KeyError` when unknown.
    """
    lib = _load(library_dir)
    for item in lib["items"]:
        if item.get("evidence_id") == evidence_id:
            item["approved"] = True
            item["approved_at"] = _utcnow()
            _save(library_dir, lib)
            return item
    raise KeyError(f"unknown evidence item: {evidence_id}")


def update_item(
    evidence_id: str,
    text: str,
    library_dir: Path | None = None,
) -> dict[str, Any]:
    """Replace an item's text. Approval resets to ``False``.

    Approval is of the exact wording — an edited item must be
    re-approved before it can back a statement again.
    """
    text = str(text or "").strip()
    if not text:
        raise ValueError("evidence text must not be empty")
    lib = _load(library_dir)
    for item in lib["items"]:
        if item.get("evidence_id") == evidence_id:
            item["text"] = text
            item["approved"] = False
            item.pop("approved_at", None)
            _save(library_dir, lib)
            return item
    raise KeyError(f"unknown evidence item: {evidence_id}")


def delete_item(evidence_id: str, library_dir: Path | None = None) -> bool:
    """Delete a draft item. Approved items are protected: unapprove via
    :func:`update_item` first. Returns True when deleted."""
    lib = _load(library_dir)
    for i, item in enumerate(lib["items"]):
        if item.get("evidence_id") == evidence_id:
            if item.get("approved") is True:
                raise ValueError(
                    "cannot delete an approved item; edit it (which "
                    "resets approval) or keep it as history"
                )
            del lib["items"][i]
            _save(library_dir, lib)
            return True
    return False


def record_use(
    evidence_id: str,
    variant_id: str,
    library_dir: Path | None = None,
) -> None:
    """Note that a resume variant used an evidence item (provenance)."""
    lib = _load(library_dir)
    for item in lib["items"]:
        if item.get("evidence_id") == evidence_id:
            used = item.setdefault("used_in", [])
            if variant_id not in used:
                used.append(variant_id)
            _save(library_dir, lib)
            return
    raise KeyError(f"unknown evidence item: {evidence_id}")


# ---------------------------------------------------------------------------
# Derivation from the real profile (never invents)
# ---------------------------------------------------------------------------


def build_from_profile(
    profile: dict[str, Any],
    library_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Derive draft evidence items from the user's real profile.

    * every experience bullet -> ``achievement``;
    * bullets containing numbers -> also ``metric`` (quoted verbatim);
    * every skill -> ``approved_phrase``;
    * linkedin/website URLs -> ``portfolio_link``.

    All items start unapproved. Nothing is generated: text is copied
    verbatim from the profile with its source reference. Returns the
    created items.
    """
    created: list[dict[str, Any]] = []

    def _add(kind: str, text: str, source: str) -> None:
        try:
            created.append(add_item(kind, text, source, library_dir))
        except ValueError as exc:
            log.warning("skipping evidence item: %s", exc)

    for i, exp in enumerate(profile.get("experience", []) or []):
        if not isinstance(exp, dict):
            continue
        for j, bullet in enumerate(exp.get("bullets", []) or []):
            bullet = str(bullet or "").strip()
            if not bullet:
                continue
            source = f"experience[{i}].bullets[{j}]"
            _add("achievement", bullet, source)
            if _NUMBER_RE.search(bullet):
                _add("metric", bullet, source)
    for i, skill in enumerate(profile.get("skills", []) or []):
        name = skill.get("name") if isinstance(skill, dict) else skill
        name = str(name or "").strip()
        if name:
            _add("approved_phrase", name, f"skills[{i}]")
    for key, label in (("linkedin_url", "LinkedIn"), ("website", "website")):
        url = str(profile.get(key) or "").strip()
        if url:
            _add("portfolio_link", f"{label}: {url}", key)
    return created


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9+#]+", str(text or "").lower()))


def find_for_requirement(
    requirement_text: str,
    library_dir: Path | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Rank approved items against a requirement by token overlap.

    Only ``approved=True`` items are ever returned — drafts can never
    back a tailored statement. Returns at most ``limit`` items, best
    first; empty when nothing relevant is approved yet.
    """
    need = _tokens(requirement_text)
    if not need:
        return []
    scored = []
    for item in list_items(approved_only=True, library_dir=library_dir):
        have = _tokens(item.get("text", ""))
        overlap = need & have
        if overlap:
            scored.append((len(overlap), item))
    scored.sort(key=lambda pair: -pair[0])
    return [item for _, item in scored[:limit]]
