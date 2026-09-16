"""End-to-end retro-validation for Initiative 06 (Interview & skills lab).

Exercised against REAL surfaces:
  - the product CLI (``cli.main`` dispatch — real argparse plugin wiring),
  - real on-disk session stores (every module's store redirected to a tmp
    dir per test; nothing touches the repo tree or the real user data dir),
  - the longitudinal practice history (redirected per module through each
    module's documented test seam),
  - the voice privacy module's fail-closed contract.

Hermetic: no network, no LLM, deterministic. Every test PASSES or it is a
real regression — these are ship-gate tests, not sketches.

Note: this module deliberately does NOT set XDG_DATA_HOME process-wide.
The longitudinal history is redirected per-module via each module's test
seam (_LONGITUDINAL_HISTORY_PATH / _PRACTICE_HISTORY_PATH /
_LAB_LONGITUDINAL_HISTORY_PATH), which keeps these tests composable with
the rest of the suite (a process-global XDG override broke
test_i07_warm_path's outbox-location assertion when run together).
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# --- Hermeticity -------------------------------------------------------------
# (No process-global env changes: each module's longitudinal-history seam
# is redirected per test in E2EBase.setUp below.)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import ai_proficiency  # noqa: E402
import cli  # noqa: E402
import grill  # noqa: E402
import mock_interview  # noqa: E402
import skill_gaps  # noqa: E402
import soft_skills  # noqa: E402
from initiatives.i06 import longitudinal as _long  # noqa: E402
from initiatives.i06 import modes as _modes  # noqa: E402
from initiatives.i06 import rubric as _rubric  # noqa: E402
from initiatives.i06 import voice as _voice  # noqa: E402

STRONG_ANSWER = (
    "In 2023 the situation was dire: our checkout API was timing out at "
    "peak traffic and the on-call context was brutal. My task as the "
    "backend lead was to cut p99 latency under 300ms before Black Friday. "
    "The action I took: I designed a Redis cache layer, I implemented "
    "request coalescing, and I led the rollout across three services. As "
    "a result, p99 latency dropped 62% and we saved $40k per month in "
    "infrastructure costs."
)


def run_cli(*argv: str) -> tuple[int, str]:
    """Run the REAL product CLI dispatch; return (exit_code, stdout text)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli.main(list(argv))
    return rc, buf.getvalue()


def run_cli_json(*argv: str) -> tuple[int, dict]:
    rc, out = run_cli(*argv, "--json")
    assert rc == 0, f"CLI {' '.join(argv)} exited {rc}: {out[-800:]}"
    return rc, json.loads(out)


