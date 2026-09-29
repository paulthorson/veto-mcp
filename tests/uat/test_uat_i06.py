"""Automated UAT acceptance journey for Initiative 06 (Interview & skills lab).

User journey: "A job seeker runs mock interviews, gets scored against a
disclosed rubric, and watches real gaps close across sessions."

Everything runs against the REAL product surfaces — the CLI (``cli.main``
dispatch) where a CLI surface exists, and the real module API directly
for voice mode, which has no CLI — with every module's on-disk store
redirected into a per-test temp dir — the same isolation seams the
shipped E2E suite (tests/test_e2e_i06.py) uses. No network, no LLM,
deterministic. Synthetic fixtures only, labeled SYNTHETIC in the data.

Traceability: the repo carries roadmap epic text but NO per-story
acceptance criteria, so every assertion here traces to the epic text, the
i06 Proof of value, or the Q1 exit gate (named in EPIC_MAP). No
story-level criteria are invented.
"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import cli  # noqa: E402
import mock_interview  # noqa: E402
import soft_skills  # noqa: E402
import ai_proficiency  # noqa: E402
import skill_gaps  # noqa: E402
from initiatives.i06 import longitudinal as _long  # noqa: E402
from initiatives.i06 import rubric as _rubric  # noqa: E402
from initiatives.i06 import voice as _voice  # noqa: E402

from .harness import JourneyCase  # noqa: E402

SYNTHETIC_STRONG_ANSWER = (
    "SYNTHETIC answer - not a real person's experience. In 2023 our "
    "checkout API was timing out at peak traffic. My task as the backend "
    "lead was to cut p99 latency under 300ms before Black Friday. The "
    "action I took: I designed a Redis cache layer, I implemented request "
    "coalescing, and I led the rollout across three services. As a "
    "result, p99 latency dropped 62% and we saved $40k per month in "
    "infrastructure costs."
)

# SYNTHETIC lab answers - one per soft-skill scenario kind.
SYNTHETIC_LAB_ANSWERS = {
    "conflict": (
        "SYNTHETIC answer. From Sam's perspective, the Friday deadline is "
        "what matters most and a shortcut feels like the only way to hit "
        "it. I propose we ship the safe core Friday with you owning the "
        "shortcut as a follow-up Monday. How about we check progress "
        "together Thursday?"),
    "influence": (
        "SYNTHETIC answer. Dana, from your perspective the key priority "
        "this quarter is cutting operational cost. Fair point - last "
        "year's proposal failed because we ignored maintenance costs. "
        "This time is different because we ran a pilot and cut spend 15%. "
        "My ask is: will you approve a two-week pilot by Friday?"),
    "negotiation": (
        "SYNTHETIC answer. I'm looking for a two-feature scope because "
        "the team can credibly deliver two features in six weeks. In "
        "exchange for adding the third feature, we would need two more "
        "weeks. Who can own that decision by Thursday?"),
    "ambiguous_stakeholder": (
        "SYNTHETIC answer. Help me understand: when you say 'better', do "
        "you mean faster load times or a new layout? I'm assuming users "
        "struggle with finding reports. In scope for v1: navigation "
        "fixes. Phase two: visual redesign."),
}


# SYNTHETIC AI-lab responses for the engineer/evaluation exercise.
# The checker measures concept-group coverage (see
# initiatives/i06/ai_lab.py): the strong response addresses the
# considerations the disclosed "good looks like" names; the weak one
# addresses none. Strong scores 1.0 and passes; weak scores 0.0 and
# fails on the real checker.
SYNTHETIC_AI_LAB_STRONG_RESPONSE = (
    "SYNTHETIC response. I would measure accuracy with precision and "
    "recall on a held-out sample of 200 tickets, compare against a "
    "human baseline, track the hallucination rate to keep summaries "
    "grounded and faithful, and block launch if the error rate passes "
    "the launch gate threshold. I would also log every output for "
    "audit.")

SYNTHETIC_AI_LAB_WEAK_RESPONSE = (
    "SYNTHETIC weak response. This seems like a nice idea and I support "
    "it fully.")


def _run_cli_json(*argv: str) -> tuple[int, dict]:
    """Run the REAL in-process product CLI dispatch; return (rc, parsed JSON)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = cli.main(list(argv))
    return rc, json.loads(buf.getvalue())


