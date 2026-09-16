#!/usr/bin/env python3
"""Tests for Initiative 09 epic 4: calendar handoff.

Test strategies used in this file:

Strategy 1 — contract-first happy-path. This strategy trades away
adversarial coverage to get fast, readable verification of the core
contract: drafts build, handoff requires confirm=True, missing times are
refused, and the manifest is complete. It asserts only documented
guarantees and would miss edge-case regressions.

Strategy 2 — adversarial edge-case fuzzing. This strategy trades away
speed and readability to get coverage of hostile or malformed inputs:
naive datetimes, unparseable dates, placeholder content, garbage inputs
to the handoff gate, and double-confirm deduping. It deliberately feeds
inputs the contract never promises to support, because this module sits
in front of a real calendar write.

Honesty notes: drafting is side-effect free EXCEPT that
confirm_and_handoff(confirm=True) emits a log.info line on success.
propose_followup_reminder anchors to datetime.now(timezone.utc) when no
from_date is given, so those drafts are time-dependent, not
deterministic — tests pin from_date explicitly wherever exact times
matter.
"""

import unittest

from initiatives.i09 import calendar_handoff
from initiatives.i09.calendar_handoff import (
    CALENDAR_MANIFEST,
    CalendarDraft,
    confirm_and_handoff,
    propose_followup_reminder,
    propose_interview_prep,
)


class _SimulatedHumanConfirmation:
    """Simulate a human approving the confirmation gate (test-only).

    Production invariant (see circuit_breaker.require_action_confirmation):
    ``confirm_and_handoff(confirm=True)`` does NOT authorize a handoff by
    itself — a human must type a per-call random confirmation value on an
    interactive terminal, and non-TTY callers fail closed with
    SystemExit(2). There is no TTY in tests, so every test class that
    exercises ``confirm=True`` inherits this mixin, which swaps the gate
    for a simulated human who always approves. The production gate is
    never touched; the refusal-to-test-without-a-TTY behavior is pinned
    separately in tests/test_calendar_handoff_confirm_gate.py.
    """

    def setUp(self):
        self._orig_gate = calendar_handoff.require_action_confirmation
        self._gate_calls = []

        def simulated_human(**kwargs):
            self._gate_calls.append(kwargs)
            return {
                "ok": True,
                "approved": True,
                "approval_id": "simulated-human-approval",
                "content_hash": kwargs.get("expected_value"),
                "channel": "simulated-human",
            }

        calendar_handoff.require_action_confirmation = simulated_human
        super().setUp()

    def tearDown(self):
        calendar_handoff.require_action_confirmation = self._orig_gate
        super().tearDown()


_APP = {"company": "Acme", "title": "Backend Engineer", "job_id": "gh:abc"}
_AWARE = "2026-10-01T14:00:00+00:00"


class DraftTests(_SimulatedHumanConfirmation, unittest.TestCase):
    def test_interview_prep_draft_with_time(self):
        draft = propose_interview_prep(_APP, interview_at=_AWARE)
        self.assertTrue(draft.has_time)
        self.assertEqual(draft.event_type, "interview_prep")
        # Prep starts 45 minutes before the interview.
        self.assertTrue(draft.start_iso < draft.end_iso)
        self.assertIn("Backend Engineer", draft.title)
        self.assertIn("Acme", draft.title)
        self.assertIn("checklist", draft.description.lower())

    def test_interview_prep_draft_without_time(self):
        draft = propose_interview_prep(_APP)
        self.assertFalse(draft.has_time)
        self.assertEqual(draft.start_iso, "")

    def test_followup_reminder_draft(self):
        draft = propose_followup_reminder(_APP, days_after=7,
                                          from_date="2026-09-13T00:00:00+00:00")
        self.assertTrue(draft.has_time)
        self.assertEqual(draft.event_type, "followup_reminder")
        self.assertIn("2026-09-20", draft.start_iso)

    def test_draft_has_no_attendees_by_default(self):
        draft = propose_interview_prep(_APP, interview_at=_AWARE)
        self.assertEqual(draft.attendees, [])
        self.assertFalse(draft.attendees_confirmed)

    def test_manifest_complete(self):
        self.assertEqual(CALENDAR_MANIFEST.validate(), [])


class RoundTripTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """B2: drafts survive serialization -> confirm without data loss."""

    def test_from_dict_round_trip(self):
        draft = propose_interview_prep(_APP, interview_at=_AWARE)
        rebuilt = CalendarDraft.from_dict(draft.to_dict())
        self.assertEqual(rebuilt.to_dict(), draft.to_dict())

    def test_from_dict_ignores_unknown_keys(self):
        data = propose_interview_prep(_APP, interview_at=_AWARE).to_dict()
        data["future_field"] = "ignored"
        rebuilt = CalendarDraft.from_dict(data)
        self.assertFalse(hasattr(rebuilt, "future_field"))

    def test_from_dict_rejects_non_dict(self):
        with self.assertRaises(TypeError):
            CalendarDraft.from_dict("not-a-dict")

    def test_handoff_accepts_dicts_when_confirming(self):
        draft = propose_interview_prep(_APP, interview_at=_AWARE)
        out = confirm_and_handoff(draft.to_dict(), confirm=True)
        self.assertTrue(out["ok"])
        self.assertEqual(out["handed_off"], 1)
        self.assertEqual(out["events"][0]["title"], draft.title)

    def test_handoff_accepts_dicts_without_confirm(self):
        draft = propose_interview_prep(_APP, interview_at=_AWARE)
        out = confirm_and_handoff(draft.to_dict())
        self.assertFalse(out["ok"])
        self.assertEqual(len(out["drafts"]), 1)

    def test_full_round_trip_draft_to_dict_to_confirm(self):
        draft = propose_interview_prep(_APP, interview_at=_AWARE)
        out = confirm_and_handoff(draft.to_dict(), confirm=True)
        self.assertTrue(out["ok"])
        event = out["events"][0]
        for key, value in draft.to_dict().items():
            self.assertEqual(event[key], value)


class HandoffGateTests(_SimulatedHumanConfirmation, unittest.TestCase):
    def _draft(self):
        return propose_interview_prep(_APP, interview_at=_AWARE)

    def test_handoff_refused_without_confirm(self):
        out = confirm_and_handoff(self._draft())
        self.assertFalse(out["ok"])
        self.assertEqual(out["handed_off"], 0)
        self.assertTrue(out["drafts"])  # drafts returned for review

    def test_handoff_confirmed(self):
        out = confirm_and_handoff(self._draft(), confirm=True)
        self.assertTrue(out["ok"])
        self.assertEqual(out["handed_off"], 1)
        self.assertIn("google-calendar", out["destination"])
        self.assertIn("title", out["data_sent_per_event"])
        self.assertIn("Wiring layer", out["note"])

    def test_missing_time_refused_even_with_confirm(self):
        draft = propose_interview_prep(_APP)  # no time
        out = confirm_and_handoff(draft, confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "missing_time")
        self.assertEqual(out["handed_off"], 0)

    def test_multiple_drafts(self):
        drafts = [
            self._draft(),
            propose_followup_reminder(_APP, from_date="2026-09-13T00:00:00+00:00"),
        ]
        out = confirm_and_handoff(drafts, confirm=True)
        self.assertTrue(out["ok"])
        self.assertEqual(out["handed_off"], 2)

    def test_zero_valid_drafts_is_not_success(self):
        # B3: an empty handoff must fail closed, not report ok:true.
        out = confirm_and_handoff([], confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["handed_off"], 0)
        self.assertEqual(out["error"], "no_valid_drafts")

    def test_garbage_inputs_are_dropped_and_reported(self):
        out = confirm_and_handoff(["junk", 42, None], confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "no_valid_drafts")
        self.assertIn("dropped", out["instructions"])


class AttendeeEnforcementTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """M1: attendees are never written without explicit per-draft consent."""

    def _draft_with_attendees(self, confirmed: bool) -> CalendarDraft:
        draft = propose_interview_prep(_APP, interview_at=_AWARE)
        draft.attendees = ["recruiter@example.com"]
        draft.attendees_confirmed = confirmed
        return draft

    def test_unconfirmed_attendees_are_stripped(self):
        out = confirm_and_handoff(
            self._draft_with_attendees(confirmed=False), confirm=True
        )
        self.assertTrue(out["ok"])
        event = out["events"][0]
        self.assertEqual(event["attendees"], [])
        self.assertTrue(event["attendees_stripped"])
        self.assertIn("Backend Engineer @ Acme", out["note"])

    def test_confirmed_attendees_are_kept(self):
        out = confirm_and_handoff(
            self._draft_with_attendees(confirmed=True), confirm=True
        )
        self.assertTrue(out["ok"])
        event = out["events"][0]
        self.assertEqual(event["attendees"], ["recruiter@example.com"])
        self.assertNotIn("attendees_stripped", event)

    def test_hand_constructed_truthy_string_confirmed_rejected_at_gate(self):
        # B1: the hand-constructed path runs the FULL gate, not just the
        # datetime checks — "yes" is not consent, and it never silently
        # keeps the attendee list.
        draft = propose_interview_prep(_APP, interview_at=_AWARE)
        draft.attendees = ["recruiter@example.com"]
        draft.attendees_confirmed = "yes"  # not a bool: must not count
        out = confirm_and_handoff(draft, confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "no_valid_drafts")
        self.assertEqual(out["dropped_count"], 1)
        self.assertIn("attendees_confirmed", out["dropped"][0]["reason"])
        self.assertEqual(out["drafts"], [])  # nothing reached a payload

    def test_truthy_string_confirmed_dropped_among_valid_drafts(self):
        good = propose_interview_prep(_APP, interview_at=_AWARE)
        bad = propose_interview_prep(_APP, interview_at=_AWARE)
        bad.attendees = ["recruiter@example.com"]
        bad.attendees_confirmed = "yes"
        out = confirm_and_handoff([good, bad], confirm=True)
        self.assertTrue(out["ok"])
        self.assertEqual(out["handed_off"], 1)
        self.assertEqual(out["dropped_count"], 1)
        self.assertEqual([r["index"] for r in out["dropped"]], [1])
        # The surviving event carries no attendees at all.
        self.assertEqual(out["events"][0]["attendees"], [])

    def test_truthy_string_confirmed_rejected_at_from_dict_gate(self):
        draft = propose_interview_prep(_APP, interview_at=_AWARE)
        data = draft.to_dict()
        data["attendees"] = ["recruiter@example.com"]
        data["attendees_confirmed"] = "yes"
        with self.assertRaises(TypeError) as ctx:
            CalendarDraft.from_dict(data)
        self.assertIn("attendees_confirmed", str(ctx.exception))


class AttendeeShapeTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """M2: attendees must be a list of strings on BOTH paths."""

    def _draft(self):
        return propose_interview_prep(_APP, interview_at=_AWARE)

    def test_attendees_bare_string_rejected_hand_constructed(self):
        draft = self._draft()
        draft.attendees = "recruiter@example.com"  # not a list
        draft.attendees_confirmed = True
        out = confirm_and_handoff(draft, confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["dropped_count"], 1)
        self.assertIn("attendees", out["dropped"][0]["reason"])

    def test_attendees_bare_string_rejected_dict_path(self):
        data = self._draft().to_dict()
        data["attendees"] = "recruiter@example.com"
        data["attendees_confirmed"] = True
        with self.assertRaises(TypeError) as ctx:
            CalendarDraft.from_dict(data)
        self.assertIn("attendees", str(ctx.exception))
        out = confirm_and_handoff(data, confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["dropped_count"], 1)

    def test_attendees_non_string_entries_rejected_hand_constructed(self):
        draft = self._draft()
        draft.attendees = ["recruiter@example.com", 42]
        draft.attendees_confirmed = True
        out = confirm_and_handoff(draft, confirm=True)
        self.assertFalse(out["ok"])
        self.assertIn("attendees", out["dropped"][0]["reason"])

    def test_attendees_non_string_entries_rejected_dict_path(self):
        data = self._draft().to_dict()
        data["attendees"] = ["recruiter@example.com", 42]
        data["attendees_confirmed"] = True
        with self.assertRaises(TypeError):
            CalendarDraft.from_dict(data)


class PayloadFieldValidationTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """m1: non-datetime payload fields are validated on BOTH paths —
    title/description/company/role/application_id are type-checked str,
    event_type is constrained to its known vocabulary."""

    def _draft(self):
        return propose_interview_prep(_APP, interview_at=_AWARE)

    def test_event_type_bogus_rejected_dict_path(self):
        data = self._draft().to_dict()
        data["event_type"] = "bogus"
        with self.assertRaises(ValueError) as ctx:
            CalendarDraft.from_dict(data)
        self.assertIn("event_type", str(ctx.exception))

    def test_event_type_bogus_rejected_hand_constructed(self):
        draft = self._draft()
        draft.event_type = "bogus"
        out = confirm_and_handoff(draft, confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["dropped_count"], 1)
        self.assertIn("event_type", out["dropped"][0]["reason"])

    def test_event_type_vocabulary_accepted(self):
        for event_type in ("interview_prep", "followup_reminder"):
            draft = self._draft()
            draft.event_type = event_type
            out = confirm_and_handoff(draft, confirm=True)
            self.assertTrue(out["ok"], event_type)
            self.assertEqual(out["events"][0]["event_type"], event_type)

    def test_title_non_str_rejected_both_paths(self):
        data = self._draft().to_dict()
        data["title"] = 123
        with self.assertRaises(TypeError) as ctx:
            CalendarDraft.from_dict(data)
        self.assertIn("title", str(ctx.exception))
        draft = self._draft()
        draft.title = 123
        out = confirm_and_handoff(draft, confirm=True)
        self.assertFalse(out["ok"])
        self.assertIn("title", out["dropped"][0]["reason"])

    def test_string_fields_non_str_rejected(self):
        for field_name in ("description", "company", "role", "application_id"):
            data = self._draft().to_dict()
            data[field_name] = 123
            with self.assertRaises(TypeError) as ctx:
                CalendarDraft.from_dict(data)
            self.assertIn(field_name, str(ctx.exception), field_name)


class TopLevelInputTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """nit: a non-iterable top-level input is dropped and named (index 0),
    not raised — the "EVERY input is dropped and named" promise holds."""

    def test_non_iterable_top_level_input_dropped_confirmed_path(self):
        out = confirm_and_handoff(42, confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "no_valid_drafts")
        self.assertEqual(out["dropped_count"], 1)
        self.assertEqual(out["dropped"][0]["index"], 0)
        self.assertTrue(out["dropped"][0]["reason"])

    def test_non_iterable_top_level_input_dropped_review_path(self):
        out = confirm_and_handoff(42, confirm=False)
        self.assertFalse(out["ok"])
        self.assertEqual(out["handed_off"], 0)
        self.assertEqual(out["dropped_count"], 1)
        self.assertEqual(out["dropped"][0]["index"], 0)

    def test_none_top_level_input_dropped_and_named(self):
        # MINOR 4: None is routed through the same drop-and-name logic
        # as any other non-iterable input — dropped_count=1, index 0,
        # reason named.
        for confirm in (True, False):
            out = confirm_and_handoff(None, confirm=confirm)
            self.assertFalse(out["ok"], f"confirm={confirm}")
            self.assertEqual(out["handed_off"], 0, f"confirm={confirm}")
            self.assertEqual(out["dropped_count"], 1, f"confirm={confirm}")
            self.assertEqual(out["dropped"][0]["index"], 0)
            self.assertTrue(out["dropped"][0]["reason"])


class DatetimeValidationTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """M2/M3: naive and malformed datetimes fail closed, never guess."""

    def test_naive_iso_string_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            propose_interview_prep(_APP, interview_at="2026-10-01T14:00:00")
        self.assertIn("naive", str(ctx.exception).lower())

    def test_naive_datetime_object_rejected(self):
        from datetime import datetime

        with self.assertRaises(ValueError):
            propose_interview_prep(
                _APP, interview_at=datetime(2026, 10, 1, 14, 0, 0)
            )

    def test_malformed_from_date_raises_instead_of_now(self):
        with self.assertRaises(ValueError) as ctx:
            propose_followup_reminder(_APP, from_date="not-a-date")
        self.assertIn("cannot parse", str(ctx.exception))

    def test_malformed_interview_at_raises(self):
        with self.assertRaises(ValueError):
            propose_interview_prep(_APP, interview_at="yesterday-ish")

    def test_aware_datetimes_still_accepted(self):
        from datetime import datetime, timezone

        draft = propose_interview_prep(
            _APP, interview_at=datetime(2026, 10, 1, 14, tzinfo=timezone.utc)
        )
        self.assertTrue(draft.has_time)


class PlaceholderTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """M4: placeholder drafts cannot reach a real calendar silently."""

    def test_placeholder_company_blocked(self):
        draft = propose_interview_prep({}, interview_at=_AWARE)
        self.assertIn("Unknown company", draft.company)
        out = confirm_and_handoff(draft, confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "placeholder_content")
        self.assertEqual(out["handed_off"], 0)

    def test_placeholder_role_blocked(self):
        draft = propose_interview_prep({"company": "Acme"}, interview_at=_AWARE)
        self.assertIn("Unknown role", draft.role)
        out = confirm_and_handoff(draft, confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "placeholder_content")

    def test_placeholder_override_requires_explicit_opt_in(self):
        draft = propose_interview_prep({}, interview_at=_AWARE)
        out = confirm_and_handoff(draft, confirm=True, allow_placeholders=True)
        self.assertTrue(out["ok"])
        self.assertEqual(out["handed_off"], 1)


class IdempotencyTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """M5: every payload event carries a stable content hash."""

    def _draft(self):
        return propose_interview_prep(_APP, interview_at=_AWARE)

    def test_key_is_stable_across_confirms(self):
        out1 = confirm_and_handoff(self._draft(), confirm=True)
        out2 = confirm_and_handoff(self._draft(), confirm=True)
        self.assertEqual(
            out1["events"][0]["idempotency_key"],
            out2["events"][0]["idempotency_key"],
        )

    def test_key_survives_serialization_round_trip(self):
        draft = self._draft()
        out = confirm_and_handoff(draft.to_dict(), confirm=True)
        self.assertEqual(out["events"][0]["idempotency_key"], draft.idempotency_key)

    def test_different_drafts_get_different_keys(self):
        other = propose_interview_prep(_APP, interview_at="2026-10-02T14:00:00+00:00")
        self.assertNotEqual(self._draft().idempotency_key, other.idempotency_key)


class TimeRangeValidationTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """m1: prep events must have start < end."""

    def test_negative_prep_minutes_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            propose_interview_prep(_APP, interview_at=_AWARE, prep_minutes=-5)
        self.assertIn("prep_minutes", str(ctx.exception))

    def test_zero_prep_minutes_rejected(self):
        # start == end is not a valid event: start must be strictly before end.
        with self.assertRaises(ValueError):
            propose_interview_prep(_APP, interview_at=_AWARE, prep_minutes=0)


class DictValidationTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """Q1/C5: the dict path passes the same validation as the builder path.

    from_dict raises on bad input; confirm_and_handoff drops-and-names it.
    """

    def _base_dict(self):
        return propose_interview_prep(_APP, interview_at=_AWARE).to_dict()

    def test_naive_time_dict_rejected(self):
        data = self._base_dict()
        data["start_iso"] = "2026-10-01T13:15:00"  # naive — no offset
        with self.assertRaises(ValueError) as ctx:
            CalendarDraft.from_dict(data)
        self.assertIn("naive", str(ctx.exception).lower())
        out = confirm_and_handoff(data, confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["dropped_count"], 1)
        self.assertEqual(out["dropped"][0]["index"], 0)
        self.assertIn("naive", out["dropped"][0]["reason"].lower())

    def test_int_start_iso_rejected(self):
        data = self._base_dict()
        data["start_iso"] = 12345
        with self.assertRaises(TypeError) as ctx:
            CalendarDraft.from_dict(data)
        self.assertIn("start_iso", str(ctx.exception))
        out = confirm_and_handoff(data, confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["dropped_count"], 1)

    def test_unparseable_time_dict_rejected(self):
        data = self._base_dict()
        data["end_iso"] = "not-a-date"
        with self.assertRaises(ValueError) as ctx:
            CalendarDraft.from_dict(data)
        self.assertIn("cannot parse", str(ctx.exception))
        out = confirm_and_handoff(data, confirm=True)
        self.assertFalse(out["ok"])

    def test_start_after_end_dict_rejected(self):
        data = self._base_dict()
        data["start_iso"] = "2026-10-01T16:00:00+00:00"
        data["end_iso"] = "2026-10-01T14:00:00+00:00"
        with self.assertRaises(ValueError) as ctx:
            CalendarDraft.from_dict(data)
        self.assertIn("before end", str(ctx.exception))
        out = confirm_and_handoff(data, confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["dropped"][0]["index"], 0)

    def test_valid_tz_aware_dict_accepted(self):
        data = self._base_dict()
        data["start_iso"] = "2026-10-01T13:00:00+00:00"
        data["end_iso"] = "2026-10-01T14:00:00+00:00"
        out = confirm_and_handoff(data, confirm=True)
        self.assertTrue(out["ok"])
        self.assertEqual(out["handed_off"], 1)

    def test_reminders_min_wrong_type_rejected(self):
        for bad in ("60", [60, "soon"], [60, True]):
            data = self._base_dict()
            data["reminders_min"] = bad
            with self.assertRaises(TypeError) as ctx:
                CalendarDraft.from_dict(data)
            self.assertIn("reminders_min", str(ctx.exception))
            out = confirm_and_handoff(data, confirm=True)
            self.assertFalse(out["ok"])

    def test_truthy_string_attendees_confirmed_rejected(self):
        data = self._base_dict()
        data["attendees"] = ["recruiter@example.com"]
        data["attendees_confirmed"] = "yes"
        with self.assertRaises(TypeError) as ctx:
            CalendarDraft.from_dict(data)
        self.assertIn("attendees_confirmed", str(ctx.exception))

    def test_hand_constructed_draft_with_naive_time_rejected_at_gate(self):
        draft = propose_interview_prep(_APP, interview_at=_AWARE)
        draft.start_iso = "2026-10-01T13:15:00"  # mutate past the builder
        out = confirm_and_handoff(draft, confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["dropped"][0]["index"], 0)

    def test_reminders_min_negative_rejected(self):
        # NIT 9: reminder offsets are range-checked (non-negative), not
        # just type-checked — [-60] is fail-closed on both paths.
        data = self._base_dict()
        data["reminders_min"] = [-60]
        with self.assertRaises(ValueError) as ctx:
            CalendarDraft.from_dict(data)
        self.assertIn("reminders_min", str(ctx.exception))
        out = confirm_and_handoff(data, confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["dropped_count"], 1)
        self.assertIn("reminders_min", out["dropped"][0]["reason"])


class DroppedReportingTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """C3/E2: dropped inputs are named (index + reason) on every path."""

    def _draft(self):
        return propose_interview_prep(_APP, interview_at=_AWARE)

    def test_review_path_reports_dropped_count_and_identities(self):
        out = confirm_and_handoff([self._draft().to_dict(), "junk"], confirm=False)
        self.assertFalse(out["ok"])
        self.assertEqual(len(out["drafts"]), 1)
        self.assertEqual(out["dropped_count"], 1)
        self.assertEqual(out["dropped"][0]["index"], 1)
        self.assertTrue(out["dropped"][0]["reason"])

    def test_success_path_names_dropped_inputs(self):
        out = confirm_and_handoff([self._draft(), "junk", 42], confirm=True)
        self.assertTrue(out["ok"])
        self.assertEqual(out["handed_off"], 1)
        self.assertEqual(out["dropped_count"], 2)
        self.assertEqual([r["index"] for r in out["dropped"]], [1, 2])
        for record in out["dropped"]:
            self.assertIn("index", record)
            self.assertTrue(record["reason"])

    def test_no_valid_drafts_path_names_dropped_inputs(self):
        out = confirm_and_handoff(["junk", None], confirm=True)
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "no_valid_drafts")
        self.assertEqual(out["dropped_count"], 2)
        self.assertEqual([r["index"] for r in out["dropped"]], [0, 1])


class FollowupValidationTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """E3: negative days_after rejected; past from_date warns, not fails."""

    def test_negative_days_after_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            propose_followup_reminder(_APP, days_after=-3)
        self.assertIn("days_after", str(ctx.exception))

    def test_past_from_date_warns_not_fails(self):
        with self.assertLogs(
            "job-apply-mcp.i09.calendar", level="WARNING"
        ) as logs:
            draft = propose_followup_reminder(
                _APP, days_after=7, from_date="2020-01-01T00:00:00+00:00"
            )
        self.assertTrue(
            any("past" in message.lower() for message in logs.output),
            f"expected a past-date warning, got: {logs.output}",
        )
        self.assertTrue(draft.has_time)

    def test_future_from_date_does_not_warn(self):
        with self.assertNoLogs("job-apply-mcp.i09.calendar", level="WARNING"):
            propose_followup_reminder(
                _APP, days_after=7, from_date="2027-01-01T00:00:00+00:00"
            )


class IdempotencyStabilityTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """E4: the key excludes attendees_confirmed (and other confirmation
    state), so confirm -> set attendees_confirmed -> re-confirm yields the
    same key for dedupe."""

    def test_key_stable_across_attendees_confirmation_flow(self):
        # E4 flow: confirm -> set attendees_confirmed -> re-confirm yields
        # the SAME key, so the wiring layer dedupes the double confirm.
        draft = propose_interview_prep(_APP, interview_at=_AWARE)
        draft.attendees = ["recruiter@example.com"]
        out1 = confirm_and_handoff(draft, confirm=True)
        key_unconfirmed = out1["events"][0]["idempotency_key"]
        draft.attendees_confirmed = True
        out2 = confirm_and_handoff(draft, confirm=True)
        self.assertEqual(
            key_unconfirmed, out2["events"][0]["idempotency_key"]
        )
        self.assertEqual(key_unconfirmed, draft.idempotency_key)

    def test_key_excludes_attendees_confirmed_but_includes_attendees(self):
        draft = propose_interview_prep(_APP, interview_at=_AWARE)
        draft.attendees = ["recruiter@example.com"]
        with_confirmed = draft.idempotency_key
        draft.attendees_confirmed = True
        self.assertEqual(with_confirmed, draft.idempotency_key)
        # ...but a genuinely different attendee list still changes the key.
        draft2 = propose_interview_prep(_APP, interview_at=_AWARE)
        self.assertNotEqual(with_confirmed, draft2.idempotency_key)


class PlaceholderBlankAndNearMissTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """MAJOR 1: empty/blank/near-miss company, role, or title are treated
    as missing and blocked exactly like the canonical placeholders — on
    hand-constructed and from_dict paths alike."""

    def _draft(self):
        return propose_interview_prep(_APP, interview_at=_AWARE)

    def _expect_blocked(self, draft_or_dict, label):
        out = confirm_and_handoff(draft_or_dict, confirm=True)
        self.assertFalse(out["ok"], label)
        self.assertEqual(out["error"], "placeholder_content", label)
        self.assertEqual(out["handed_off"], 0, label)

    def test_empty_company_blocked(self):
        draft = self._draft()
        draft.company = ""
        self._expect_blocked(draft, "company=''")

    def test_whitespace_company_blocked(self):
        draft = self._draft()
        draft.company = "  "
        self._expect_blocked(draft, "company='  '")

    def test_lowercase_placeholder_company_blocked(self):
        draft = self._draft()
        draft.company = "unknown company"
        self._expect_blocked(draft, "company='unknown company'")

    def test_uppercase_near_miss_role_blocked(self):
        draft = self._draft()
        draft.role = "UNKNOWN ROLE"
        self._expect_blocked(draft, "role='UNKNOWN ROLE'")

    def test_from_dict_omitting_company_blocked(self):
        # from_dict falls back to the dataclass default "" — the gate
        # must treat it as missing, not as "has a company".
        data = self._draft().to_dict()
        del data["company"]
        self._expect_blocked(data, "from_dict omitting company")

    def test_empty_role_blocked(self):
        draft = self._draft()
        draft.role = ""
        self._expect_blocked(draft, "role=''")

    def test_whitespace_title_blocked(self):
        draft = self._draft()
        draft.title = "  "
        self._expect_blocked(draft, "title='  '")

    def test_blank_company_blocked_on_dict_path(self):
        data = self._draft().to_dict()
        data["company"] = ""
        self._expect_blocked(data, "dict company=''")

    def test_allow_placeholders_true_overrides_blank(self):
        draft = self._draft()
        draft.company = ""
        out = confirm_and_handoff(draft, confirm=True, allow_placeholders=True)
        self.assertTrue(out["ok"])
        self.assertEqual(out["handed_off"], 1)

    def test_allow_placeholders_true_overrides_near_miss(self):
        draft = self._draft()
        draft.company = "UNKNOWN COMPANY"
        out = confirm_and_handoff(draft, confirm=True, allow_placeholders=True)
        self.assertTrue(out["ok"])
        self.assertEqual(out["handed_off"], 1)


class StrictBoolGateTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """MAJOR 2: confirm and allow_placeholders are strict-bool — only the
    literal True authorizes. Truthy non-True values fail closed."""

    def _draft(self):
        return propose_interview_prep(_APP, interview_at=_AWARE)

    def test_truthy_non_true_confirm_refused(self):
        for bad in ("yes", 1, [True]):
            out = confirm_and_handoff(self._draft(), confirm=bad)
            self.assertFalse(out["ok"], f"confirm={bad!r}")
            self.assertEqual(out["handed_off"], 0, f"confirm={bad!r}")
            # Review path: drafts returned, nothing handed off.
            self.assertTrue(out["drafts"], f"confirm={bad!r}")

    def test_confirm_false_still_refused(self):
        out = confirm_and_handoff(self._draft(), confirm=False)
        self.assertFalse(out["ok"])
        self.assertEqual(out["handed_off"], 0)

    def test_confirm_true_still_authorizes(self):
        out = confirm_and_handoff(self._draft(), confirm=True)
        self.assertTrue(out["ok"])
        self.assertEqual(out["handed_off"], 1)

    def test_allow_placeholders_truthy_string_does_not_bypass_gate(self):
        draft = propose_interview_prep({}, interview_at=_AWARE)
        out = confirm_and_handoff(
            draft, confirm=True, allow_placeholders="yes"
        )
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "placeholder_content")

    def test_allow_placeholders_true_bypasses_gate(self):
        draft = propose_interview_prep({}, interview_at=_AWARE)
        out = confirm_and_handoff(
            draft, confirm=True, allow_placeholders=True
        )
        self.assertTrue(out["ok"])
        self.assertEqual(out["handed_off"], 1)


class ReconfirmUpdateContractTests(_SimulatedHumanConfirmation, unittest.TestCase):
    """MAJOR 3: the idempotency key names the EVENT, not the confirm
    attempt. A re-confirm with newly confirmed attendees shares the key
    with the first confirm but carries different content — this is an
    UPDATE, not a duplicate. The payload note states the exact
    dedupe-vs-update rule the wiring layer must apply."""

    def test_reconfirm_with_newly_confirmed_attendees_is_update(self):
        draft = propose_interview_prep(_APP, interview_at=_AWARE)
        draft.attendees = ["recruiter@example.com"]
        out1 = confirm_and_handoff(draft, confirm=True)
        self.assertTrue(out1["ok"])
        self.assertEqual(out1["events"][0]["attendees"], [])
        key = out1["events"][0]["idempotency_key"]

        draft.attendees_confirmed = True
        out2 = confirm_and_handoff(draft, confirm=True)
        self.assertTrue(out2["ok"])
        # Same key (event identity), different content (invite now
        # included) — an UPDATE, not a duplicate to drop.
        self.assertEqual(out2["events"][0]["idempotency_key"], key)
        self.assertEqual(
            out2["events"][0]["attendees"], ["recruiter@example.com"]
        )
        self.assertNotEqual(out1["events"][0], out2["events"][0])

    def test_note_states_dedupe_vs_update_rule(self):
        draft = propose_interview_prep(_APP, interview_at=_AWARE)
        out = confirm_and_handoff(draft, confirm=True)
        note = out["note"]
        self.assertIn("UPDATE", note)
        self.assertIn("byte-identical", note)
        self.assertIn("do NOT dedupe on the key alone", note)

    def test_byte_identical_reconfirm_is_drop_candidate(self):
        # Two confirms of an UNCHANGED draft: same key AND identical
        # event content — the only re-confirm the note says to drop.
        draft = propose_interview_prep(_APP, interview_at=_AWARE)
        out1 = confirm_and_handoff(draft, confirm=True)
        out2 = confirm_and_handoff(draft, confirm=True)
        self.assertEqual(out1["events"][0], out2["events"][0])


if __name__ == "__main__":
    unittest.main()