class E2EBase(unittest.TestCase):
    """Redirect every i06 module's on-disk store into a tmp dir."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        t = Path(self._tmp.name)
        self._patches = []
        redirects = [
            (mock_interview, "SESSIONS_FILE", t / "mock_sessions.json"),
            (mock_interview, "_LONGITUDINAL_HISTORY_PATH", t / "i06_history.json"),
            (grill, "SESSIONS_FILE", t / "grill_sessions.json"),
            (soft_skills, "SESSIONS_PATH", t / "soft_skill_sessions.json"),
            (soft_skills, "PROGRESS_PATH", t / "soft_skills.json"),
            (soft_skills, "_LAB_SESSIONS_PATH",
             t / "soft_skill_lab_sessions.json"),
            (soft_skills, "_LAB_LONGITUDINAL_HISTORY_PATH",
             t / "i06_history.json"),
            (ai_proficiency, "STORE_PATH", t / "ai_proficiency.json"),
            (ai_proficiency, "_LAB_LONGITUDINAL_HISTORY_PATH", t / "i06_history.json"),
            (skill_gaps, "STORE_PATH", t / "skill_gaps.json"),
            (skill_gaps, "_PRACTICE_HISTORY_PATH", t / "i06_history.json"),
            (skill_gaps, "_PRACTICE_FOCUS_PATH", t / "i06_focus.json"),
        ]
        for module, attr, path in redirects:
            p = mock.patch.object(module, attr, path)
            p.start()
            self._patches.append(p)
            self.addCleanup(p.stop)
        self.history_path = t / "i06_history.json"

    # -- helpers -------------------------------------------------------------
    def start_session(self, company="Initech", role="Backend Engineer",
                      mode="recruiter") -> str:
        _, result = run_cli_json("mock-start", company, role, "--mode", mode)
        self.assertIn("session_id", result)
        self.assertEqual(result["mode"], mode)
        # The mode must be disclosed BEFORE the round starts.
        self.assertIn("mode_card", result)
        self.assertIsInstance(result["mode_card"], str)
        self.assertTrue(result["mode_card"].strip())
        self.assertIn("first_question", result)
        self.assertTrue(result["first_question"]["question"])
        return result["session_id"]

    def answer_all_five(self, session_id, answers=None):
        answers = answers or [STRONG_ANSWER] * 5
        last = None
        for i, text in enumerate(answers):
            _, result = run_cli_json("mock-answer", session_id, text)
            self.assertEqual(result["answered"], i + 1)
            self.assertIn("overall", result)
            self.assertIn("rubric", result)
            dims = result["rubric"]["dimension_scores"]
            for dim in _rubric.DIMENSIONS:
                self.assertIn(dim, dims)
            last = result
        self.assertTrue(last["complete"])
        return last


class TestMockInterviewE2E(E2EBase):
    """Full 5-question mock interview through the real product CLI."""

    def test_full_session_via_cli(self):
        session_id = self.start_session()
        self.answer_all_five(session_id)

        _, summary = run_cli_json("mock-summary", session_id)
        self.assertEqual(len(summary["per_question"]), 5)
        self.assertIn("overall_score", summary)
        self.assertGreaterEqual(summary["overall_score"], 0)
        self.assertLessEqual(summary["overall_score"], 100)
        # Rubric aggregation is disclosed in the summary.
        self.assertIn("rubric_averages", summary)
        for dim in _rubric.DIMENSIONS:
            self.assertIn(dim, summary["rubric_averages"])
        self.assertEqual(len(summary["top_tips"]), 2)
        # Tips must reference the answers, never invent facts.
        self.assertTrue(all(isinstance(t, str) and t
                            for t in summary["top_tips"]))

        # Real persistence: the session file on disk holds all five answers.
        sessions = json.loads(
            mock_interview.SESSIONS_FILE.read_text(encoding="utf-8"))
        session = sessions[session_id]
        self.assertTrue(session["complete"])
        self.assertEqual(len(session["answers"]), 5)
        for entry in session["answers"].values():
            self.assertEqual(entry["answer"], STRONG_ANSWER)
            self.assertIn("rubric", entry)
            self.assertIn("overall", entry)

        # Longitudinal history: the completed session is recorded for the
        # observed-gap engine, with the disclosed mode and company label.
        history = json.loads(self.history_path.read_text(encoding="utf-8"))
        entries = [e for e in history if e.get("source") == "mock_interview"]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["mode"], "recruiter")
        self.assertIn("Initech", entry["label"])
        self.assertIn("structure", entry["dimension_scores"])

    def test_rubric_disclosed_via_cli(self):
        _, result = run_cli_json("mock-rubric")
        self.assertIn("rubric", result)
        for dim in _rubric.DIMENSIONS:
            self.assertIn(dim, result["rubric"])
            self.assertIn("weight", result["rubric"][dim])
            self.assertIn("how_scored", result["rubric"][dim])
        modes = result["modes"]
        for mode in _modes.MODES:
            self.assertIn(mode, modes)
            self.assertTrue(modes[mode].get("persona"))
            weights = modes[mode]["weights"]
            self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)

    def test_weak_answer_scores_lower_and_still_completes(self):
        session_id = self.start_session(mode="peer")
        weak = "We did stuff and it was fine I guess."
        last = self.answer_all_five(session_id, answers=[weak] * 5)
        _, summary = run_cli_json("mock-summary", session_id)
        strong_session = self.start_session(mode="peer")
        self.answer_all_five(strong_session)
        _, strong_summary = run_cli_json("mock-summary", strong_session)
        self.assertLess(summary["overall_score"], strong_summary["overall_score"])
        self.assertTrue(last["complete"])


class TestSoftSkillsLabE2E(E2EBase):
    """Soft-skills lab scenario through the real product CLI."""

    def ss_json(self, *args):
        rc, out = run_cli("soft-skills", "--json", *args)
        self.assertEqual(rc, 0, out[-800:])
        return json.loads(out)

    def test_lab_scenario_via_cli(self):
        kinds = self.ss_json("lab-kinds")
        if isinstance(kinds, dict):
            kinds = kinds.get("kinds", [])
        kind_list = [k["kind"] if isinstance(k, dict) else k for k in kinds]
        self.assertIn("conflict", kind_list)

        started = self.ss_json("lab-start", "conflict")
        session_id = started["session_id"]
        self.assertIn("card", started)
        self.assertIn("prompt", started)
        self.assertEqual(started["kind"], "conflict")

        answer = (
            "I see we disagree on the launch date. My priority is hitting "
            "the commitment we made to the customer, and I want to "
            "understand what is blocking your team. Can we walk through "
            "the risks together and find a date we both trust?")
        reviewed = self.ss_json("lab-review", session_id, answer)
        self.assertIn("rubric", reviewed)
        self.assertIn("overall", reviewed["rubric"])
        self.assertGreaterEqual(reviewed["rubric"]["overall"], 0)
        self.assertIn("signals", reviewed)
        self.assertIn("feedback", reviewed)

        summary = self.ss_json("lab-summary", session_id)
        self.assertEqual(len(summary["rounds"]), 1)
        self.assertIn("overall", summary["rounds"][0]["rubric"])

        # Real persistence: the lab session file holds the scored round.
        lab_path = soft_skills._LAB_SESSIONS_PATH
        sessions = json.loads(lab_path.read_text(encoding="utf-8"))
        self.assertIn(session_id, sessions)
        self.assertEqual(len(sessions[session_id]["results"]), 1)
        self.assertEqual(sessions[session_id]["results"][0]["answer"], answer)


class TestSkillGapsE2E(E2EBase):
    """skill-gaps flow through the real product CLI.

    The observed-gap engine only ever recommends from OBSERVED practice
    history (or explicit user selection) — never invented weaknesses.
    """

    def _seed_history_with_gap(self, dimension="trade_offs",
                               scores=(55, 62, 70)):
        for i, score in enumerate(scores):
            dims = {d: 80 for d in _rubric.DIMENSIONS}
            dims[dimension] = score
            _long.record_result(
                source="mock_interview",
                label=f"recruiter @ SeedCorp #{i}",
                dimension_scores=dims,
                overall=score,
                mode="recruiter",
                session_id=f"seed-{i}",
                history_path=self.history_path,
            )

    def test_analyze_plan_observe_recommend_via_cli(self):
        t = Path(self._tmp.name)
        jobs_path = t / "jobs.json"
        profile_path = t / "profile.json"
        jobs_path.write_text(json.dumps([
            {"job_id": "j1", "title": "Backend Engineer",
             "description": "Needs distributed systems, Kubernetes, and Go."},
        ]), encoding="utf-8")
        profile_path.write_text(json.dumps({
            "full_name": "Test Candidate",
            "experience": [{"title": "Backend Engineer", "company": "SeedCorp",
                            "start": "2020-01", "end": "",
                            "description": "Built APIs in Python."}],
        }), encoding="utf-8")

        _, analyzed = run_cli_json("skill-gaps", "analyze",
                                   "--jobs", str(jobs_path),
                                   "--profile", str(profile_path))
        self.assertIn("gaps", analyzed)

        _, planned = run_cli_json("skill-gaps", "plan")
        self.assertIn("plan", planned)

        # No observed gaps yet: history is empty, so observe is honest.
        _, observed_empty = run_cli_json("skill-gaps", "observe")
        self.assertEqual(observed_empty["gaps"], [])

        # Seed three completed sessions with a repeated low dimension.
        self._seed_history_with_gap()
        _, observed = run_cli_json("skill-gaps", "observe")
        gap_dims = [g["dimension"] for g in observed["gaps"]]
        self.assertIn("trade_offs", gap_dims)
        for gap in observed["gaps"]:
            self.assertEqual(gap["basis"], "observed")
        # Provisional rule values stay disclosed.
        self.assertTrue(observed["rule"]["pending_approval"])

        # recommend_next_drill draws ONLY from observed gaps.
        _, rec = run_cli_json("skill-gaps", "recommend")
        self.assertIn("trade_offs", rec.get("dimension", "") + json.dumps(rec))

        # Real persistence: the store holds the analyzed gaps.
        store = json.loads(skill_gaps.STORE_PATH.read_text(encoding="utf-8"))
        self.assertIn("gaps", store)


class TestAILabE2E(E2EBase):
    """AI-proficiency lab exercise through the real product CLI."""

    def test_lab_exercise_via_cli(self):
        _, tracks = run_cli_json("ai-skills", "lab-tracks")
        track_list = tracks["tracks"] if isinstance(tracks, dict) else tracks
        tracks_by_name = {t.get("track", t.get("id")): t for t in track_list}
        self.assertIn("engineer", tracks_by_name)
        self.assertIn("ethics", tracks_by_name["engineer"]["exercise_types"])

        _, started = run_cli_json("ai-skills", "lab-exercise",
                                  "--track", "engineer",
                                  "--exercise-type", "ethics")
        session_id = started["session_id"]
        self.assertIn("brief", started)
        self.assertIn("task", started)

        response = (
            "I would not deploy the model without an evaluation harness: "
            "I would measure precision and recall on a held-out set, check "
            "for disparate impact across user groups, add a human review "
            "step for high-stakes decisions, and log every automated "
            "decision so failures can be audited.")
        _, checked = run_cli_json("ai-skills", "lab-submit",
                                  "--session-id", session_id,
                                  "--response", response)
        self.assertIn("score", checked)
        self.assertIn("passed", checked)

        # Real persistence: the lab session is marked submitted in the store.
        store = json.loads(
            ai_proficiency.STORE_PATH.read_text(encoding="utf-8"))
        lab = store["lab_sessions"][session_id]
        self.assertTrue(lab["submitted"])
        self.assertEqual(lab["track"], "engineer")


class TestGrillE2E(E2EBase):
    """Per-application grilling through the real product CLI."""

    JOB = {"job_id": "job-e2e", "title": "Backend Engineer",
           "company": "Initech",
           "description": "Build and scale backend services."}
    PROFILE = {"full_name": "Test Candidate", "experience": []}

    def test_grill_session_via_cli(self):
        import server  # noqa: E402 — lazy by design in grill.py
        with mock.patch.object(server, "get_job_details",
                               lambda jid: dict(self.JOB, job_id=jid)), \
             mock.patch.object(server, "_load_saved_profile",
                               lambda: dict(self.PROFILE)):
            rc, out = run_cli("grill-start", "job-e2e", "--json")
        self.assertEqual(rc, 0, out[-800:])
        started = json.loads(out)
        session_id = started["session_id"]
        questions = started["questions"]
        self.assertTrue(questions)

        first = questions[0]
        _, answered = run_cli_json("grill-answer", "job-e2e",
                                   first["id"], "We shipped it on time.")
        self.assertEqual(answered["answered"], 1)

        _, status = run_cli_json("grill-status", "job-e2e")
        self.assertEqual(status["answered"], 1)
        self.assertEqual(status["total"], len(questions))

        # Real persistence: the grill session file holds the answer.
        sessions = json.loads(grill.SESSIONS_FILE.read_text(encoding="utf-8"))
        self.assertIn("job-e2e", sessions)
        self.assertIn(first["id"], sessions["job-e2e"]["answers"])
        self.assertEqual(sessions["job-e2e"]["session_id"], session_id)


class TestVoiceFailClosedE2E(unittest.TestCase):
    """Voice input is opt-in; every path fails closed without consent."""

    def setUp(self):
        _voice.reset()
        self.addCleanup(_voice.reset)

    def test_disabled_by_default(self):
        status = _voice.describe_status()
        self.assertEqual(status["mode"], "disabled")
        self.assertEqual(status["default_modality"], "text")
        self.assertFalse(status["transcription_allowed"])
        with self.assertRaises(_voice.VoiceBlocked):
            _voice.transcribe("fake-audio")

    def test_local_mode_needs_user_provider(self):
        with self.assertRaises(ValueError):
            _voice.enable_local(None)
        _voice.enable_local(lambda audio: "transcribed text")
        result = _voice.transcribe("fake-audio")
        self.assertEqual(result["transcript"], "transcribed text")
        self.assertEqual(result["mode"], "local")

    def test_connected_requires_disclosure_then_consent(self):
        with self.assertRaises(ValueError):
            _voice.propose_connected("", lambda a: "x", "kept 30 days")
        # No pending disclosure -> consent cannot be granted.
        with self.assertRaises(_voice.VoiceBlocked):
            _voice.grant_consent()
        disclosure = _voice.propose_connected(
            "my-stt-endpoint", lambda a: "hello world", "audio kept 30 days")
        self.assertEqual(disclosure["service_name"], "my-stt-endpoint")
        # Disclosure shown but consent not yet granted -> still blocked.
        self.assertIsNotNone(_voice.get_pending_disclosure())
        with self.assertRaises(_voice.VoiceBlocked):
            _voice.transcribe("fake-audio")
        _voice.grant_consent()
        result = _voice.transcribe("fake-audio")
        self.assertEqual(result["transcript"], "hello world")
        self.assertEqual(result["service_name"], "my-stt-endpoint")


class TestModesDisclosedE2E(unittest.TestCase):
    """Every interviewer mode publishes persona + rubric weights upfront."""

    def test_all_modes_publish_persona_and_weights(self):
        for mode in _modes.MODES:
            spec = _modes.MODES[mode]
            self.assertTrue(spec.get("persona"), mode)
            self.assertTrue(spec.get("round_shape"), mode)
            weights = _modes.mode_weights(mode)
            self.assertAlmostEqual(sum(weights.values()), 1.0, places=6,
                                   msg=mode)
            for dim in _rubric.DIMENSIONS:
                self.assertIn(dim, weights, f"{mode}/{dim}")
            # The disclosed card rendered for candidates names the mode.
            card = _modes.mode_card(mode)
            self.assertIsInstance(card, str)
            self.assertTrue(card.strip())

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            _modes.validate_mode("not-a-mode")


if __name__ == "__main__":
    unittest.main()
