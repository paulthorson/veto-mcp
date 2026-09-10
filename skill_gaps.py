"""Skill-gap planner: find what your target jobs want that you don't have yet.

Workflow:
1. ``analyze_gaps(profile, jobs)`` — diff every target job's required
   keywords (via ``tailor.extract_job_keywords``) against the profile's
   skills; aggregate into a ranked gap list scored by
   frequency x seniority-weight.
2. ``gap_plan()`` — map each gap to the closest ``ai_proficiency`` track
   lesson (defensive import; degrades to a concrete practice-project
   idea when the module or a matching lesson is unavailable).
3. ``mark_gap_progress(skill, status)`` — track {planned, practicing,
   closed}. Closing is a self-attestation and requires a one-line
   evidence note; gaps are never auto-closed.

Honesty contract: a closed gap means *you said* you did the work and
wrote down what it was — this module never verifies it and never
presents practice as a credential or certification.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

from tailor import extract_job_keywords
from filters import detect_seniority

BASE_DIR = Path(__file__).resolve().parent
STORE_PATH = BASE_DIR / "skill_gaps.json"
PROFILE_PATH = BASE_DIR / "profiles" / "profile.json"

_VALID_STATUSES = ("planned", "practicing", "closed")

# Seniority weight: a gap that senior/staff postings demand is more urgent
# than one that only appears in entry-level postings.
_SENIORITY_WEIGHT = {
    "entry": 0.8,
    "mid": 1.0,
    "senior": 1.25,
    "staff": 1.4,
    "principal": 1.5,
}

# Concrete practice-project ideas for common non-AI skills. These are
# *suggestions for reps*, not credentials — building the project is the
# evidence, and only the user can attest to that.
NON_AI_PROJECTS: dict[str, str] = {
    "kubernetes": (
        "Deploy a small web app to a local k3s/kind cluster: write the "
        "Deployment + Service YAML yourself, expose it, then break it and "
        "fix it. Write up the YAML decisions."
    ),
    "docker": (
        "Containerize one of your own scripts: multi-stage Dockerfile, "
        "non-root user, pinned base image. Document the image size before "
        "and after."
    ),
    "terraform": (
        "Write Terraform that provisions a throwaway cloud sandbox (VPC + "
        "one VM), apply, then destroy. Keep the plan output as your notes."
    ),
    "typescript": (
        "Convert a small JavaScript project to strict TypeScript: fix every "
        "'any', add interfaces for the data shapes, get tsc clean."
    ),
    "graphql": (
        "Build a tiny GraphQL API over data you already have (a JSON file "
        "counts): schema, two queries, one mutation, one resolver with a "
        "dataloader-style batch."
    ),
    "sql": (
        "Take a public dataset and answer 5 business questions with SQL "
        "only: joins, window functions, one CTE. Save the queries."
    ),
    "figma": (
        "Redesign one screen of an app you use: wireframe, then hi-fi "
        "mock, then a clickable prototype. Write 3 sentences on each "
        "design decision."
    ),
    "excel": (
        "Model something real in a spreadsheet: pivot tables, INDEX/MATCH "
        "or XLOOKUP, one dashboard chart. No manual copy-paste steps."
    ),
    "salesforce": (
        "In a free Trailhead playground: build a custom object with "
        "validation rules, one Flow, and one report. Screenshot the Flow."
    ),
    "tableau": (
        "Build a dashboard from a public dataset: 3 chart types, one "
        "parameter-driven filter, published to Tableau Public."
    ),
    "go": (
        "Write a small CLI in Go with goroutines doing real concurrent "
        "work (e.g. parallel URL fetcher): channels, WaitGroup, context "
        "cancellation, tests."
    ),
    "rust": (
        "Rewrite a Python script you own in Rust: fight the borrow "
        "checker, add error handling with Result, ship a binary."
    ),
}

_ai_proficiency: Any = None
_ai_proficiency_tried = False


def _ai_module() -> Any | None:
    """Import ai_proficiency defensively; None when unavailable."""
    global _ai_proficiency, _ai_proficiency_tried
    if not _ai_proficiency_tried:
        _ai_proficiency_tried = True
        try:
            import ai_proficiency as _mod

            _ai_proficiency = _mod
        except Exception:
            _ai_proficiency = None
    return _ai_proficiency


def _lesson_index() -> list[dict[str, Any]]:
    """Flatten every track's lessons into searchable entries."""
    mod = _ai_module()
    if mod is None:
        return []
    tracks = getattr(mod, "TRACKS", {}) or {}
    index: list[dict[str, Any]] = []
    for track, tdata in tracks.items():
        for lesson in tdata.get("lessons", []) or []:
            index.append(
                {
                    "track": track,
                    "lesson_id": lesson.get("id", ""),
                    "title": lesson.get("title", ""),
                    "skill": lesson.get("skill", ""),
                    "est_minutes": lesson.get("est_minutes"),
                }
            )
    return index


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2}


