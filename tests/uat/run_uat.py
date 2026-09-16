#!/usr/bin/env python3
"""Run Veto's automated UAT acceptance journeys and render Paul's report.

Usage (from the product repo root)::

    .venv/bin/python tests/uat/run_uat.py
    .venv/bin/python tests/uat/run_uat.py --report uat-report.md
    .venv/bin/python tests/uat/run_uat.py --only i04

Runs the seven shipped-initiative journeys (04, 05, 06, 07, 10, 11, 12)
and produces a plain-English report with epic -> check -> pass/fail
traceability. Paul reviews this report and signs off; the automation does
the trying, he does the accepting.

Exit code: 0 if every journey check passed (skips allowed), 1 otherwise.
"""

from __future__ import annotations

import argparse
import datetime
import importlib
import subprocess
import sys
import time
import traceback
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

JOURNEYS: list[tuple[str, str, str]] = [
    ("04", "Fit decoder & career graph", "tests.uat.test_uat_i04"),
    ("05", "Application Studio", "tests.uat.test_uat_i05"),
    ("06", "Interview & skills lab", "tests.uat.test_uat_i06"),
    ("07", "Mentor matching & warm paths", "tests.uat.test_uat_i07"),
    ("10", "Packaging, backup & secure sync", "tests.uat.test_uat_i10"),
    ("11", "Governed extension platform", "tests.uat.test_uat_i11"),
    ("12", "Public growth & education", "tests.uat.test_uat_i12"),
]


def _git_head() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(REPO),
            capture_output=True, text=True, timeout=15)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


