"""Veto Web UI backend — stdlib-only HTTP API server.

Serves the static frontend in ``webui/`` (built by the frontend worker)
plus a JSON API over the real job-apply modules:

  GET  /api/tools        -> tool/action/param catalog
  GET  /api/kpis         -> dashboard_data.compute_kpis(repo_root)
  POST /api/run          -> {"tool","action","params"} dispatch

Destructive actions (follow-up send, contribution submit, application
record) are confirm-gated: the first call returns a preview + preview_hash,
and a second call with {"confirmed": true, "preview_hash": ...} only
proceeds when the recomputed hash matches.

Exposes ``cmd_serve(args)`` for cli.py wiring. Stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import html as _html  # noqa: F401  (kept for potential template use)
import json
import math
import mimetypes
import os
import sys
import threading
import traceback
import webbrowser
from datetime import date, datetime, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

WEBUI_DIR = BASE_DIR / "webui"
DEFAULT_PORT = 8765
MAX_BODY = 5 * 1024 * 1024  # 5 MB
_LIST_CAP = 500
_DEPTH_CAP = 12


# ---------------------------------------------------------------------------
# JSON sanitization
# ---------------------------------------------------------------------------

def _clean(obj, _depth=0):
    """Convert arbitrary module output into JSON-serializable data."""
    if _depth > _DEPTH_CAP:
        return "<max-depth>"
    if obj is None or isinstance(obj, (str, int, bool)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, (date, datetime, time)):
        return obj.isoformat()
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _clean(v, _depth + 1) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v, _depth + 1) for v in obj[:_LIST_CAP]]
    if isinstance(obj, (set, frozenset)):
        return [_clean(v, _depth + 1)
                for v in sorted(obj, key=repr)[:_LIST_CAP]]
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8", "replace")
        except Exception:
            return repr(obj)
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return repr(obj)


def _require(params, *names):
    missing = [n for n in names if params.get(n) in (None, "")]
    if missing:
        raise ValueError("missing required param(s): " + ", ".join(missing))


def _profile(params):
    """Profile dict for actions: explicit param or the saved default profile."""
    p = params.get("profile")
    if isinstance(p, dict) and p:
        return p
    try:
        from profiles import load_profile
        prof = load_profile("")
        return prof if isinstance(prof, dict) else {}
    except Exception:
        return {}


def _preview_payload(preview: str):
    digest = hashlib.sha256(preview.encode("utf-8")).hexdigest()
    return {
        "ok": False,
        "needs_confirm": True,
        "preview": preview,
        "preview_hash": digest,
    }


class _GateError(Exception):
    """A preview/validation failure from a confirm-gated action (user-facing)."""

# ---------------------------------------------------------------------------
# Action handlers — each calls the REAL module function. No reimplementation.
# ---------------------------------------------------------------------------

# ---- FIND: match --------------------------------------------------------

def _h_match_score(params):
    import match
    _require(params, "job")
    return match.score_job(params["job"], _profile(params), params.get("preferences"))


def _h_match_rank(params):
    import match
    _require(params, "jobs")
    jobs = list(params["jobs"])[:50]
    return match.rank_jobs(jobs, _profile(params), params.get("preferences"))


# ---- FIND: radar --------------------------------------------------------

def _h_radar_svg(params):
    import radar
    _require(params, "score")
    return {"svg": radar.radar_svg(
        params["score"],
        title=params.get("title"),
        size=int(params.get("size") or 400),
        color=params.get("color") or "#ffb000",
    )}


def _h_radar_compare(params):
    import radar
    _require(params, "items")
    labeled = []
    for item in params["items"][:20]:
        labeled.append((item.get("name", "?"), item.get("components", {})))
    return {"svg": radar.compare_svg(labeled, title=params.get("title") or "Fit comparison")}


def _h_radar_html(params):
    import radar
    _require(params, "items")
    labeled = []
    for item in params["items"][:20]:
        labeled.append((item.get("name", "?"), item.get("components", {})))
    return {"html": radar.radar_html(labeled, title=params.get("title") or "Veto fit radar")}


# ---- FIND: jd_decoder -----------------------------------------------------

def _h_jd_decode(params):
    import jd_decoder
    _require(params, "text")
    return jd_decoder.decode_jd(params["text"])


def _h_jd_verdict(params):
    import jd_decoder
    _require(params, "text")
    return jd_decoder.jd_verdict(params["text"])


# ---- FIND: referrals ------------------------------------------------------

def _h_referrals_find(params):
    import referrals
    return referrals.find_referrals_data(
        company=params.get("company") or "",
        limit=int(params.get("limit") or 10),
    )


def _h_referrals_rank(params):
    import referrals
    _require(params, "connections", "targets")
    return referrals.rank_referrals(params["connections"], params["targets"],
                                    _profile(params))


def _h_referrals_outreach(params):
    import referrals
    _require(params, "contact")
    return referrals.draft_outreach(params["contact"], params.get("job"),
                                    _profile(params),
                                    kind=params.get("kind") or "warm")


def _h_referrals_targets(_params):
    import referrals
    return {"companies": referrals.target_companies()}


# ---- TAILOR: tailor -------------------------------------------------------

def _h_tailor_resume(params):
    import tailor
    _require(params, "job")
    return tailor.tailor_resume(_profile(params), params["job"])


def _h_tailor_diff(params):
    import tailor
    _require(params, "job")
    return tailor.tailor_with_diff(_profile(params), params["job"])


def _h_tailor_keywords(params):
    import tailor
    _require(params, "job")
    return tailor.extract_job_keywords(params["job"], _profile(params))


def _h_tailor_variants(_params):
    import tailor
    return {"variants": tailor.list_approved_variants()}


def _h_tailor_variant(params):
    import tailor
    _require(params, "job_id")
    return {"variant": tailor.load_approved_variant(params["job_id"])}


# ---- TAILOR: cover_letters --------------------------------------------------

def _h_cover_draft(params):
    import cover_letters
    _require(params, "job")
    return cover_letters.draft_cover_letter(_profile(params), params["job"])


def _h_cover_honesty(params):
    import cover_letters
    _require(params, "letter")
    return {"flags": cover_letters.honesty_scan(params["letter"], _profile(params),
                                                params.get("job"))}


def _h_cover_approve(params):
    import cover_letters
    _require(params, "job_id", "letter")
    return cover_letters.approve_letter(params["job_id"], params["letter"])


def _h_cover_list(_params):
    import cover_letters
    return {"letters": cover_letters.list_letters()}


# ---- TAILOR: linkedin_optimizer ----------------------------------------------

def _h_linkedin_audit(params):
    import linkedin_optimizer
    return linkedin_optimizer.audit_profile(_profile(params), params.get("target_role"))


def _h_linkedin_headline(params):
    import linkedin_optimizer
    return linkedin_optimizer.rewrite_headline(_profile(params), params.get("target_role"))


def _h_linkedin_about(params):
    import linkedin_optimizer
    return linkedin_optimizer.rewrite_about(_profile(params))


def _h_linkedin_keyword_gap(params):
    import linkedin_optimizer
    return linkedin_optimizer.keyword_gap(_profile(params), params.get("target_role"))

# ---- TRAIN: mock_interview --------------------------------------------------

def _h_mock_start(params):
    import mock_interview
    _require(params, "company", "role")
    return mock_interview.start_mock_interview(
        params["company"], params["role"],
        profile=_profile(params) or {},
        channel=params.get("channel") or "chat",
        job_id=params.get("job_id"),
    )


def _h_mock_answer(params):
    import mock_interview
    _require(params, "session_id", "answer")
    return mock_interview.answer_mock_question(params["session_id"], params["answer"])


def _h_mock_summary(params):
    import mock_interview
    _require(params, "session_id")
    return mock_interview.mock_summary(params["session_id"])


# ---- TRAIN: soft_skills -----------------------------------------------------

def _h_soft_assess(params):
    import soft_skills
    _require(params, "area", "answers")
    return soft_skills.assess(params["area"], params["answers"])


def _h_soft_drill(params):
    import soft_skills
    _require(params, "area")
    return soft_skills.drill(params["area"], _profile(params),
                             mode=params.get("mode") or "coach",
                             difficulty=params.get("difficulty") or "firm")


def _h_soft_review(params):
    import soft_skills
    _require(params, "session_id", "answer")
    return soft_skills.review_drill(params["session_id"], params["answer"])


def _h_soft_negotiate(params):
    import soft_skills
    _require(params, "current_offer", "target")
    return soft_skills.negotiation_sim(float(params["current_offer"]),
                                      float(params["target"]),
                                      _profile(params),
                                      difficulty=params.get("difficulty") or "firm")


# ---- TRAIN: ai_proficiency ----------------------------------------------------

def _h_ai_tracks(_params):
    import ai_proficiency
    return {"tracks": ai_proficiency.list_tracks()}


def _h_ai_plan(params):
    import ai_proficiency
    _require(params, "track")
    return ai_proficiency.plan(params["track"], params.get("level"))


def _h_ai_lesson(params):
    import ai_proficiency
    _require(params, "track", "lesson_id")
    return ai_proficiency.get_lesson(params["track"], params["lesson_id"])


def _h_ai_exercise(params):
    import ai_proficiency
    _require(params, "track", "lesson_id")
    return ai_proficiency.exercise(params["track"], params["lesson_id"])


def _h_ai_submit(params):
    import ai_proficiency
    _require(params, "session_id", "response")
    return ai_proficiency.submit_exercise(params["session_id"], params["response"])


def _h_ai_progress(_params):
    import ai_proficiency
    return ai_proficiency.progress()


def _h_ai_diagnose(params):
    import ai_proficiency
    _require(params, "track", "answers")
    return ai_proficiency.diagnose(params["track"], params["answers"])


# ---- TRAIN: mentors -----------------------------------------------------------

def _h_mentors_matchmake(params):
    import mentors
    _require(params, "answers")
    return mentors.matchmake(params["answers"])


def _h_mentors_outreach(params):
    import mentors
    _require(params, "mentor_id", "mentee_name", "mentee_goal")
    return mentors.connection_draft(params["mentor_id"], params["mentee_name"],
                                    params["mentee_goal"])


def _h_mentors_prep(params):
    import mentors
    _require(params, "topic")
    return mentors.prep_for_topic(params["topic"])


def _h_mentors_suggest(_params):
    import mentors
    return mentors.suggest_mentors_from_training()


def _h_mentors_opt_in(params):
    import mentors
    _require(params, "profile")
    return mentors.mentor_opt_in(params["profile"])


def _h_mentors_opt_out(params):
    import mentors
    return mentors.mentor_opt_out(params.get("mentor_id"))


def _h_mentors_card(params):
    import mentors
    return mentors.my_mentor_card(params.get("updates"))


def _h_mentors_record_outreach(params):
    import mentors
    _require(params, "mentor_id")
    return mentors.record_outreach(params["mentor_id"])


# ---- TRAIN: skill_gaps --------------------------------------------------------

def _h_gaps_analyze(params):
    import skill_gaps
    return skill_gaps.analyze_gaps(profile=params.get("profile") or _profile(params),
                                  jobs=params.get("jobs"))


def _h_gaps_plan(_params):
    import skill_gaps
    return skill_gaps.gap_plan()


def _h_gaps_mark(params):
    import skill_gaps
    _require(params, "skill", "status")
    return skill_gaps.mark_gap_progress(params["skill"], params["status"],
                                       params.get("evidence"))

# ---- WIN: followup ------------------------------------------------------------

def _h_followup_draft(params):
    import followup
    _require(params, "entry")
    return followup.draft_followup(params["entry"], _profile(params))


def _h_followup_drafts(params):
    import followup
    return {"drafts": followup.followups_with_drafts(_profile(params))}


def _followup_preview(params):
    _require(params, "entry_id", "to", "subject", "body")
    return "\n".join([
        "FOLLOW-UP EMAIL — review before confirming",
        f"Entry:   {params['entry_id']}",
        f"To:      {params['to']}",
        f"Subject: {params['subject']}",
        "",
        params["body"],
    ])


def _followup_send_confirmed(params):
    import followup
    return followup.send_followup(params["entry_id"], params["to"],
                                  params["subject"], params["body"],
                                  confirmed=True)


# ---- WIN: network_crm -----------------------------------------------------------

def _h_crm_add(params):
    import network_crm
    _require(params, "name", "company")
    return network_crm.add_contact(
        params["name"], params["company"],
        role=params.get("role") or "", industry=params.get("industry") or "",
        linkedin_url=params.get("linkedin_url") or "",
        source=params.get("source") or "", notes=params.get("notes") or "",
    )


def _h_crm_list(_params):
    import network_crm
    return {"contacts": network_crm.list_contacts()}


def _h_crm_log(params):
    import network_crm
    _require(params, "contact_id", "kind", "summary")
    return network_crm.log_interaction(params["contact_id"], params["kind"],
                                      params["summary"], params.get("due"))


def _h_crm_nudges(_params):
    import network_crm
    return {"nudges": network_crm.nudge_list()}


def _h_crm_warm_path(params):
    import network_crm
    _require(params, "company")
    return {"path": network_crm.warm_path_to(params["company"])}


# ---- WIN: offer_compare -----------------------------------------------------------

def _h_offer_add(params):
    import offer_compare
    _require(params, "name", "base")
    return offer_compare.add_offer(
        params["name"], float(params["base"]),
        bonus=float(params.get("bonus") or 0),
        equity_total=float(params.get("equity_total") or 0),
        equity_years=float(params.get("equity_years") or 4),
        benefits_value=float(params.get("benefits_value") or 0),
        pto_days=float(params.get("pto_days") or 15),
        remote=params.get("remote") or "onsite",
        location=params.get("location") or "",
        growth_score=float(params.get("growth_score") or 5),
        notes=params.get("notes") or "",
    )


def _h_offer_list(_params):
    import offer_compare
    return offer_compare.list_offers()


def _h_offer_report(params):
    import offer_compare
    _require(params, "offer_id")
    return offer_compare.offer_report(params["offer_id"])


def _h_offer_compare(params):
    import offer_compare
    return offer_compare.compare_offers(params.get("weights"))


def _h_offer_weights(_params):
    import offer_compare
    return {"weights": offer_compare.get_weights()}


def _h_offer_set_weights(params):
    import offer_compare
    _require(params, "overrides")
    return offer_compare.set_weights(params["overrides"])


# ---- WIN: rejection_autopsy -------------------------------------------------------

def _h_autopsy_record(params):
    import rejection_autopsy
    _require(params, "job_id", "outcome", "stage")
    return rejection_autopsy.record_outcome(
        params["job_id"], params["outcome"], params["stage"],
        notes=params.get("notes") or "", applied_at=params.get("applied_at"),
    )


def _h_autopsy_run(_params):
    import rejection_autopsy
    return rejection_autopsy.autopsy()


def _h_autopsy_diagnose(_params):
    import rejection_autopsy
    return rejection_autopsy.diagnose()


# ---- WIN: streaks -------------------------------------------------------------------

def _h_streaks_log(params):
    import streaks
    _require(params, "kind")
    return streaks.log_rep(params["kind"])


def _h_streaks_view(_params):
    import streaks
    return streaks.streaks()


def _h_streaks_set_goal(params):
    import streaks
    _require(params, "kind", "daily_target")
    return streaks.set_goal(params["kind"], int(params["daily_target"]))


def _h_streaks_goals(_params):
    import streaks
    return streaks.goals()


def _h_streaks_today(_params):
    import streaks
    return streaks.today()


def _h_streaks_weekly(_params):
    import streaks
    return streaks.weekly_recap()


def _h_streaks_card(_params):
    import streaks
    return streaks.share_card()

# ---- GOVERN: contribute --------------------------------------------------------

def _h_contrib_preview(params):
    import contribute
    _require(params, "session_ids")
    return contribute.preview_contribution(list(params["session_ids"]))


def _contrib_preview_canonical(params):
    """Canonical preview for the contribute submit gate.

    Calls preview_contribution (which records the bundle hash in the
    module's preview registry — required for submit to succeed) and
    derives a canonical string from the deterministic bundle_hash."""
    _require(params, "session_ids")
    import contribute
    session_ids = list(params["session_ids"])
    result = contribute.preview_contribution(session_ids)
    if "bundle_hash" not in result:
        raise _GateError(result.get("error") or "could not build contribution bundle")
    canonical = json.dumps(
        {"session_ids": sorted(str(s) for s in session_ids),
         "bundle_hash": result["bundle_hash"]},
        sort_keys=True,
    )
    preview_text = "\n".join([
        "CONTRIBUTION BUNDLE — review before confirming",
        f"bundle_hash: {result['bundle_hash']}",
        f"sessions: {result.get('bundle', {}).get('session_count', len(session_ids))}",
        "Scrubbed per the scrub rules (see scrub_rules action).",
        "Submit stages the bundle to the LOCAL outbox only — nothing is uploaded.",
    ])
    return canonical, preview_text


def _contrib_submit_confirmed(params):
    import contribute
    return contribute.submit_contribution(list(params["session_ids"]), confirmed=True)


def _h_contrib_scrub(_params):
    import contribute
    return {"rules": contribute.scrub_rules_report()}


def _h_contrib_toggle(params):
    import contribute
    _require(params, "enabled")
    return contribute.set_contributions_enabled(bool(params["enabled"]))


# ---- GOVERN: crew -------------------------------------------------------------------

def _h_crew_run(params):
    import crew
    _require(params, "persona_id", "task")
    return crew.run_agent(params["persona_id"], params["task"], params.get("context"))


def _h_crew_plan(params):
    import crew
    _require(params, "goal")
    return {"plan": crew.ceo_plan(params["goal"])}


def _h_crew_status(_params):
    import crew
    return crew.crew_status()


def _h_crew_red_team(params):
    import crew
    _require(params, "text")
    return crew.red_team_scan(params["text"])


def _h_crew_compliance(params):
    import crew
    _require(params, "task")
    return crew.compliance_screen(params["task"])


# ---- CORE: search -------------------------------------------------------------------

def _h_search_query(params):
    import server
    _require(params, "query", "location")
    return {"jobs": server.search_jobs(
        params["query"], params["location"],
        board=params.get("board") or "all",
        limit=int(params.get("limit") or 10),
        remote_only=bool(params.get("remote_only") or False),
        salary_min=int(params.get("salary_min") or 0),
        seniority=params.get("seniority") or "",
    )}


def _h_search_details(params):
    import server
    _require(params, "job_id")
    return server.get_job_details(params["job_id"])


def _h_search_boards(_params):
    import server
    return {"boards": server.list_boards()}


def _h_search_track(_params):
    import server
    return {"applications": server.track_applications()}


def _apply_preview_canonical(params):
    """Canonical preview for the apply record gate: a dry run."""
    _require(params, "job_id", "resume_path")
    import server
    preview = server.apply_to_job(
        params["job_id"], params["resume_path"],
        cover_letter=params.get("cover_letter") or "",
        answers=params.get("answers"),
        confirm=False,
        profile=_profile(params) if params.get("profile") else None,
        headless=bool(params.get("headless", True)),
    )
    canonical = json.dumps(preview, sort_keys=True, default=str)
    if isinstance(preview, dict) and preview.get("status") == "error":
        raise _GateError(str(preview.get("error") or "could not preview application"))
    job = (preview.get("preview") or {}) if isinstance(preview, dict) else {}
    text = "\n".join([
        "APPLICATION — review before confirming",
        f"Job:      {job.get('title', '?')} @ {job.get('company', '?')}",
        f"Location: {job.get('location', '?')}",
        f"Board:    {job.get('board', '?')}",
        f"Resume:   {params['resume_path']}",
        "",
        "Confirming records the application locally and returns the",
        "apply_url for manual completion in your browser.",
    ])
    return canonical, text


def _apply_record_confirmed(params):
    import server
    return server.apply_to_job(
        params["job_id"], params["resume_path"],
        cover_letter=params.get("cover_letter") or "",
        answers=params.get("answers"),
        confirm=True,
        profile=_profile(params) if params.get("profile") else None,
        headless=bool(params.get("headless", True)),
    )


# ---- CORE: apply_queue ----------------------------------------------------------------

def _h_queue_list(_params):
    import apply_queue
    return {"queue": apply_queue.list_queue()}


def _h_queue_remove(params):
    import apply_queue
    _require(params, "job_id")
    return {"removed": apply_queue.remove_from_queue(params["job_id"])}


def _queue_preview_canonical(params):
    _require(params, "job_id")
    return json.dumps(
        {"job_id": params["job_id"], "scheduled_for": params.get("scheduled_for")},
        sort_keys=True,
    ), "\n".join([
        "QUEUE APPLICATION — review before confirming",
        f"Job ID:       {params['job_id']}",
        f"Scheduled for:{params.get('scheduled_for') or 'as soon as possible'}",
        "",
        "Confirming adds this job to the local apply queue.",
    ])


def _queue_add_confirmed(params):
    import apply_queue
    return apply_queue.add_to_queue(params["job_id"],
                                   scheduled_for=params.get("scheduled_for"))


# ---- CORE: wizard -----------------------------------------------------------------------

def _h_wizard_blank(_params):
    import wizard
    return wizard.blank_profile()


def _h_wizard_merge(params):
    import wizard
    _require(params, "base", "linkedin")
    return wizard.merge_profile(params["base"], params["linkedin"])


# ---- CORE: doctor -------------------------------------------------------------------------

def _h_doctor_run(_params):
    import doctor
    return doctor.run_doctor()


def _h_doctor_profile(_params):
    import doctor
    return doctor.check_profile()


# ---- CORE: analytics ------------------------------------------------------------------------

def _h_analytics_report(params):
    import analytics
    return analytics.generate_report(stale_days=int(params.get("stale_days") or 14))


def _h_analytics_funnel(params):
    import analytics
    _require(params, "applications")
    return analytics.funnel(params["applications"])


def _h_analytics_response_rate(params):
    import analytics
    _require(params, "applications")
    return analytics.response_rate_by_board(params["applications"])


def _h_analytics_stale(params):
    import analytics
    _require(params, "applications")
    return {"stale": analytics.stale_applications(
        params["applications"], days=int(params.get("days") or 14))}


# ---------------------------------------------------------------------------
# Confirm-gated actions
# ---------------------------------------------------------------------------
# Each entry: preview builder -> (canonical_string_for_hashing, human_preview_text)
# plus the confirmed runner. The gate recomputes the canonical string and
# requires the supplied preview_hash to match before calling the module
# with confirmed=True.

def _followup_preview_pair(params):
    text = _followup_preview(params)
    return text, text  # canonical string is the exact preview text


GATED = {
    ("followup", "send"): {
        "preview": _followup_preview_pair,
        "run": _followup_send_confirmed,
    },
    ("contribute", "submit"): {
        "preview": _contrib_preview_canonical,
        "run": _contrib_submit_confirmed,
    },
    ("search", "record_apply"): {
        "preview": _apply_preview_canonical,
        "run": _apply_record_confirmed,
    },
    ("apply_queue", "add"): {
        "preview": _queue_preview_canonical,
        "run": _queue_add_confirmed,
    },
}

# ---------------------------------------------------------------------------
# Tool catalog for GET /api/tools
# ---------------------------------------------------------------------------
# Param schema entries: {name, type, required, default, help}.
# Types: string | integer | number | boolean | object | array.

def _p(name, type, required=False, default=None, help=""):
    p = {"name": name, "type": type, "required": bool(required), "help": help}
    if default is not None:
        p["default"] = default
    return p


def _profile_param(help="Profile object; defaults to the saved profile when omitted."):
    return _p("profile", "object", False, help=help)


def _a(action_id, description, handler, params):
    return {"id": action_id, "description": description,
            "handler": handler, "params": params}


TOOLS = [
    # ---------------- FIND ----------------
    {"id": "match", "group": "FIND", "name": "Job fit scoring",
     "description": "Deterministic 0-100 fit scores for jobs against your profile, with reasons, matched/missing skills, and veto flags.",
     "actions": [
         _a("score", "Score one job against your profile.",
            _h_match_score, [_p("job", "object", True, help="Job dict (title, company, description, requirements, location, salary)."),
                                        _profile_param(),
                                        _p("preferences", "object", False, help="Preferences dict (locations, salary_min, remote).")]),
         _a("rank", "Rank a list of jobs by fit (capped at 50).",
            _h_match_rank, [_p("jobs", "array", True, help="List of job dicts."),
                                       _profile_param(), _p("preferences", "object", False)]),
     ]},
    {"id": "radar", "group": "FIND", "name": "Fit radar charts",
     "description": "SVG / HTML radar visualizations of a score_job component breakdown.",
     "actions": [
         _a("svg", "Radar SVG for one match.score_job result.",
            _h_radar_svg, [_p("score", "object", True, help="Output of match.score."),
                                      _p("title", "string"), _p("size", "integer", default=400),
                                      _p("color", "string", default="#ffb000")]),
         _a("compare", "Overlay radar SVG comparing up to 20 scored results.",
            _h_radar_compare, [_p("items", "array", True, help="[{name, components}] list."),
                                          _p("title", "string", default="Fit comparison")]),
         _a("html", "Standalone HTML radar comparison page.",
            _h_radar_html, [_p("items", "array", True, help="[{name, components}] list."),
                                       _p("title", "string", default="Veto fit radar")]),
     ]},
    {"id": "jd_decoder", "group": "FIND", "name": "JD decoder",
     "description": "Reads a job description and flags red/green flags, vagueness, and overwork signals.",
     "actions": [
         _a("decode", "Full structured decode of a job description.",
            _h_jd_decode, [_p("text", "string", True, help="Job description text.")]),
         _a("verdict", "Short verdict: apply / caution / skip with reasons.",
            _h_jd_verdict, [_p("text", "string", True, help="Job description text.")]),
     ]},
    {"id": "referrals", "group": "FIND", "name": "Referral finder",
     "description": "Ranks your connections as referral prospects for target companies and drafts outreach.",
     "actions": [
         _a("find", "Find referral prospects for a company from your connections.",
            _h_referrals_find, [_p("company", "string", help="Company name filter."),
                                               _p("limit", "integer", default=10)]),
         _a("rank", "Rank connections against target companies.",
            _h_referrals_rank, [_p("connections", "array", True, help="Connection dicts."),
                                              _p("targets", "array", True, help="Company names."),
                                              _profile_param()]),
         _a("outreach", "Draft a referral request message for a connection.",
            _h_referrals_outreach, [_p("contact", "object", True),
                                                   _p("job", "object"),
                                                   _profile_param(),
                                                   _p("kind", "string", default="warm", help="'warm' or 'cold'.")]),
         _a("targets", "Target companies derived from watches + applications.",
            _h_referrals_targets, []),
     ]},
    # ---------------- TAILOR ----------------
    {"id": "tailor", "group": "TAILOR", "name": "Resume tailor",
     "description": "Rewrites resume bullets around a job's keywords; keeps a library of approved variants.",
     "actions": [
         _a("resume", "Tailored resume markdown for a job.",
            _h_tailor_resume, [_profile_param(), _p("job", "object", True)]),
         _a("diff", "Tailored resume plus a diff against the base resume.",
            _h_tailor_diff, [_profile_param(), _p("job", "object", True)]),
         _a("keywords", "Keywords extracted from a job, split by matched/missing.",
            _h_tailor_keywords, [_profile_param(), _p("job", "object", True)]),
         _a("variants", "List saved approved resume variants.",
            _h_tailor_variants, []),
         _a("variant", "Load one approved resume variant.",
            _h_tailor_variant, [_p("job_id", "string", True)]),
     ]},
    {"id": "cover_letters", "group": "TAILOR", "name": "Cover letters",
     "description": "Drafts letters from profile evidence only; the honesty scan flags invented claims.",
     "actions": [
         _a("draft", "Draft a cover letter from profile evidence.",
            _h_cover_draft, [_profile_param(), _p("job", "object", True)]),
         _a("honesty_scan", "Flag claims in a letter that are not backed by the profile.",
            _h_cover_honesty, [_p("letter", "string", True), _profile_param(),
                                          _p("job", "object")]),
         _a("approve", "Save an approved letter for a job.",
            _h_cover_approve, [_p("job_id", "string", True), _p("letter", "string", True)]),
         _a("letters", "List approved cover letters.",
            _h_cover_list, []),
     ]},
    {"id": "linkedin_optimizer", "group": "TAILOR", "name": "LinkedIn optimizer",
     "description": "Scores headline, about, bullets, and skills; suggests rewrites for a target role.",
     "actions": [
         _a("audit", "Score every profile section with fix suggestions.",
            _h_linkedin_audit, [_profile_param(), _p("target_role", "string")]),
         _a("headline", "Rewrite the headline for a target role.",
            _h_linkedin_headline, [_profile_param(), _p("target_role", "string")]),
         _a("about", "Rewrite the about section.",
            _h_linkedin_about, [_profile_param()]),
         _a("keyword_gap", "Keywords missing from the profile for a target role.",
            _h_linkedin_keyword_gap, [_profile_param(), _p("target_role", "string")]),
     ]},
    # ---------------- TRAIN ----------------
    {"id": "mock_interview", "group": "TRAIN", "name": "Mock interview",
     "description": "Deterministic 5-question mock interviews with STAR-scored answers. Chat channel is non-interactive.",
     "actions": [
         _a("start", "Start a session and get the first question.",
            _h_mock_start, [_p("company", "string", True), _p("role", "string", True),
                                       _profile_param(),
                                       _p("channel", "string", default="chat", help="'chat' or 'whatsapp'."),
                                       _p("job_id", "string", help="Reuse questions from an interview brief.")]),
         _a("answer", "Submit an answer; get scored feedback and the next question.",
            _h_mock_answer, [_p("session_id", "string", True), _p("answer", "string", True)]),
         _a("summary", "Final scorecard and tips for a session.",
            _h_mock_summary, [_p("session_id", "string", True)]),
     ]},
    {"id": "soft_skills", "group": "TRAIN", "name": "Soft-skills drills",
     "description": "Scenario assessments, coaching drills, and a salary-negotiation simulator.",
     "actions": [
         _a("assess", "Score answers for a skill area.",
            _h_soft_assess, [_p("area", "string", True), _p("answers", "array", True)]),
         _a("drill", "Start a coaching drill scenario.",
            _h_soft_drill, [_p("area", "string", True), _profile_param(),
                                       _p("mode", "string", default="coach"),
                                       _p("difficulty", "string", default="firm")]),
         _a("review", "Get coached feedback on a drill answer.",
            _h_soft_review, [_p("session_id", "string", True), _p("answer", "string", True)]),
         _a("negotiate", "Run a salary-negotiation simulation.",
            _h_soft_negotiate, [_p("current_offer", "number", True), _p("target", "number", True),
                                              _profile_param(), _p("difficulty", "string", default="firm")]),
     ]},
    {"id": "ai_proficiency", "group": "TRAIN", "name": "AI proficiency",
     "description": "Lesson tracks, graded exercises, diagnostics, and progress tracking.",
     "actions": [
         _a("tracks", "List available lesson tracks.", _h_ai_tracks, []),
         _a("plan", "Learning plan for a track and level.",
            _h_ai_plan, [_p("track", "string", True), _p("level", "string")]),
         _a("lesson", "Fetch a lesson's content.",
            _h_ai_lesson, [_p("track", "string", True), _p("lesson_id", "string", True)]),
         _a("exercise", "Start a graded exercise (returns a session_id).",
            _h_ai_exercise, [_p("track", "string", True), _p("lesson_id", "string", True)]),
         _a("submit", "Submit an exercise response for grading.",
            _h_ai_submit, [_p("session_id", "string", True), _p("response", "string", True)]),
         _a("progress", "Overall progress and streaks.", _h_ai_progress, []),
         _a("diagnose", "Diagnose a level from quiz answers.",
            _h_ai_diagnose, [_p("track", "string", True), _p("answers", "array", True)]),
     ]},
    {"id": "mentors", "group": "TRAIN", "name": "Mentor matchmaking",
     "description": "Opt in as a mentor, get matched, draft outreach, prep for topics.",
     "actions": [
         _a("matchmake", "Match mentors to mentee answers.",
            _h_mentors_matchmake, [_p("answers", "object", True, help="Goal, role, topics, availability answers.")]),
         _a("outreach", "Draft a connection request to a mentor.",
            _h_mentors_outreach, [_p("mentor_id", "string", True),
                                                 _p("mentee_name", "string", True),
                                                 _p("mentee_goal", "string", True)]),
         _a("prep", "Prep notes for a mentorship topic.",
            _h_mentors_prep, [_p("topic", "string", True)]),
         _a("suggest", "Suggest mentors based on your training weak areas.",
            _h_mentors_suggest, []),
         _a("opt_in", "Publish your own mentor card.",
            _h_mentors_opt_in, [_p("profile", "object", True, help="Mentor profile card fields.")]),
         _a("opt_out", "Remove your mentor card.",
            _h_mentors_opt_out, [_p("mentor_id", "string")]),
         _a("card", "View or update your mentor card.",
            _h_mentors_card, [_p("updates", "object")]),
         _a("record_outreach", "Record that you reached out to a mentor.",
            _h_mentors_record_outreach, [_p("mentor_id", "string", True)]),
     ]},
    {"id": "skill_gaps", "group": "TRAIN", "name": "Skill-gap analyzer",
     "description": "Compares profile skills against target jobs and builds a learning plan.",
     "actions": [
         _a("analyze", "Find gaps between your profile and target jobs.",
            _h_gaps_analyze, [_profile_param(), _p("jobs", "array", help="Job dicts; defaults to watched targets.")]),
         _a("plan", "Learning plan for the recorded gaps.", _h_gaps_plan, []),
         _a("mark_progress", "Update progress on a gap skill.",
            _h_gaps_mark, [_p("skill", "string", True), _p("status", "string", True),
                                      _p("evidence", "string")]),
     ]},
    # ---------------- WIN ----------------
    {"id": "followup", "group": "WIN", "name": "Follow-up emails",
     "description": "Drafts follow-up emails from application history. Sending email requires a two-step confirmation.",
     "actions": [
         _a("draft", "Draft a follow-up for one application entry.",
            _h_followup_draft, [_p("entry", "object", True, help="Application entry dict."),
                                               _profile_param()]),
         _a("drafts", "All due follow-ups with drafts.",
            _h_followup_drafts, [_profile_param()]),
         _a("send", "Send a follow-up email. CONFIRM-GATED: first call returns a preview + hash; re-call with confirmed=true and the same hash.",
            _h_followup_draft,  # placeholder; dispatch uses GATED entry
            [_p("entry_id", "string", True), _p("to", "string", True),
             _p("subject", "string", True), _p("body", "string", True),
             _p("confirmed", "boolean"), _p("preview_hash", "string")]),
     ]},
    {"id": "network_crm", "group": "WIN", "name": "Network CRM",
     "description": "Local contact list with interaction logging, nudge lists, and warm paths to companies.",
     "actions": [
         _a("add", "Add a contact.",
            _h_crm_add, [_p("name", "string", True), _p("company", "string", True),
                                    _p("role", "string"), _p("industry", "string"),
                                    _p("linkedin_url", "string"), _p("source", "string"),
                                    _p("notes", "string")]),
         _a("list", "List all contacts.", _h_crm_list, []),
         _a("log", "Log an interaction with a contact.",
            _h_crm_log, [_p("contact_id", "string", True), _p("kind", "string", True),
                                    _p("summary", "string", True), _p("due", "string", help="ISO date for the next nudge.")]),
         _a("nudges", "Contacts with overdue follow-ups.", _h_crm_nudges, []),
         _a("warm_path", "Find the warmest path to someone at a company.",
            _h_crm_warm_path, [_p("company", "string", True)]),
     ]},
    {"id": "offer_compare", "group": "WIN", "name": "Offer comparison",
     "description": "4-year total-comp math, weighted offer ranking, and per-offer reports.",
     "actions": [
         _a("add", "Record an offer.",
            _h_offer_add, [_p("name", "string", True), _p("base", "number", True),
                                      _p("bonus", "number", default=0), _p("equity_total", "number", default=0),
                                      _p("equity_years", "number", default=4),
                                      _p("benefits_value", "number", default=0),
                                      _p("pto_days", "number", default=15),
                                      _p("remote", "string", default="onsite"),
                                      _p("location", "string"), _p("growth_score", "number", default=5),
                                      _p("notes", "string")]),
         _a("list", "List all recorded offers.", _h_offer_list, []),
         _a("report", "Full report for one offer.",
            _h_offer_report, [_p("offer_id", "string", True)]),
         _a("compare", "Rank offers by weighted score.",
            _h_offer_compare, [_p("weights", "object", help="Factor -> weight overrides.")]),
         _a("weights", "Current comparison weights.", _h_offer_weights, []),
         _a("set_weights", "Override comparison weights.",
            _h_offer_set_weights, [_p("overrides", "object", True)]),
     ]},
    {"id": "rejection_autopsy", "group": "WIN", "name": "Rejection autopsy",
     "description": "Records application outcomes and diagnoses where your funnel leaks.",
     "actions": [
         _a("record", "Record an outcome for an application.",
            _h_autopsy_record, [_p("job_id", "string", True), _p("outcome", "string", True),
                                               _p("stage", "string", True), _p("notes", "string"),
                                               _p("applied_at", "string")]),
         _a("autopsy", "Aggregate outcome stats.", _h_autopsy_run, []),
         _a("diagnose", "Pattern diagnosis with suggestions.", _h_autopsy_diagnose, []),
     ]},
    {"id": "streaks", "group": "WIN", "name": "Streaks & reps",
     "description": "Daily rep logging, current/longest streaks, goals, and weekly recaps.",
     "actions": [
         _a("log", "Log a rep of a kind (e.g. 'applications', 'outreach').",
            _h_streaks_log, [_p("kind", "string", True)]),
         _a("streaks", "Current and longest streaks.", _h_streaks_view, []),
         _a("set_goal", "Set a daily target for a rep kind.",
            _h_streaks_set_goal, [_p("kind", "string", True), _p("daily_target", "integer", True)]),
         _a("goals", "All daily goals.", _h_streaks_goals, []),
         _a("today", "Today's progress vs goals.", _h_streaks_today, []),
         _a("weekly", "Weekly recap.", _h_streaks_weekly, []),
         _a("card", "Shareable streak card.", _h_streaks_card, []),
     ]},
    # ---------------- GOVERN ----------------
    {"id": "contribute", "group": "GOVERN", "name": "Training-data contributions",
     "description": "Preview, scrub, and stage anonymized training sessions for maintainers. Never transmits anything.",
     "actions": [
         _a("preview", "Build the exact bundle that would be staged; nothing is sent.",
            _h_contrib_preview, [_p("session_ids", "array", True)]),
         _a("submit", "Stage the bundle to the local outbox. CONFIRM-GATED: preview first, then re-call with confirmed=true and the preview_hash.",
            _h_contrib_preview,  # placeholder; dispatch uses GATED entry
            [_p("session_ids", "array", True), _p("confirmed", "boolean"),
             _p("preview_hash", "string")]),
         _a("scrub_rules", "PII scrubbing rules applied to bundles.",
            _h_contrib_scrub, []),
         _a("toggle", "Enable or disable contributions (kill-switch).",
            _h_contrib_toggle, [_p("enabled", "boolean", True)]),
     ]},
    {"id": "crew", "group": "GOVERN", "name": "Agent crew",
     "description": "Specialist personas, red-team scans, and compliance screening.",
     "actions": [
         _a("run", "Run a specialist persona on a task.",
            _h_crew_run, [_p("persona_id", "string", True), _p("task", "string", True),
                                     _p("context", "object")]),
         _a("plan", "CEO persona breaks a goal into tasks.",
            _h_crew_plan, [_p("goal", "string", True)]),
         _a("status", "Crew roster and availability.", _h_crew_status, []),
         _a("red_team", "Red-team scan of a text.",
            _h_crew_red_team, [_p("text", "string", True)]),
         _a("compliance", "Compliance screen of a task.",
            _h_crew_compliance, [_p("task", "string", True)]),
     ]},
    # ---------------- CORE ----------------
    {"id": "search", "group": "CORE", "name": "Job search",
     "description": "Search job boards, fetch posting details, track applications, record applications.",
     "actions": [
         _a("query", "Search jobs across boards.",
            _h_search_query, [_p("query", "string", True), _p("location", "string", True),
                                         _p("board", "string", default="all"),
                                         _p("limit", "integer", default=10),
                                         _p("remote_only", "boolean", default=False),
                                         _p("salary_min", "integer", default=0),
                                         _p("seniority", "string")]),
         _a("details", "Full details for a job id.",
            _h_search_details, [_p("job_id", "string", True)]),
         _a("boards", "Available job boards.", _h_search_boards, []),
         _a("track", "Tracked applications.", _h_search_track, []),
         _a("record_apply", "Record an application (dry-run preview first). CONFIRM-GATED: first call returns preview + hash; re-call with confirmed=true and the same hash.",
            _h_search_query,  # placeholder; dispatch uses GATED entry
            [_p("job_id", "string", True), _p("resume_path", "string", True),
             _p("cover_letter", "string"), _p("answers", "object"), _p("headless", "boolean", default=True),
             _p("confirmed", "boolean"), _p("preview_hash", "string")]),
     ]},
    {"id": "apply_queue", "group": "CORE", "name": "Apply queue",
     "description": "Local queue of jobs to apply to later.",
     "actions": [
         _a("add", "Add a job to the apply queue. CONFIRM-GATED.",
            _h_queue_list,  # placeholder; dispatch uses GATED entry
            [_p("job_id", "string", True), _p("scheduled_for", "string"),
             _p("confirmed", "boolean"), _p("preview_hash", "string")]),
         _a("list", "List queued jobs.", _h_queue_list, []),
         _a("remove", "Remove a job from the queue.",
            _h_queue_remove, [_p("job_id", "string", True)]),
     ]},
    {"id": "wizard", "group": "CORE", "name": "Profile wizard",
     "description": "Profile templates and LinkedIn-merge helpers.",
     "actions": [
         _a("blank", "Blank profile template.", _h_wizard_blank, []),
         _a("merge", "Merge a base profile with a LinkedIn export.",
            _h_wizard_merge, [_p("base", "object", True), _p("linkedin", "object", True)]),
     ]},
    {"id": "doctor", "group": "CORE", "name": "Doctor",
     "description": "Environment health checks: profile, compliance, sessions, boards.",
     "actions": [
         _a("run", "Run all checks.", _h_doctor_run, []),
         _a("profile", "Check the saved profile.", _h_doctor_profile, []),
     ]},
    {"id": "analytics", "group": "CORE", "name": "Analytics",
     "description": "Funnel stats, response rates, and stale-application reports.",
     "actions": [
         _a("report", "Full analytics report.",
            _h_analytics_report, [_p("stale_days", "integer", default=14)]),
         _a("funnel", "Funnel breakdown for a list of applications.",
            _h_analytics_funnel, [_p("applications", "array", True)]),
         _a("response_rate", "Response rate by board.",
            _h_analytics_response_rate, [_p("applications", "array", True)]),
         _a("stale", "Applications stale for N days.",
            _h_analytics_stale, [_p("applications", "array", True),
                                            _p("days", "integer", default=14)]),
     ]},
]

_ACTION_LOOKUP = {(t["id"], a["id"]): a for t in TOOLS for a in t["actions"]}

# ---------------------------------------------------------------------------
# /api/run dispatch
# ---------------------------------------------------------------------------

def _catalog_action(tool_id, action_id):
    """Public catalog entry for a tool/action (no handler internals)."""
    action = _ACTION_LOOKUP.get((tool_id, action_id))
    if action is None:
        return None
    return {"id": action["id"], "description": action["description"],
            "params": action["params"]}


def run_action(tool_id, action_id, params):
    """Dispatch one action. Returns a JSON-safe response dict."""
    params = dict(params or {})
    action = _ACTION_LOOKUP.get((tool_id, action_id))
    if action is None:
        return {"ok": False, "error": f"unknown tool/action: {tool_id}/{action_id}"}

    gate = GATED.get((tool_id, action_id))
    try:
        if gate is not None:
            canonical, preview_text = gate["preview"](params)
            expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            if params.get("confirmed") is True and params.get("preview_hash") == expected:
                data = gate["run"](params)
                return {"ok": True, "data": _clean(data)}
            if params.get("preview_hash") and params.get("preview_hash") != expected:
                payload = _preview_payload(preview_text)
                payload["ok"] = False
                payload["error"] = "preview mismatch — review the new preview"
                return payload
            return _preview_payload(preview_text)
        data = action["handler"](params)
        return {"ok": True, "data": _clean(data)}
    except _GateError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # never leak a traceback as a crash; log it
        print(f"[webui] {tool_id}/{action_id} failed: {exc}", file=sys.stderr)
        traceback.print_exc()
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


# ---------------------------------------------------------------------------
# /api/kpis
# ---------------------------------------------------------------------------

_KPI_KEYS = ["applications", "avg_fit", "streak_days", "interviews",
             "offers", "followups_due", "activity_30d", "funnel"]


def get_kpis():
    """Return dashboard KPIs; zeros + degraded flag if dashboard_data is absent."""
    try:
        import dashboard_data
        kpis = dashboard_data.compute_kpis(BASE_DIR)
        result = {k: kpis.get(k, 0) for k in _KPI_KEYS}
        result["degraded"] = False
        return _clean(result)
    except Exception as exc:
        print(f"[webui] dashboard_data unavailable: {exc}", file=sys.stderr)
        result = {k: ({} if k == "funnel" else 0) for k in _KPI_KEYS}
        result["degraded"] = True
        return result


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

class _Handler(BaseHTTPRequestHandler):
    server_version = "VetoWebUI/1.0"

    # -- helpers ---------------------------------------------------------
    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, path: Path):
        ctype, _ = mimetypes.guess_type(str(path))
        if ctype is None:
            ctype = "application/octet-stream"
        if ctype.startswith("text/") or ctype in (
                "application/javascript", "application/json", "image/svg+xml"):
            ctype += "; charset=utf-8"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):  # keep logs tidy
        sys.stderr.write(f"[webui] {self.address_string()} {fmt % args}\n")

    # -- routing ----------------------------------------------------------
    def do_GET(self):
        try:
            path = urlsplit(self.path).path
            if path == "/api/tools":
                tools = []
                for t in TOOLS:
                    tools.append({
                        "id": t["id"], "group": t["group"], "name": t["name"],
                        "description": t["description"],
                        "actions": [
                            {"id": a["id"], "description": a["description"],
                             "params": a["params"]}
                            for a in t["actions"]
                        ],
                    })
                return self._send_json({"tools": tools})
            if path == "/api/kpis":
                return self._send_json(get_kpis())
            if path in ("/api/run",):
                return self._send_json(
                    {"ok": False, "error": "use POST"}, status=405)
            return self._serve_static(path)
        except BrokenPipeError:
            pass
        except Exception as exc:
            self._send_json({"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                            status=500)

    def _serve_static(self, path):
        rel = unquote(path)
        if rel == "/" or rel == "":
            rel = "/index.html"
        rel = rel.lstrip("/")
        if not rel:
            rel = "index.html"
        target = (WEBUI_DIR / rel).resolve()
        try:
            target.relative_to(WEBUI_DIR.resolve())
        except ValueError:
            return self._send_json({"ok": False, "error": "forbidden"}, status=403)
        if target.is_file():
            return self._send_static(target)
        return self._send_json({"ok": False, "error": "not found"}, status=404)

    def do_POST(self):
        try:
            path = urlsplit(self.path).path
            if path != "/api/run":
                return self._send_json({"ok": False, "error": "not found"},
                                       status=404)
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                return self._send_json({"ok": False, "error": "bad request body"},
                                       status=400)
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return self._send_json({"ok": False, "error": "invalid JSON"},
                                       status=400)
            if not isinstance(body, dict):
                return self._send_json({"ok": False, "error": "expected a JSON object"},
                                       status=400)
            resp = run_action(body.get("tool"), body.get("action"),
                              body.get("params"))
            return self._send_json(resp)
        except BrokenPipeError:
            pass
        except Exception as exc:
            self._send_json({"ok": False, "error": f"{type(exc).__name__}: {exc}"},
                            status=500)

    # No directory listings, no PUT/DELETE.
    def do_PUT(self):
        self._send_json({"ok": False, "error": "method not allowed"}, status=405)

    def do_DELETE(self):
        self._send_json({"ok": False, "error": "method not allowed"}, status=405)


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def serve(port: int) -> _Server:
    server = _Server(("127.0.0.1", port), _Handler)
    return server


# ---------------------------------------------------------------------------
# Entry point for cli.py: cmd_serve(args) -> int
# ---------------------------------------------------------------------------

def cmd_serve(args) -> int:
    """Start the web UI server. Blocks until Ctrl-C."""
    port = getattr(args, "port", None) or os.environ.get("PORT") or DEFAULT_PORT
    try:
        port = int(port)
    except (TypeError, ValueError):
        print(f"error: invalid port {port!r}", file=sys.stderr)
        return 2
    server = serve(port)
    url = f"http://127.0.0.1:{server.server_address[1]}"
    print(f"Veto web UI: {url}")
    if not getattr(args, "no_browser", False):
        try:
            webbrowser.open(url)
        except Exception as exc:  # headless environments
            print(f"(could not open browser: {exc})", file=sys.stderr)
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down web UI server.")
    finally:
        server.server_close()
    return 0


def _main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Veto web UI server (stdlib only).")
    parser.add_argument("--port", type=int, default=None,
                        help=f"Port to bind (default {DEFAULT_PORT}; PORT env also works).")
    parser.add_argument("--no-browser", action="store_true",
                        help="Do not open the browser automatically.")
    args = parser.parse_args(argv)
    return cmd_serve(args)


if __name__ == "__main__":
    sys.exit(_main())
