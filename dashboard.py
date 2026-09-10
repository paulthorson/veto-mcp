"""Interactive terminal dashboard for the job-apply repo (stdlib only).

Launches a grouped menu (FIND / TAILOR / TRAIN / WIN / GOVERN / UTILITIES)
that wires every one of the 19 feature modules through short guided
workflows. The dashboard only ever reads state or saves local previews:
it NEVER sends email, submits applications, or transmits data — those
steps print a preview and point at the module's own confirm flow.

Entry point: ``cmd_dashboard(args)`` — takes an argparse namespace and
ignores it (the coordinator wires the subparser).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

import dashboard_data  # noqa: E402

import match  # noqa: E402
import radar  # noqa: E402
import tailor  # noqa: E402
import followup  # noqa: E402
import referrals  # noqa: E402
import mock_interview  # noqa: E402
import soft_skills  # noqa: E402
import ai_proficiency  # noqa: E402
import mentors  # noqa: E402
import contribute  # noqa: E402
import offer_compare  # noqa: E402
import skill_gaps  # noqa: E402
import cover_letters  # noqa: E402
import linkedin_optimizer  # noqa: E402
import jd_decoder  # noqa: E402
import network_crm  # noqa: E402
import rejection_autopsy  # noqa: E402
import streaks  # noqa: E402
import crew  # noqa: E402
import doctor  # noqa: E402


class _Quit(Exception):
    """Raised on Ctrl-C / EOF so the dashboard exits cleanly."""


# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------


def _read(prompt_text: str) -> str:
    """input() that converts Ctrl-C / EOF into a clean _Quit."""
    try:
        return input(prompt_text)
    except (EOFError, KeyboardInterrupt):
        raise _Quit()


def ask(prompt: str, default: str = "", required: bool = False) -> str:
    """Prompt with the default shown in [brackets]; re-prompts when required."""
    label = f"{prompt} [{default}]: " if default else f"{prompt}: "
    while True:
        raw = _read(label).strip()
        if raw:
            return raw
        if default or not required:
            return default
        print("  Please enter a value (Ctrl-C cancels).")


def ask_int(prompt: str, default: int, lo: int | None = None,
            hi: int | None = None) -> int:
    """Prompt for an integer in [lo, hi]; re-prompts on bad input."""
    while True:
        raw = ask(prompt, str(default)).strip()
        try:
            value = int(raw)
        except ValueError:
            print(f"  Enter a whole number (default {default}).")
            continue
        if lo is not None and value < lo:
            print(f"  Must be at least {lo}.")
            continue
        if hi is not None and value > hi:
            print(f"  Must be at most {hi}.")
            continue
        return value


def ask_float(prompt: str, default: float) -> float:
    """Prompt for a number; re-prompts on bad input."""
    while True:
        raw = ask(prompt, str(default)).strip()
        try:
            return float(raw)
        except ValueError:
            print(f"  Enter a number (default {default}).")


def ask_choice(prompt: str, choices: list[str], default: str | None = None) -> str:
    """Numbered choice list; returns the chosen value."""
    indexed = {str(i + 1): c for i, c in enumerate(choices)}
    default_idx = None
    if default in choices:
        default_idx = str(choices.index(default) + 1)
    for i, c in enumerate(choices, 1):
        mark = " (default)" if str(i) == default_idx else ""
        print(f"  {i}) {c}{mark}")
    while True:
        raw = _read(f"{prompt} [1-{len(choices)}"
                    f"{', default ' + default_idx if default_idx else ''}]: ").strip()
        if not raw and default_idx:
            return indexed[default_idx]
        if raw in indexed:
            return indexed[raw]
        print(f"  Pick a number 1-{len(choices)}.")


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    """Yes/no prompt; returns True for yes."""
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        raw = _read(f"{prompt} {hint}: ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  Answer y or n.")


def read_text_or_file(prompt: str) -> str:
    """Accept a file path or pasted text (end paste with an empty line)."""
    raw = _read(f"{prompt} (file path, or Enter to paste): ").strip()
    if raw:
        path = Path(raw).expanduser()
        if not path.is_file():
            print(f"  No file at {path} — treating it as pasted text.")
            return raw
        return path.read_text(encoding="utf-8")
    print("  Paste text, then an empty line to finish:")
    lines: list[str] = []
    while True:
        line = _read("")
        if not line.strip():
            break
        lines.append(line)
    return "\n".join(lines)


def load_profile() -> dict:
    """Load the candidate profile JSON (validated path, defaults offered)."""
    path = Path(ask("Profile JSON", str(REPO_DIR / "profiles" / "profile.json")))
    if not path.is_file():
        print(f"  No profile at {str(path)[:40]}. Continuing without one.")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        print(f"  {path} is not valid JSON — continuing without one.")
        return {}
    return data if isinstance(data, dict) else {}


def _job_details() -> tuple[dict, dict]:
    """Prompt for profile + job triple shared by the TAILOR workflows."""
    profile = load_profile()
    title = ask("Job title", "")
    company = ask("Company", "")
    jd = read_text_or_file("Job description")
    return profile, {"title": title, "company": company, "description": jd}


def _divider(label: str = "") -> None:
    print("\n" + ("— " + label + " ").ljust(60, "—") if label else "")


# ---------------------------------------------------------------------------
# KPI header
# ---------------------------------------------------------------------------


def print_kpis() -> None:
    """Print the KPI header row from dashboard_data.compute_kpis()."""
    k = dashboard_data.compute_kpis(REPO_DIR)
    avg = f"{k['avg_fit']:.0f}" if k["avg_fit"] is not None else "—"
    print(
        f"Applications: {k['applications']}  |  Avg fit: {avg}  |  "
        f"Day streak: {k['streak_days']}  |  Interviews: {k['interviews']}  |  "
        f"Follow-ups due: {k['followups_due']}  |  Offers: {k['offers']}"
    )


# ---------------------------------------------------------------------------
# FIND workflows
# ---------------------------------------------------------------------------


def wf_match() -> None:
    """Score one job posting against the profile (match.score_job)."""
    _divider("SCORE A JOB")
    profile, job = _job_details()
    if not job["description"] and not job["title"]:
        print("  Nothing to score — give a title or description next time.")
        return
    res = match.score_job(job, profile or {}, None)
    print(f"\n  Score: {res['score']}/100" + ("  ⚠ VETOED" if res.get("veto") else ""))
    if res.get("veto_reason"):
        print(f"  Veto reason: {res['veto_reason']}")
    if res.get("matched"):
        print("  Matched: " + ", ".join(res["matched"][:8]))
    if res.get("missing"):
        print("  Missing: " + ", ".join(res["missing"][:8]))
    for reason in (res.get("reasons") or [])[:6]:
        print(f"  • {reason}")


def wf_jd_decoder() -> None:
    """Decode a job description: red flags, green flags, verdict."""
    _divider("DECODE A JOB DESCRIPTION")
    text = read_text_or_file("Job description")
    if not text.strip():
        print("  Empty input — nothing to decode.")
        return
    v = jd_decoder.jd_verdict(text)
    print(f"\n  Verdict: {v.get('verdict', '?')} ({v.get('score', '?')}/100)")
    reasons = v.get("reasons") or []
    good = [r for r in reasons if r.get("impact", 0) > 0]
    bad = [r for r in reasons if r.get("impact", 0) < 0]
    signals = v.get("signals") or {}
    greens = signals.get("green_flags") or []
    overwork = signals.get("overwork") or []
    if greens:
        print(f"\n  Green flags ({len(greens)}):")
        for f in greens[:5]:
            print(f"  ✓ {f.get('label', f.get('type', '?'))}: "
                  f"{str(f.get('quote', ''))[:90]}")
    if overwork:
        print(f"\n  Overwork flags ({len(overwork)}):")
        for f in overwork[:5]:
            label = f.get("phrase", f.get("label", f.get("type", "?")))
            print(f"  ✕ {label}: {str(f.get('quote', ''))[:90]}")
    if bad:
        print(f"\n  Concerns ({len(bad)}):")
        for r in bad[:5]:
            print(f"  ✕ {r.get('reason')}: {str(r.get('quote', ''))[:80]}")
    if good:
        print(f"\n  Positives ({len(good)}):")
        for r in good[:5]:
            print(f"  ✓ {r.get('reason')}")
    if not (greens or overwork or reasons):
        print("  No notable signals either way.")


def wf_radar() -> None:
    """Build a radar-chart SVG from component scores."""
    _divider("FIT RADAR CHART")
    raw = ask("Component scores (name=score, comma-separated)",
              "skills=75, seniority=60, salary=50, location=80, recency=40")
    comps: dict[str, float] = {}
    for part in raw.split(","):
        if "=" not in part:
            continue
        name, _, val = part.partition("=")
        try:
            comps[name.strip()] = max(0.0, min(100.0, float(val.strip())))
        except ValueError:
            print(f"  Skipping {part.strip()!r} (not a number).")
    if len(comps) < 3:
        print("  Need at least 3 valid components — try again.")
        return
    title = ask("Chart title", "My fit")
    score = round(sum(comps.values()) / len(comps))
    svg = radar.radar_svg({"components": comps, "score": score, "veto": False},
                          title=title)
    out = REPO_DIR / "radar_chart.svg"
    out.write_text(svg, encoding="utf-8")
    print(f"\n  Chart saved to {out}")


# ---------------------------------------------------------------------------
# TAILOR workflows
# ---------------------------------------------------------------------------


def wf_tailor() -> None:
    """Tailor resume bullets to a JD; optionally save an approved variant."""
    _divider("TAILOR RESUME")
    profile, job = _job_details()
    res = tailor.tailor_resume(profile, job)
    matched = res.get("matched_skills") or []
    missing = res.get("missing_skills") or []
    print(f"\n  Matched skills ({len(matched)}): " + (", ".join(matched[:10]) or "—"))
    print(f"  Missing skills ({len(missing)}): " + (", ".join(missing[:10]) or "—"))
    lines = (res.get("resume_md") or "").splitlines()
    print("\n  Tailored resume (first lines):")
    for line in lines[:18]:
        print("  " + line)
    if len(lines) > 18:
        print(f"  … ({len(lines) - 18} more lines)")
    if ask_yes_no("Save this as an approved local variant?"):
        job_id = ask("Job id", (job.get("company") or "job") + "-" + (job.get("title") or "role"))
        saved = tailor.save_approved_variant(job_id, res, job)
        print(f"  Saved: {saved.get('path', job_id)} (local file — nothing sent)")


def wf_cover_letter() -> None:
    """Draft a cover letter with an honesty scan; save locally, never send."""
    _divider("DRAFT COVER LETTER")
    profile, job = _job_details()
    res = cover_letters.draft_cover_letter(profile, job)
    letter = res.get("letter", "")
    print("\n" + letter + "\n")
    issues = cover_letters.honesty_scan(letter, profile, job) or []
    if issues:
        print("  Honesty scan flags:")
        for i in issues[:5]:
            if isinstance(i, dict):
                print(f"  ! {i.get('type', '?')}: {str(i.get('text', i))[:110]}")
            else:
                print(f"  ! {str(i)[:110]}")
    else:
        print("  Honesty scan: clean.")
    if ask_yes_no("Save this letter as the approved local version?"):
        job_id = ask("Job id", (job.get("company") or "job") + "-" + (job.get("title") or "role"))
        saved = cover_letters.approve_letter(job_id, letter)
        print(f"  Approved & saved locally: {saved.get('path', job_id)}")
    print("  Note: the dashboard never emails anything — send via your own flow.")


def wf_linkedin() -> None:
    """Audit the LinkedIn profile; preview a rewritten headline."""
    _divider("LINKEDIN AUDIT")
    profile = load_profile()
    targets = profile.get("target_titles") or []
    target_role = ask("Target role", str(targets[0]) if targets else "")
    audit = linkedin_optimizer.audit_profile(profile, target_role or None)
    print(f"\n  Overall: {audit.get('overall', '?')}/100")
    sections = audit.get("sections") or {}
    for name, s in list(sections.items())[:4]:
        if isinstance(s, dict):
            fix = (s.get("fixes") or [""])[0]
            print(f"  {name}: {s.get('score', '?')} — {str(fix)[:90]}")
    for fix in (audit.get("top_fixes") or [])[:3]:
        print(f"  → {fix}"[:100])
    if ask_yes_no("Preview a rewritten headline?", default=True):
        rw = linkedin_optimizer.rewrite_headline(profile, target_role or None)
        headline = rw.get("headline", "")
        print(f"\n  Suggested headline: {headline}")
        for src in (rw.get("built_from") or [])[:3]:
            print(f"    from: {src}")
        print("  Preview only — paste your pick into LinkedIn yourself.")


# ---------------------------------------------------------------------------
# TRAIN workflows
# ---------------------------------------------------------------------------


def wf_mock_interview() -> None:
    """Run a short mock interview: questions, answers, summary."""
    _divider("MOCK INTERVIEW")
    company = ask("Company", "Acme")
    role = ask("Role", "Backend Engineer")
    n = ask_int("Questions", 3, lo=1, hi=8)
    sess = mock_interview.start_mock_interview(company=company, role=role)
    sid = sess["session_id"]
    question = (sess.get("first_question") or {}).get("question", "")
    for i in range(n):
        if not question:
            break
        print(f"\n  Q{i + 1}: {question}")
        answer = _read("  Your answer (blank = finish): ").strip()
        if not answer:
            break
        res = mock_interview.answer_mock_question(sid, answer)
        feedback = res.get("feedback")
        if isinstance(feedback, list):
            feedback = "; ".join(str(f) for f in feedback)
        if feedback:
            print(f"  Feedback: {feedback}")
        star = res.get("star") or {}
        if isinstance(star, dict):
            covered = [k.upper() for k, v in star.items()
                       if v and k.lower() in ("situation", "task", "action", "result")]
            print(f"  STAR covered: {', '.join(covered) or 'none yet'}")
        nxt = res.get("next_question") or {}
        question = nxt.get("question", "") if isinstance(nxt, dict) else ""
        if res.get("complete"):
            break
    summary = mock_interview.mock_summary(sid)
    overall = summary.get("overall_score", "?")
    print(f"\n  Session summary — score: {overall}/100 "
          f"({summary.get('answered', 0)}/{summary.get('total', '?')} answered)")
    for tip in (summary.get("top_tips") or [])[:4]:
        print(f"  • {tip}")


def wf_soft_skills() -> None:
    """Run one soft-skills drill round with coaching feedback."""
    _divider("SOFT-SKILLS DRILL")
    areas = sorted(soft_skills.SKILL_AREAS)
    area = ask_choice("Skill area", areas, default="star_storytelling")
    difficulty = ask_choice("Difficulty", list(soft_skills.DIFFICULTIES), default="firm")
    sess = soft_skills.drill(area=area, difficulty=difficulty)
    print(f"\n  Prompt: {sess.get('prompt')}")
    answer = _read("  Your answer (blank = skip review): ").strip()
    if not answer:
        print(f"  Session {sess['session_id']} saved; review it later with the CLI.")
        return
    res = soft_skills.review_drill(sess["session_id"], answer)
    coach = res.get("coach") or {}
    feedback = coach.get("feedback") if isinstance(coach, dict) else None
    if isinstance(feedback, list):
        print("\n  Coach feedback:")
        for line in feedback:
            print(f"  • {line}")
    elif feedback:
        print(f"\n  Coach: {feedback}")
    debrief = res.get("debrief") or {}
    score = debrief.get("score") if isinstance(debrief, dict) else None
    if score is not None:
        print(f"  Score: {score}")


def wf_ai_proficiency() -> None:
    """Pick an AI track, do one lesson exercise, get scored."""
    _divider("AI PROFICIENCY")
    tracks = ai_proficiency.list_tracks()
    labels = [f"{t.get('label', t['id'])} [{t['id']}]" for t in tracks]
    pick = ask_choice("Track", labels, default=labels[0])
    tid = pick.rsplit("[", 1)[-1].rstrip("]")
    plan = ai_proficiency.plan(tid)
    lessons = plan.get("lessons") or []
    if not lessons:
        print("  No lessons in this track.")
        return
    llabels = [f"{l.get('title', l.get('id'))} [{l['id']}]" for l in lessons]
    lp = ask_choice("Lesson", llabels, default=llabels[0])
    lid = lp.rsplit("[", 1)[-1].rstrip("]")
    ex = ai_proficiency.exercise(tid, lid)
    print(f"\n  {ex.get('title', lid)}")
    print(f"  {ex.get('exercise_prompt')}")
    if ex.get("hint"):
        print(f"  Hint: {ex['hint']}")
    response = _read("  Your response (blank = skip): ").strip()
    if not response:
        print("  Skipped — the lesson stays open.")
        return
    sub = ai_proficiency.submit_exercise(ex["session_id"], response)
    print(f"\n  Score: {sub.get('score')} — {'passed' if sub.get('passed') else 'keep practicing'}")
    print(f"  {sub.get('feedback')}")
    if sub.get("next_lesson"):
        print(f"  Next: {sub['next_lesson']}")


def wf_skill_gaps() -> None:
    """Analyze skill gaps between the profile and one JD."""
    _divider("SKILL GAPS")
    profile = load_profile()
    title = ask("Job title", "")
    jd = read_text_or_file("Job description")
    if not jd.strip():
        print("  Empty JD — nothing to analyze.")
        return
    g = skill_gaps.analyze_gaps(profile or None, [{"title": title, "description": jd}])
    gaps = g.get("gaps") or []
    if not gaps:
        print("  No gaps found — strong match.")
        return
    print(f"\n  Top gaps (from {g.get('jobs_analyzed', 1)} job):")
    for gap in gaps[:6]:
        lesson = gap.get("lesson") or ""
        print(f"  • {gap.get('skill')} (in {gap.get('job_count', '?')} job(s), "
              f"weight {gap.get('weighted_score', '?')})"
              + (f" → lesson: {lesson}" if lesson else ""))


def wf_mentors() -> None:
    """Matchmake mentors; preview a connection note (never send)."""
    _divider("FIND A MENTOR")
    industry = ask("Your industry", "tech")
    target_role = ask("Target role", "Senior Engineer")
    topics = [t.strip() for t in ask("Topics, most important first (comma-separated)",
                                     "system_design, interviews").split(",") if t.strip()]
    goal = ask("Your goal in one sentence", "Land a senior backend role", required=True)
    m = mentors.matchmake({"industry": industry, "target_role": target_role,
                           "topics_ranked": topics, "goal": goal})
    matches = m.get("matches") or []
    if not matches:
        print(f"  {m.get('guidance', 'No mentors available right now.')}")
        return
    print(f"\n  Top {min(3, len(matches))} matches:")
    for cand in matches[:3]:
        name = cand.get("name") or "?"
        print(f"  • {name} — {cand.get('role', '')} ({cand.get('industry', '')}, "
              f"score {cand.get('score', '?')})")
    if ask_yes_no("Preview a connection note for the top match?"):
        top = matches[0]
        mid = top.get("mentor_id") or top.get("id") or ""
        me = str((load_profile() or {}).get("full_name") or "a mentee")
        draft = mentors.connection_draft(mid, me, goal)
        print(f"\n  Status: {draft.get('status', 'draft — not sent')}")
        print(f"  {draft.get('note', '')}")
        for item in (draft.get("prep_checklist") or [])[:3]:
            print(f"  prep: {item}")
        print("  Preview only — the dashboard never sends connection requests.")


# ---------------------------------------------------------------------------
# WIN workflows
# ---------------------------------------------------------------------------


def wf_followup() -> None:
    """List due follow-ups, show a draft. The dashboard never sends email."""
    _divider("FOLLOW-UPS DUE")
    profile = load_profile()
    items = followup.followups_with_drafts(profile)
    if not items:
        print("  No follow-ups due — you're all caught up.")
        return
    labels = [f"{(i['entry'].get('company') or '?')} — {(i['entry'].get('title') or '?')} "
              f"[{i['entry'].get('stage', 'applied')}]" for i in items]
    pick = ask_choice("Which application", labels, default=labels[0])
    draft = items[labels.index(pick)]["draft"]
    print(f"\n  To: {draft.get('to') or '(no contact on file)'}")
    print(f"  Subject: {draft.get('subject')}")
    print(f"  Kind: {draft.get('kind')} | Waiting: {draft.get('days_waiting')} days\n")
    print("  " + draft.get("body", "").replace("\n", "\n  "))
    print("\n  The dashboard never sends email — send this via the followup "
          "module's own confirm flow.")


def wf_referrals() -> None:
    """Rank referral paths to target companies from the connections CSV."""
    _divider("REFERRAL PATHS")
    csv_path = ask("Connections CSV", str(REPO_DIR / "profiles" / "connections.csv"))
    try:
        conns = referrals.load_connections(csv_path)
    except (OSError, ValueError) as exc:
        print(f"  Could not load connections: {exc}")
        return
    if not conns:
        print("  No connections loaded — check the CSV path.")
        return
    targets = [t.strip() for t in ask("Target companies (comma-separated)",
                                     required=True).split(",") if t.strip()]
    ranked = referrals.rank_referrals(conns, targets, None)
    if not ranked:
        print("  No warm paths found to those companies.")
        return
    print(f"\n  Top {min(5, len(ranked))} paths:")
    for r in ranked[:5]:
        print(f"  • {r.get('name', '?')} — {r.get('company', '')} "
              f"(warmth {r.get('warmth', r.get('score', '?'))})")
        if r.get("reason"):
            print(f"    {str(r['reason'])[:100]}")


def wf_network_crm() -> None:
    """Add a contact, log an interaction, or see who to nudge."""
    _divider("NETWORK CRM")
    action = ask_choice("Action", ["add contact", "log interaction", "nudges due"],
                        default="nudges due")
    if action == "add contact":
        name = ask("Name", required=True)
        company = ask("Company", required=True)
        role = ask("Their role", "")
        linkedin = ask("LinkedIn URL", "")
        res = network_crm.add_contact(name=name, company=company, role=role,
                                      linkedin_url=linkedin)
        print(f"  Added: {res.get('name')} @ {res.get('company')} (id {res.get('id')})")
    elif action == "log interaction":
        cid = ask("Contact id", required=True)
        kind = ask_choice("Kind", ["intro", "call", "coffee", "email", "linkedin", "followup"],
                          default="followup")
        summary = ask("Summary", required=True)
        due = ask("Follow-up due date (YYYY-MM-DD, blank = none)", "")
        res = network_crm.log_interaction(cid, kind, summary, due or None)
        print(f"  Logged: {res.get('ok', res)}")
    else:
        nudges = network_crm.nudge_list()
        if not nudges:
            print("  No nudges due.")
            return
        print(f"\n  {len(nudges)} nudge(s) due:")
        for n in nudges[:8]:
            print(f"  • {n.get('name', '?')} @ {n.get('company', '')} — "
                  f"{str(n.get('reason', n.get('due', '')))[:100]}")


def wf_offer_compare() -> None:
    """Add offers locally and compare them by weighted score."""
    _divider("COMPARE OFFERS")
    action = ask_choice("Action", ["add offer", "compare offers"],
                        default="compare offers")
    if action == "add offer":
        name = ask("Offer name", required=True)
        base = ask_float("Base salary", 150000)
        bonus = ask_float("Annual bonus", 0)
        equity = ask_float("Total equity value", 0)
        remote = ask_choice("Work mode", ["onsite", "hybrid", "remote"], default="remote")
        res = offer_compare.add_offer(name=name, base=base, bonus=bonus,
                                      equity_total=equity, remote=remote)
        offer = res.get("offer", {}) if isinstance(res, dict) else {}
        print(f"  Added {offer.get('name')} (id {offer.get('id')}) — local only, nothing sent.")
        return
    res = offer_compare.compare_offers()
    if not res.get("ok"):
        print(f"  {res.get('error', 'Add at least two offers first.')}")
        return
    offers = res.get("offers") or []
    print("\n  Ranked:")
    for o in offers:
        offer = o.get("offer", {})
        score = o.get("weighted_total")
        score_txt = f"{score:.1f}" if isinstance(score, (int, float)) else "?"
        comp = o.get("comp_4yr")
        comp_txt = f"${comp:,.0f}" if isinstance(comp, (int, float)) else "?"
        print(f"  {o.get('rank', '?')}. {offer.get('name')} — score {score_txt} "
              f"(4-yr comp {comp_txt})")
    if offers:
        print(f"\n  Leader: {offers[0].get('offer', {}).get('name')}")


def wf_rejection_autopsy() -> None:
    """Diagnose rejection patterns from recorded outcomes."""
    _divider("REJECTION AUTOPSY")
    d = rejection_autopsy.diagnose()
    if d.get("summary"):
        print(f"\n  {d['summary']}")
    for s in (d.get("suggestions") or [])[:4]:
        if isinstance(s, dict):
            finding = s.get("finding", "")
            fix = s.get("fix", "")
            print(f"  • {finding}")
            if fix:
                print(f"    Fix: {fix}")
        else:
            print(f"  • {s}")
    if not d.get("suggestions"):
        print("  Not enough outcome data yet — record outcomes as decisions land.")


# ---------------------------------------------------------------------------
# GOVERN workflows
# ---------------------------------------------------------------------------


def wf_crew() -> None:
    """Red-team scan a text; screen a planned task for compliance."""
    _divider("GOVERNANCE — CREW")
    text = _read("Text to red-team scan (blank = skip): ").strip()
    if text:
        r = crew.red_team_scan(text)
        print(f"\n  Verdict: {r.get('verdict')}")
        for f in (r.get("findings") or [])[:5]:
            if isinstance(f, dict):
                print(f"  ! {f.get('label', f.get('type', '?'))}: "
                      f"{str(f.get('quote', f.get('detail', '')))[:100]}")
            else:
                print(f"  ! {str(f)[:100]}")
    if ask_yes_no("Screen a planned task for compliance?"):
        task = ask("Task description", required=True)
        s = crew.compliance_screen(task)
        print(f"  Allowed: {s.get('allowed')}")
        for flag in (s.get("flags") or [])[:5]:
            print(f"  ! {str(flag)[:110]}")


def wf_streaks() -> None:
    """Show streaks and log one rep."""
    _divider("STREAKS")
    s = streaks.streaks()
    overall = s.get("overall_streak", 0)
    if isinstance(overall, dict):
        overall = overall.get("current", 0)
    print(f"\n  Overall day streak: {overall}")
    per_kind = s.get("kinds") or s.get("per_kind") or {}
    for kind, info in list(per_kind.items())[:7]:
        cur = info.get("current", info) if isinstance(info, dict) else info
        print(f"  {streaks.KIND_LABELS.get(kind, kind)}: {cur} day(s)")
    kind = ask_choice("Log a rep", list(streaks.REP_KINDS), default="application")
    if not ask_yes_no(f"Log one '{kind}' rep now?"):
        print("  Not logged.")
        return
    entry = streaks.log_rep(kind)
    rep = entry.get("rep") or {}
    when = rep.get("ts")
    when_s = (datetime.fromtimestamp(when).strftime("%Y-%m-%d %H:%M")
              if isinstance(when, (int, float)) else "today")
    print(f"  Logged {kind} rep at {when_s}. Keep it going.")


def wf_contribute() -> None:
    """Preview a contribution bundle. Preview only — never submit."""
    _divider("CONTRIBUTE (PREVIEW ONLY)")
    listing = contribute.list_contributable()
    items = listing.get("contributable") or []
    print(f"  {listing.get('count', len(items))} completed session(s) eligible.")
    for it in items[:5]:
        print(f"  • {it.get('session_id')} — {it.get('source')}/"
              f"{it.get('session_type')} (score {it.get('score')})")
    if not items:
        print("  Finish a mock interview, drill, or AI lesson to unlock this.")
        return
    ids = [i.strip() for i in ask("Session ids to preview (comma-separated)",
                                  required=True).split(",") if i.strip()]
    preview = contribute.preview_contribution(ids)
    if preview.get("error"):
        print(f"  {preview['error']}")
        return
    bundle = preview.get("bundle") or {}
    sessions = bundle.get("sessions") or []
    print(f"\n  Bundle hash: {preview.get('bundle_hash', '?')}")
    print(f"  Sessions in bundle: {len(sessions)} | "
          f"Scrub rules applied: {len(preview.get('scrub_rules') or [])}")
    for s in sessions[:3]:
        text = str(s.get("scrubbed_transcript", s.get("transcript", "")))
        print(f"  • {s.get('session_id')}: {text[:120]}")
    print("\n  Preview only — the dashboard never submits contributions.")
    print("  To contribute, use the contribute module's own confirm flow.")


# ---------------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------------


def wf_wizard() -> None:
    """Hand the terminal to the onboarding wizard."""
    print("  Launching the onboarding wizard…")
    subprocess.run([sys.executable, str(REPO_DIR / "wizard.py")], check=False)


def wf_doctor() -> None:
    """Run the setup health check and print the report."""
    _divider("DOCTOR")
    report = doctor.run_doctor()
    for check in report.get("checks", []):
        mark = "OK  " if check.get("ok") else "FAIL"
        sev = "" if check.get("severity") == "error" else " [warning]"
        print(f"  [{mark}]{sev} {check.get('name')}: {check.get('detail')}")
    print(f"\n  Doctor: {'PASS' if report.get('ok') else 'FAIL'}")


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

# key -> (label, workflow)
MENU: dict[str, tuple[str, object]] = {
    "1": ("Score a job against your profile", wf_match),
    "2": ("Decode a job description", wf_jd_decoder),
    "3": ("Draw a fit radar chart", wf_radar),
    "4": ("Tailor resume bullets to a JD", wf_tailor),
    "5": ("Draft a cover letter", wf_cover_letter),
    "6": ("Audit my LinkedIn profile", wf_linkedin),
    "7": ("Run a mock interview", wf_mock_interview),
    "8": ("Soft-skills drill", wf_soft_skills),
    "9": ("AI proficiency lesson", wf_ai_proficiency),
    "10": ("Find my skill gaps", wf_skill_gaps),
    "11": ("Find a mentor", wf_mentors),
    "12": ("Follow-ups due", wf_followup),
    "13": ("Referral paths", wf_referrals),
    "14": ("Network CRM", wf_network_crm),
    "15": ("Compare offers", wf_offer_compare),
    "16": ("Rejection autopsy", wf_rejection_autopsy),
    "17": ("Red-team scan / compliance screen", wf_crew),
    "18": ("Log a rep / view streaks", wf_streaks),
    "19": ("Preview a data contribution", wf_contribute),
    "w": ("Onboarding wizard", wf_wizard),
    "d": ("Run the doctor", wf_doctor),
}


def print_menu() -> None:
    """Print the grouped menu."""
    groups = [
        ("FIND", ["1", "2", "3"]),
        ("TAILOR", ["4", "5", "6"]),
        ("TRAIN", ["7", "8", "9", "10", "11"]),
        ("WIN", ["12", "13", "14", "15", "16"]),
        ("GOVERN", ["17", "18", "19"]),
        ("UTILITIES", ["w", "d"]),
    ]
    print()
    for name, keys in groups:
        print(f"  {name}")
        for key in keys:
            label, _ = MENU[key]
            print(f"    {key:>3}  {label}")
    print("      q  Quit")


def run_dashboard() -> int:
    """Main menu loop; Ctrl-C / EOF exits cleanly."""
    while True:
        print("\n  ══ JOB-APPLY DASHBOARD ══")
        print()
        print_kpis()
        print_menu()
        try:
            choice = _read("\n  Choice [q]: ").strip().lower() or "q"
        except _Quit:
            print("\n  Goodbye — good hunting.")
            return 0
        if choice in ("q", "quit", "exit"):
            print("  Goodbye — good hunting.")
            return 0
        entry = MENU.get(choice)
        if entry is None:
            print("  Unknown choice — pick a number, w, d, or q.")
            continue
        label, fn = entry
        try:
            fn()  # type: ignore[operator]
        except _Quit:
            print("\n  Goodbye — good hunting.")
            return 0
        except Exception as exc:  # never traceback on bad input
            print(f"  Oops — {exc}. Nothing was sent anywhere.")
        _read("\n  [Enter to continue]")


def cmd_dashboard(args: argparse.Namespace) -> int:
    """Handler for the ``dashboard`` CLI command.

    Takes an argparse namespace and ignores it; the coordinator wires the
    ``dashboard`` subparser and maps it here.
    """
    del args
    try:
        return run_dashboard()
    except _Quit:
        print("\n  Goodbye — good hunting.")
        return 0


if __name__ == "__main__":
    sys.exit(cmd_dashboard(argparse.Namespace()))