class _Listener(unittest.TestResult):
    """Collects per-test outcomes plus evidence for the report."""

    def __init__(self):
        super().__init__()
        self.records: list[dict] = []
        self._started: dict[str, float] = {}

    def startTest(self, test):
        self._started[test.id()] = time.time()
        super().startTest(test)

    @staticmethod
    def _doc_summary(test) -> str:
        """First paragraph of the test docstring, joined to one line."""
        raw = (test._testMethodDoc or "").strip()
        if not raw:
            return ""
        para = []
        for line in raw.splitlines():
            if not line.strip():
                break
            para.append(line.strip())
        return " ".join(para)

    def _finish(self, test, status, evidence=""):
        elapsed = time.time() - self._started.pop(test.id(), time.time())
        self.records.append({
            "id": test.id(),
            "method": test._testMethodName,
            "doc": self._doc_summary(test),
            "status": status,
            "evidence": evidence,
            "elapsed": elapsed,
        })

    def addSuccess(self, test):
        super().addSuccess(test)
        self._finish(test, "PASS")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._finish(test, "SKIP", f"Skipped: {reason}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._finish(test, "FAIL", _format_err(err))

    def addError(self, test, err):
        super().addError(test, err)
        self._finish(test, "ERROR", _format_err(err))


def _format_err(err) -> str:
    exc_type, exc_value, tb = err
    msg = "".join(traceback.format_exception_only(exc_type, exc_value)).strip()
    frames = traceback.extract_tb(tb)
    interesting = [f for f in frames
                   if "tests/uat" in (f.filename or "")]
    loc = (f'  at {interesting[-1].filename}:{interesting[-1].lineno}'
           if interesting else "")
    return f"{msg}\n{loc}".strip()


def _norm_only(only: str | None) -> str | None:
    """Normalize --only to a bare initiative number; reject unknown ones."""
    if not only:
        return None
    norm = only.strip().lower()
    if norm.startswith("i"):
        norm = norm[1:]
    valid = {num for num, _, _ in JOURNEYS}
    if norm not in valid:
        print(
            f"error: --only {only!r}: no such initiative; "
            f"choose from {', '.join('i' + n for n, _, _ in JOURNEYS)}",
            file=sys.stderr)
        raise SystemExit(2)
    return norm


def _module_epic_map(module) -> dict:
    """Module-level EPIC_MAP merged with each journey class's own map.

    Journeys declare EPIC_MAP as a class attribute (validated at class
    definition by the harness); some also re-export it at module level.
    """
    merged = dict(getattr(module, "EPIC_MAP", {}) or {})
    for name in dir(module):
        obj = getattr(module, name)
        if (isinstance(obj, type)
                and issubclass(obj, unittest.TestCase)
                and obj.__module__ == module.__name__):
            merged.update(getattr(obj, "EPIC_MAP", {}) or {})
    return merged


def _validate_epic_map(module) -> list[str]:
    """Every test method must map to exactly one epic; return problems."""
    epic_map = _module_epic_map(module)
    problems: list[str] = []
    for name in dir(module):
        obj = getattr(module, name)
        if (isinstance(obj, type)
                and issubclass(obj, unittest.TestCase)
                and obj.__module__ == module.__name__):
            methods = {m for m in dir(obj)
                       if m.startswith(unittest.TestLoader.testMethodPrefix)
                       and callable(getattr(obj, m))}
            missing = sorted(methods - set(epic_map))
            extra = sorted(set(epic_map) - methods)
            if missing:
                problems.append(
                    f"{name}: test methods without EPIC_MAP entries: "
                    f"{missing}")
            if extra:
                problems.append(
                    f"{name}: EPIC_MAP entries with no test method: {extra}")
    if not epic_map:
        problems.append("module defines no EPIC_MAP at all")
    return problems


def run_journeys(only: str | None = None):
    started = datetime.datetime.now().astimezone()
    all_records: list[dict] = []
    epic_maps: dict[str, dict] = {}
    for num, title, module_name in JOURNEYS:
        if only and only != num:
            continue
        module = importlib.import_module(module_name)
        epic_maps[num] = _module_epic_map(module)
        for problem in _validate_epic_map(module):
            # Loud in the report: a journey whose checks cannot be traced
            # to epics fails the gate instead of silently passing.
            all_records.append({
                "initiative": num,
                "initiative_title": title,
                "id": f"{module_name}.EPIC_MAP",
                "method": "EPIC_MAP",
                "doc": "Epic traceability is complete and honest",
                "status": "ERROR",
                "evidence": f"Traceability defect: {problem}",
                "elapsed_s": 0.0,
            })
        suite = unittest.TestLoader().loadTestsFromModule(module)
        listener = _Listener()
        suite.run(listener)
        for rec in listener.records:
            rec["initiative"] = num
            rec["initiative_title"] = title
            rec["elapsed_s"] = round(rec.pop("elapsed"), 1)
            all_records.append(rec)
    return started, all_records, epic_maps


def _epic_info(epic_maps, num, method):
    info = epic_maps.get(num, {}).get(method)
    if info:
        return info  # (epic_id, epic_title, acceptance_source)
    return ("?", "unmapped", "no EPIC_MAP entry")


def render_markdown(started, records, epic_maps) -> str:
    git_head = _git_head()
    total = len(records)
    passed = sum(1 for r in records if r["status"] == "PASS")
    failed = [r for r in records if r["status"] in ("FAIL", "ERROR")]
    skipped = [r for r in records if r["status"] == "SKIP"]

    lines = [
        "# Veto UAT acceptance report",
        "",
        f"Ran {started.strftime('%Y-%m-%d %H:%M %Z')} — "
        f"repo HEAD `{git_head}`, `{sys.executable}`.",
        "",
        f"**Result: {passed}/{total} checks passed**, "
        f"{len(failed)} failed, {len(skipped)} skipped.",
        "",
        "Each check below is one automated acceptance journey step, traced "
        "to its roadmap epic. The automation does the trying; "
        "Paul does the accepting.",
        "",
        "## Traceability: epic -> check -> result",
        "",
        "| Initiative | Epic | Check (what was verified) | Result | Time |",
        "|---|---|---|---|---|",
    ]
    for r in records:
        epic_id, epic_title, _src = _epic_info(
            epic_maps, r["initiative"], r["method"])
        check = r["doc"] or r["method"]
        mark = {"PASS": "PASS", "FAIL": "FAIL",
                "ERROR": "ERROR", "SKIP": "SKIP"}[r["status"]]
        lines.append(
            f"| {r['initiative']} | {epic_id}: {epic_title} | {check} "
            f"| **{mark}** | {r.get('elapsed_s', '?')}s |")
    lines += [""]

    if failed:
        lines += ["## Failures (with evidence)", ""]
        for r in failed:
            epic_id, epic_title, src = _epic_info(
                epic_maps, r["initiative"], r["method"])
            lines += [
                f"### {r['initiative']} {r['initiative_title']} — "
                f"{epic_id}: {epic_title}",
                "",
                f"Check: {r['doc'] or r['method']}",
                f"Acceptance source: {src}",
                "",
                "```",
                r["evidence"][:3000],
                "```",
                "",
            ]

    if skipped:
        lines += ["## Skipped checks", ""]
        for r in skipped:
            epic_id, epic_title, _src = _epic_info(
                epic_maps, r["initiative"], r["method"])
            lines.append(
                f"- {r['initiative']} / {epic_id} {epic_title}: "
                f"{r['doc'] or r['method']} — {r['evidence']}")
        lines += [""]

    lines += [
        "## Acceptance-criteria gap",
        "",
        "The repo defines per-initiative **epics** (annual roadmap) but no "
        "per-story acceptance criteria; only Initiative 05 has job stories "
        "(unvalidated, no criteria). The checks above trace to epic text, "
        "Proof-of-value statements, quarterly exit gates, and initiative "
        "README hard rules — no story-level criteria were invented.",
        "",
        "## Sign-off",
        "",
        "Paul personally accepts or rejects each initiative before it "
        "counts as shipped. One line per initiative:",
        "",
    ]
    seen = []
    for r in records:
        if r["initiative"] not in seen:
            seen.append(r["initiative"])
    for num in seen:
        title = next(x["initiative_title"] for x in records
                     if x["initiative"] == num)
        lines.append(f"- [ ] Initiative {num} ({title}) — "
                     "accepted / rejected: ___")
    lines.append("")
    return "\n".join(lines)


def render_console(records) -> str:
    total = len(records)
    passed = sum(1 for r in records if r["status"] == "PASS")
    failed = sum(1 for r in records if r["status"] in ("FAIL", "ERROR"))
    skipped = sum(1 for r in records if r["status"] == "SKIP")
    lines = [f"UAT: {passed}/{total} passed, {failed} failed, "
             f"{skipped} skipped"]
    for r in records:
        if r["status"] != "PASS":
            lines.append(f"  [{r['status']}] i{r['initiative']} "
                         f"{r['method']}: {r['evidence'][:160]}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", default=None,
                    help="Write the markdown report to this path.")
    ap.add_argument("--only", default=None,
                    help="Run one initiative only (e.g. --only i04).")
    args = ap.parse_args()

    try:
        only = _norm_only(args.only)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    started, records, epic_maps = run_journeys(only)
    if not records:
        # Never present an empty run as a green report.
        print("error: no UAT journeys ran; refusing to report 0/0 as a "
              "pass", file=sys.stderr)
        return 1
    md = render_markdown(started, records, epic_maps)
    print(render_console(records))

    if args.report:
        out = Path(args.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(md, encoding="utf-8")
        print(f"Report written to {out}")

    failed = sum(1 for r in records if r["status"] in ("FAIL", "ERROR"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