class InterviewLabJourney(JourneyCase):
    """Initiative 06 acceptance journey: mock interviews to observed gaps."""

    EPIC_MAP = {
        "test_role_specific_simulations": (
            "E1", "Role-specific simulations", "Roadmap i06 E1 epic text"),
        "test_rubric_engine_disclosed": (
            "E2", "Rubric engine", "Roadmap i06 E2 epic text"),
        "test_longitudinal_practice": (
            "E3", "Longitudinal practice",
            "i06 Proof of value + Roadmap i06 E3 epic text + Q1 exit gate"),
        "test_soft_skill_lab": (
            "E4", "Soft-skill lab", "Roadmap i06 E4 epic text"),
        "test_ai_proficiency_lab": (
            "E5", "AI proficiency lab", "Roadmap i06 E5 epic text"),
        "test_voice_mode_text_default_privacy_gate": (
            "E6", "Optional voice mode", "Roadmap i06 E6 epic text"),
    }

    def setUp(self):
        super().setUp()
        t = self.workdir
        redirects = [
            (mock_interview, "SESSIONS_FILE", t / "mock_sessions.json"),
            (mock_interview, "_LONGITUDINAL_HISTORY_PATH", t / "i06_history.json"),
            (soft_skills, "SESSIONS_PATH", t / "soft_skill_sessions.json"),
            (soft_skills, "PROGRESS_PATH", t / "soft_skills.json"),
            (soft_skills, "_LAB_SESSIONS_PATH",
             t / "soft_skill_lab_sessions.json"),
            (soft_skills, "_LAB_LONGITUDINAL_HISTORY_PATH",
             t / "i06_history.json"),
            (ai_proficiency, "STORE_PATH", t / "ai_proficiency.json"),
            (ai_proficiency, "_LAB_LONGITUDINAL_HISTORY_PATH",
             t / "i06_history.json"),
            (skill_gaps, "STORE_PATH", t / "skill_gaps.json"),
            (skill_gaps, "_PRACTICE_HISTORY_PATH", t / "i06_history.json"),
            (skill_gaps, "_PRACTICE_FOCUS_PATH", t / "i06_focus.json"),
        ]
        for module, attr, path in redirects:
            p = mock.patch.object(module, attr, path)
            p.start()
            self.addCleanup(p.stop)
        self.history_path = t / "i06_history.json"

    # -- helpers ---------------------------------------------------------
    def cli_json(self, *argv: str) -> dict:
        rc, result = _run_cli_json(*argv)
        self.assertEqual(rc, 0, f"cli {' '.join(argv)} exited {rc}")
        return result

    def start_mock_session(self, mode: str) -> str:
        result = self.cli_json("mock-start", "SynthCorp", "Backend Engineer",
                               "--mode", mode, "--json")
        self.assertEqual(result["mode"], mode)
        self.assertTrue(result.get("mode_card", "").strip())
        return result["session_id"]

    def answer_five(self, session_id: str,
                    answer: str = SYNTHETIC_STRONG_ANSWER) -> dict:
        last = None
        for _ in range(5):
            last = self.cli_json("mock-answer", session_id, answer, "--json")
        self.assertTrue(last["complete"])
        return last

    # -- E1 --------------------------------------------------------------
    def test_role_specific_simulations(self):
        """Each interviewer mode produces a session with its own disclosed persona and rubric weights."""
        modes = ["recruiter", "hiring_manager", "peer", "executive",
                 "adversarial"]
        cards = {}
        for mode in modes:
            result = self.cli_json("mock-start", "SynthCorp",
                                   "Backend Engineer", "--mode", mode, "--json")
            self.assertEqual(result["mode"], mode,
                             f"{mode} mode not disclosed on the session")
            card = result.get("mode_card", "")
            self.assertTrue(card.strip(), f"{mode} has no persona card")
            # The session discloses whose seat the interviewer is in.
            self.assertTrue(result.get("first_question", {}).get("question"),
                            f"{mode} session has no first question")
            # Every mode's card discloses that mode's rubric weights - the
            # weights are shown on the card the interviewee reads before
            # the round, not hidden in the scorer.
            self.assertIn("Scoring weights", card,
                          f"{mode} card hides the scoring weights")
            for dim in _rubric.DIMENSIONS:
                self.assertIn(dim.replace("_", " "), card,
                              f"{mode} card hides the weight for {dim}")
            cards[mode] = card
        # Mode flavoring is real: every mode's card is distinct - each
        # interviewer seat has its own persona and weight profile.
        distinct = {cards[m] for m in modes}
        self.assertEqual(len(distinct), len(modes),
                         "two modes share an identical card - no mode "
                         "flavoring")

    # -- E2 --------------------------------------------------------------
    def test_rubric_engine_disclosed(self):
        """The rubric is disclosed before any scoring, and every question is scored against it."""
        # Rubric shown FIRST, before any session exists or any answer scored.
        rubric = self.cli_json("mock-rubric", "--json")
        self.assertIn("rubric", rubric)
        for dim in _rubric.DIMENSIONS:
            self.assertIn(dim, rubric["rubric"],
                          f"rubric hides dimension {dim}")
            self.assertIn("weight", rubric["rubric"][dim])
            self.assertTrue(rubric["rubric"][dim].get("how_scored", "").strip(),
                            f"dimension {dim} has no plain-words scoring rule")

        # Full session: every question scored on every disclosed dimension.
        session_id = self.start_mock_session("recruiter")
        self.answer_five(session_id)
        summary = self.cli_json("mock-summary", session_id, "--json")
        self.assertEqual(len(summary["per_question"]), 5,
                         "session does not ask 5 questions")
        self.assertIn("rubric_averages", summary)
        for dim in _rubric.DIMENSIONS:
            self.assertIn(dim, summary["rubric_averages"],
                          f"summary hides average for {dim}")
        # The persisted session holds per-question dimension scores.
        sessions = json.loads(
            mock_interview.SESSIONS_FILE.read_text(encoding="utf-8"))
        session = sessions[session_id]
        self.assertEqual(len(session["answers"]), 5)
        for entry in session["answers"].values():
            for dim in _rubric.DIMENSIONS:
                self.assertIn(dim, entry["rubric"]["dimension_scores"],
                              f"question not scored on {dim}")
        # Improvement tips are generic craft advice chosen from this
        # session's aggregate answer stats (STAR coverage, numbers used,
        # length, ownership) - they never quote or reference any single
        # answer.
        self.assertEqual(len(summary["top_tips"]), 2)
        self.assertTrue(all(isinstance(t, str) and t.strip()
                            for t in summary["top_tips"]))

    # -- E3 --------------------------------------------------------------
    def _seed_repeated_gap(self, dimension="trade_offs", scores=(55, 62)):
        for i, score in enumerate(scores):
            dims = {d: 80 for d in _rubric.DIMENSIONS}
            dims[dimension] = score
            _long.record_result(
                source="mock_interview",
                label=f"recruiter @ SynthCorp #{i}",
                dimension_scores=dims,
                overall=score,
                mode="recruiter",
                session_id=f"uat-seed-{i}",
                history_path=self.history_path,
            )

    def _seed_improved_sessions(self, dimension="trade_offs",
                                scores=(80, 85)):
        for i, score in enumerate(scores):
            dims = {d: 80 for d in _rubric.DIMENSIONS}
            dims[dimension] = score
            _long.record_result(
                source="mock_interview",
                label=f"recruiter @ SynthCorp drill #{i}",
                dimension_scores=dims,
                overall=score,
                mode="recruiter",
                session_id=f"uat-improved-{i}",
                history_path=self.history_path,
            )

    def test_longitudinal_practice(self):
        """A gap that repeats across sessions is flagged and the next drill names that observed gap."""
        # Nothing invented from thin air: with no history there are no gaps.
        observed_empty = self.cli_json("skill-gaps", "observe", "--json")
        self.assertEqual(observed_empty["gaps"], [])

        # Two practice sessions with the same recurring low dimension.
        self._seed_repeated_gap()
        observed = self.cli_json("skill-gaps", "observe", "--json")
        gap_dims = [g["dimension"] for g in observed["gaps"]]
        self.assertIn("trade_offs", gap_dims,
                      "repeated gap not detected across sessions")
        for gap in observed["gaps"]:
            self.assertEqual(gap["basis"], "observed",
                             "gap basis is not 'observed'")

        # Q1 exit gate: the recommendation names an observed gap, never an
        # invented weakness label.
        rec = self.cli_json("skill-gaps", "recommend", "--json")
        rec_text = json.dumps(rec)
        self.assertIn("trade_offs", rec_text,
                      "recommendation does not name the observed gap")
        # Falsifiable: every recommendation target must be an observed
        # gap dimension — the recommender may not invent weakness labels
        # outside the observed set.
        targets = rec.get("targets") or []
        self.assertTrue(targets, "recommendation must target at least one gap")
        for target in targets:
            self.assertIn(
                target["dimension"], gap_dims,
                f"recommendation targets unobserved dimension: {target}")
            self.assertEqual(
                target["basis"], "observed",
                f"recommendation target basis is not 'observed': {target}")

        # Gap-closure arc: the seeker drills the gap; two more sessions
        # score the dimension above threshold. The journey then watches
        # the flagged gap clear for real.
        self._seed_improved_sessions()
        observed_after = self.cli_json("skill-gaps", "observe", "--json")
        gap_dims_after = [g["dimension"] for g in observed_after["gaps"]]
        self.assertNotIn("trade_offs", gap_dims_after,
                         "flagged gap still present after improved sessions")

        # And `skill-gaps progress` trends the dimension "improving" now
        # that the scores moved from the 50s to the 80s.
        progress = self.cli_json("skill-gaps", "progress", "--json")
        by_dim = {d["dimension"]: d for d in progress["dimensions"]}
        self.assertIn("trade_offs", by_dim)
        self.assertEqual(by_dim["trade_offs"]["trend"], "improving",
                         "progress does not trend improving after real "
                         "score gains")
        self.assertGreaterEqual(by_dim["trade_offs"]["delta"], 5,
                                "progress delta does not reflect the gains")
        self.assertTrue(by_dim["trade_offs"]["meets_threshold"],
                        "latest session still below threshold")

    # -- E4 --------------------------------------------------------------
    def test_soft_skill_lab(self):
        """Each soft-skill scenario (conflict, influence, negotiation, ambiguous stakeholder) runs and is scored."""
        kinds = ["conflict", "influence", "negotiation", "ambiguous_stakeholder"]
        listed = self.cli_json("soft-skills", "--json", "lab-kinds")
        available = listed.get("kinds", []) if isinstance(listed, dict) else listed
        available = [k["kind"] if isinstance(k, dict) else k for k in available]
        for kind in kinds:
            self.assertIn(kind, available, f"scenario kind {kind} not offered")

        for kind in kinds:
            started = self.cli_json("soft-skills", "--json", "lab-start", kind)
            session_id = started["session_id"]
            # The scenario card is disclosed before the round is scored.
            self.assertTrue(started.get("card", "").strip(),
                            f"{kind} scenario card not disclosed")
            reviewed = self.cli_json("soft-skills", "--json", "lab-review",
                                     session_id, SYNTHETIC_LAB_ANSWERS[kind])
            self.assertIn("rubric", reviewed, f"{kind} round not scored")
            overall = reviewed["rubric"]["overall"]
            self.assertGreaterEqual(overall, 0)
            self.assertLessEqual(overall, 100)
            summary = self.cli_json("soft-skills", "--json", "lab-summary",
                                    session_id)
            self.assertTrue(summary.get("rounds"),
                            f"{kind} has no scored rounds")
            self.assertIn("rubric", summary["rounds"][0])

    # -- E5 --------------------------------------------------------------
    def test_ai_proficiency_lab(self):
        """The AI lab offers role-based exercises and evaluates a submitted response.

        The evaluation score is a FRACTION (0-1), not 0-100: concept
        groups addressed divided by concept groups total. The exercise
        feedback discloses the scale to the learner ("5/5 concept
        groups"), a strong response must outscore a weak one, and both
        the pass and the fail path are asserted with their feedback
        text - the journey is not blind to pass/fail. Three track x
        exercise combos are exercised: engineer/evaluation (in full)
        plus product/ethics and data/failure_analysis.
        """
        tracks = self.cli_json("ai-skills", "lab-tracks", "--json")
        track_list = tracks["tracks"] if isinstance(tracks, dict) else tracks
        by_name = {t.get("track", t.get("id")): t for t in track_list}
        self.assertIn("engineer", by_name, "no engineer role track")
        self.assertTrue(by_name["engineer"].get("exercise_types"),
                        "engineer track has no exercise types")

        # Main combo: engineer track, evaluation exercise.
        started = self.cli_json("ai-skills", "lab-exercise",
                                "--track", "engineer",
                                "--exercise-type", "evaluation", "--json")
        session_id = started["session_id"]
        self.assertTrue(started.get("brief", "").strip(),
                        "exercise brief not disclosed")
        self.assertTrue(started.get("task", "").strip(),
                        "exercise task not disclosed")

        strong = self.cli_json("ai-skills", "lab-submit",
                               "--session-id", session_id,
                               "--response", SYNTHETIC_AI_LAB_STRONG_RESPONSE,
                               "--json")
        # TRUE contract: the score is a 0-1 fraction, equal to
        # groups_hit / groups_total.
        self.assertIn("score", strong, "no evaluation ran")
        self.assertGreaterEqual(strong["score"], 0)
        self.assertLessEqual(strong["score"], 1)
        self.assertAlmostEqual(strong["score"],
                               strong["groups_hit"] / strong["groups_total"],
                               places=2)
        # The scale is disclosed to the learner: the feedback names the
        # fraction ("5/5 concept groups"), making the 0-1 score
        # interpretable.
        self.assertIn(f"{strong['groups_hit']}/{strong['groups_total']} "
                      "concept groups", strong["feedback"])
        # Pass path, asserted explicitly with its feedback text.
        self.assertTrue(strong["passed"])
        self.assertIn("Passed", strong["feedback"])

        # Weak response on a fresh session: the fail path, equally
        # explicit with its feedback text.
        started_weak = self.cli_json("ai-skills", "lab-exercise",
                                     "--track", "engineer",
                                     "--exercise-type", "evaluation", "--json")
        weak = self.cli_json("ai-skills", "lab-submit",
                             "--session-id", started_weak["session_id"],
                             "--response", SYNTHETIC_AI_LAB_WEAK_RESPONSE,
                             "--json")
        self.assertFalse(weak["passed"])
        self.assertIn("Not quite", weak["feedback"])
        self.assertIn(f"{weak['groups_hit']}/{weak['groups_total']} "
                      "concept groups", weak["feedback"])
        self.assertIn("Needs >=", weak["feedback"])

        # Discrimination: the strong response must outscore the weak one -
        # the evaluator is not a coin flip.
        self.assertGreater(strong["score"], weak["score"],
                           "strong response did not outscore the weak one")

        # Two more track x exercise combos (different tracks AND
        # different exercise types) run under the same disclosed contract.
        for track, exercise_type in (("product", "ethics"),
                                     ("data", "failure_analysis")):
            combo = self.cli_json("ai-skills", "lab-exercise",
                                  "--track", track,
                                  "--exercise-type", exercise_type, "--json")
            self.assertEqual(combo["track"], track)
            self.assertEqual(combo["exercise_type"], exercise_type)
            self.assertTrue(combo.get("brief", "").strip(),
                            f"{track}/{exercise_type} brief not disclosed")
            submitted = self.cli_json(
                "ai-skills", "lab-submit",
                "--session-id", combo["session_id"],
                "--response", SYNTHETIC_AI_LAB_WEAK_RESPONSE, "--json")
            self.assertGreaterEqual(submitted["score"], 0)
            self.assertLessEqual(submitted["score"], 1)
            self.assertAlmostEqual(
                submitted["score"],
                submitted["groups_hit"] / submitted["groups_total"],
                places=2)
            self.assertIn("concept groups", submitted["feedback"])

    # -- E6 --------------------------------------------------------------
    def test_voice_mode_text_default_privacy_gate(self):
        """Voice stays off by default and any connected voice path needs a clear privacy choice first."""
        _voice.reset()
        self.addCleanup(_voice.reset)

        # Text is the default; nothing voice-related is active.
        status = _voice.describe_status()
        self.assertEqual(status["mode"], "disabled")
        self.assertEqual(status["default_modality"], "text")
        self.assertFalse(status["transcription_allowed"])

        # The privacy gate is fail-closed: no consent, no transcription.
        with self.assertRaises(_voice.VoiceBlocked):
            _voice.transcribe("fake-audio")
        with self.assertRaises(_voice.VoiceBlocked):
            _voice.grant_consent()

        # A connected path requires disclosure first, then an explicit
        # yes from the user - disclosure alone must not enable it.
        disclosure = _voice.propose_connected(
            "SYNTHETIC-STT", lambda a: "hello", "audio kept 30 days")
        self.assertEqual(disclosure["service_name"], "SYNTHETIC-STT")
        self.assertIsNotNone(_voice.get_pending_disclosure())
        with self.assertRaises(_voice.VoiceBlocked):
            _voice.transcribe("fake-audio")
        _voice.grant_consent()
        result = _voice.transcribe("fake-audio")
        self.assertEqual(result["transcript"], "hello")
        self.assertEqual(result["mode"], "connected")


if __name__ == "__main__":
    unittest.main()