def _best_lesson(skill: str) -> dict[str, Any] | None:
    """Closest ai_proficiency lesson for a gap skill, or None.

    Token-overlap scoring between the skill and each lesson's skill +
    title. Requires at least one shared meaningful token so unrelated
    lessons are never suggested.
    """
    skill_toks = _tokens(skill)
    if not skill_toks:
        return None
    best: dict[str, Any] | None = None
    best_score = 0
    for entry in _lesson_index():
        entry_toks = _tokens(entry["skill"] + " " + entry["title"])
        overlap = skill_toks & entry_toks
        # Substring hits count too ("rag" inside "RAG pipelines").
        sub_hits = sum(
            1
            for st in skill_toks
            for et in entry_toks
            if st != et and (st in et or et in st)
        )
        score = len(overlap) * 2 + sub_hits
        if score > best_score:
            best_score = score
            best = entry
    return best if best_score > 0 else None


def _load_store() -> dict[str, Any]:
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_store(store: dict[str, Any]) -> None:
    tmp = STORE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STORE_PATH)


def _job_weight(job: dict[str, Any]) -> float:
    level = detect_seniority(str(job.get("title", "") or ""))
    return _SENIORITY_WEIGHT.get(level or "mid", 1.0)


def analyze_gaps(
    profile: dict[str, Any] | None = None,
    jobs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Diff target jobs' required keywords against the profile's skills.

    Args:
        profile: candidate profile (defaults to the saved onboarding
            profile). Only the profile's own skill list is used.
        jobs: target job dicts (title/description/requirements/snippet).

    Returns:
        {"gaps": [...], "markdown": ...} — each gap has the skill, how
        many target jobs want it, the frequency x seniority weighted
        score, and up to 3 example job titles. Existing progress statuses
        in skill_gaps.json are preserved across re-runs.
    """
    prof = dict(profile) if profile is not None else _load_profile()
    jobs = list(jobs) if jobs else []

    agg: dict[str, dict[str, Any]] = {}
    for job in jobs:
        if not isinstance(job, dict):
            continue
        weight = _job_weight(job)
        title = str(job.get("title", "") or "Untitled role")
        try:
            missing = extract_job_keywords(job, prof).get("missing", [])
        except Exception:
            continue
        for skill in missing:
            key = skill.lower().strip()
            entry = agg.setdefault(
                key, {"skill": skill, "job_count": 0, "weighted": 0.0, "example_jobs": []}
            )
            entry["job_count"] += 1
            entry["weighted"] += weight
            if title not in entry["example_jobs"] and len(entry["example_jobs"]) < 3:
                entry["example_jobs"].append(title)

    ranked = sorted(
        agg.values(),
        key=lambda e: (-e["weighted"], -e["job_count"], e["skill"].lower()),
    )
    gaps = [
        {
            "skill": e["skill"],
            "job_count": e["job_count"],
            "weighted_score": round(e["weighted"], 2),
            "example_jobs": e["example_jobs"],
        }
        for e in ranked
    ]

    # Persist only when the gap set actually changed, so a no-op analysis
    # (e.g. triggered by --help or a bare import) never creates or
    # rewrites the state file. Statuses the user already recorded are
    # preserved across re-runs.
    store = _load_store()
    old = store.get("gaps", {}) if isinstance(store.get("gaps"), dict) else {}
    now = int(time.time())
    merged: dict[str, Any] = {}
    for gap in gaps:
        key = gap["skill"].lower()
        prev = old.get(key, {}) if isinstance(old.get(key), dict) else {}
        merged[key] = {
            **gap,
            "status": prev.get("status", "planned"),
            "evidence": prev.get("evidence"),
            "updated_at": prev.get("updated_at", now),
        }
    if merged != old:
        store["gaps"] = merged
        store["analyzed_at"] = now
        store["jobs_analyzed"] = len(jobs)
        _save_store(store)

    lines = ["# Skill gaps", ""]
    if not gaps:
        lines.append("No gaps found — your skills cover every target job's keywords.")
    else:
        for i, gap in enumerate(gaps, 1):
            lines.append(
                f"{i}. **{gap['skill']}** — wanted by {gap['job_count']} job(s) "
                f"(score {gap['weighted_score']}); e.g. "
                + ", ".join(gap["example_jobs"])
            )
    return {"gaps": gaps, "jobs_analyzed": len(jobs), "markdown": "\n".join(lines)}


def gap_plan() -> dict[str, Any]:
    """Map each stored gap to a learning step.

    Prefers the closest ``ai_proficiency`` track lesson; falls back to a
    concrete practice-project idea (from NON_AI_PROJECTS, else a generic
    project template). Degrades gracefully when ai_proficiency is
    unavailable — the plan never fails, it just suggests projects.
    """
    store = _load_store()
    gaps = store.get("gaps", {}) if isinstance(store.get("gaps"), dict) else {}
    if not gaps:
        return {
            "plan": [],
            "markdown": "No gaps analyzed yet — run `skill-gaps analyze` first.",
        }

    plan: list[dict[str, Any]] = []
    for key in sorted(gaps, key=lambda k: -gaps[k].get("weighted_score", 0)):
        gap = gaps[key]
        skill = gap["skill"]
        lesson = _best_lesson(skill)
        if lesson is not None:
            step = {
                "type": "ai_proficiency_lesson",
                "skill": skill,
                "track": lesson["track"],
                "lesson_id": lesson["lesson_id"],
                "title": lesson["title"],
                "est_minutes": lesson.get("est_minutes"),
                "why": f"Closest lesson to '{skill}' in the {lesson['track']} track.",
            }
        elif key in NON_AI_PROJECTS:
            step = {
                "type": "practice_project",
                "skill": skill,
                "project": NON_AI_PROJECTS[key],
                "why": f"Hands-on project idea for '{skill}'.",
            }
        else:
            step = {
                "type": "practice_project",
                "skill": skill,
                "project": (
                    f"Build a small portfolio project that uses {skill} end "
                    "to end, document what you built and the decisions you "
                    "made, and link it from your resume. The write-up is the "
                    "evidence."
                ),
                "why": f"No built-in lesson or project idea for '{skill}' — generic project.",
            }
        step["status"] = gap.get("status", "planned")
        plan.append(step)

    store["plan"] = plan
    store["planned_at"] = int(time.time())
    _save_store(store)

    lines = ["# Gap-closing plan", ""]
    for i, step in enumerate(plan, 1):
        if step["type"] == "ai_proficiency_lesson":
            lines.append(
                f"{i}. **{step['skill']}** [{step['status']}] → lesson "
                f"`{step['lesson_id']}` \"{step['title']}\" "
                f"({step['track']} track, ~{step.get('est_minutes') or '?'} min)"
            )
        else:
            lines.append(
                f"{i}. **{step['skill']}** [{step['status']}] → project: {step['project']}"
            )
    return {"plan": plan, "markdown": "\n".join(lines)}


def mark_gap_progress(
    skill: str, status: str, evidence: str | None = None
) -> dict[str, Any]:
    """Record progress on a gap skill.

    Args:
        skill: the gap skill (case-insensitive; must come from a prior
            ``analyze_gaps`` run).
        status: one of planned | practicing | closed.
        evidence: required when closing — a one-line note of what you
            built or did (e.g. "shipped k3s homelab deploy, notes in
            ~/notes/k3s.md").

    Closing is a self-attestation: the module records your claim, never
    verifies it, and a closed gap is practice logged — never a
    credential or certification.
    """
    status = (status or "").strip().lower()
    if status not in _VALID_STATUSES:
        raise ValueError(
            f"Unknown status {status!r}; use one of {', '.join(_VALID_STATUSES)}"
        )
    if status == "closed" and not (evidence or "").strip():
        raise ValueError(
            "Closing a gap requires a one-line evidence note — "
            "what did you build or do? (e.g. mark_gap_progress("
            "'kubernetes', 'closed', evidence='deployed k3s homelab'))"
        )

    store = _load_store()
    gaps = store.get("gaps", {}) if isinstance(store.get("gaps"), dict) else {}
    key = (skill or "").strip().lower()
    if key not in gaps:
        known = ", ".join(sorted(g["skill"] for g in gaps.values())) or "none"
        raise ValueError(
            f"Unknown gap skill {skill!r}. Known gaps: {known}. "
            "Run `skill-gaps analyze` first."
        )
    gaps[key]["status"] = status
    gaps[key]["evidence"] = (evidence or "").strip() or None
    gaps[key]["updated_at"] = int(time.time())
    _save_store(store)
    return {"skill": gaps[key]["skill"], **gaps[key]}


def _load_profile() -> dict[str, Any]:
    try:
        data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _print_result(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(result.get("markdown") or json.dumps(result, indent=2))


def cmd_skill_gaps(args: Any) -> int:
    """CLI handler for `skill-gaps`."""
    action = (getattr(args, "action", "") or "").strip().lower()
    as_json = getattr(args, "json", False)
    if action == "analyze":
        jobs_path = getattr(args, "jobs", "") or ""
        if not jobs_path:
            raise SystemExit("analyze requires --jobs PATH to a JSON list of job dicts")
        jobs = json.loads(Path(jobs_path).read_text(encoding="utf-8"))
        profile_path = getattr(args, "profile", "") or str(PROFILE_PATH)
        try:
            profile = json.loads(Path(profile_path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            profile = {}
        _print_result(analyze_gaps(profile, jobs), as_json)
    elif action == "plan":
        _print_result(gap_plan(), as_json)
    elif action == "mark":
        _print_result(
            mark_gap_progress(
                getattr(args, "skill", ""),
                getattr(args, "status", ""),
                getattr(args, "evidence", None),
            ),
            as_json,
        )
    else:
        raise SystemExit(f"Unknown action {action!r}; use analyze|plan|mark")
    return 0


def register_tools(mcp: Any) -> None:
    """Register the skill-gap MCP tools on an MCP server instance."""
    _impl_analyze = globals()["analyze_gaps"]
    _impl_plan = globals()["gap_plan"]
    _impl_mark = globals()["mark_gap_progress"]

    @mcp.tool()
    def analyze_skill_gaps(profile: dict, jobs: list) -> dict:
        """Diff target jobs' required keywords against profile skills.

        Args:
            profile: candidate profile dict (with a "skills" list).
            jobs: list of job dicts (title/description/requirements).

        Returns:
            Ranked gap list scored by frequency x seniority-weight, each
            with skill, job_count, weighted_score, example job titles.
        """
        return _impl_analyze(profile, jobs)

    @mcp.tool()
    def skill_gap_plan() -> dict:
        """Map each analyzed gap to a learning step.

        Returns:
            Plan entries pointing at the closest ai_proficiency lesson
            or a concrete practice-project idea, with current status.
        """
        return _impl_plan()

    @mcp.tool()
    def mark_gap_progress(skill: str, status: str, evidence: str = "") -> dict:
        """Record progress on a gap skill.

        Args:
            skill: gap skill from analyze_skill_gaps.
            status: planned | practicing | closed.
            evidence: one-line note of what you built/did — required
                when closing. Closing is a self-attestation, never a
                verified credential.
        """
        return _impl_mark(skill, status, evidence)


def register_cli(subparsers: Any) -> dict[str, Any]:
    """Add `skill-gaps` to an argparse subparsers.

    Returns a {command: handler} mapping the caller can merge into its
    own dispatch table (cli.py-style).
    """
    p = subparsers.add_parser("skill-gaps", help="Analyze and close skill gaps.")
    p.add_argument("action", help="One of: analyze, plan, mark.")
    p.add_argument("--jobs", default="", help="analyze: path to JSON list of job dicts.")
    p.add_argument(
        "--profile", default="", help="analyze: path to profile JSON (default: saved profile)."
    )
    p.add_argument("--skill", default="", help="mark: the gap skill.")
    p.add_argument("--status", default="", help="mark: planned | practicing | closed.")
    p.add_argument(
        "--evidence", default=None, help="mark: one-line evidence note (required to close)."
    )
    p.add_argument("--json", action="store_true", help="Machine-readable JSON output.")
    return {"skill-gaps": cmd_skill_gaps}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="skill-gaps")
    sub = parser.add_subparsers()
    handlers = register_cli(sub)
    args = parser.parse_args(argv)
    handler = handlers.get("skill-gaps")
    return handler(args) if handler else 2


if __name__ == "__main__":
    raise SystemExit(main())
