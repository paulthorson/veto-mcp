#!/usr/bin/env python3
"""Epic 4 — calendar handoff: confirmed interview-prep events and follow-up
reminders through connected calendars.

Design (roadmap constraint 02 — humans own consequential actions):

* ``propose_interview_prep`` / ``propose_followup_reminder`` build event
  DRAFTS only. They read application records, they change nothing, they
  touch no calendar.
* ``confirm_and_handoff`` turns drafts into a handoff payload ONLY with
  ``confirm=True``. Without it, the drafts are returned with instructions.
* The actual calendar write happens through the user's connected calendar
  (the google-calendar skill) at the wiring layer — this module names the
  destination explicitly and lists exactly what data the event carries, so
  the confirmation the user gives is informed.

Every handoff declares its manifest: what it can do, why it may be
blocked, what data it sends, which actions require confirmation.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from providers._contract import ConnectorManifest

log = logging.getLogger("job-apply-mcp.i09.calendar")

CALENDAR_MANIFEST = ConnectorManifest(
    name="calendar_handoff",
    connector_type="calendar",
    what_it_can_do=[
        "Draft interview-prep calendar events from confirmed interview "
        "details (role, company, time, prep checklist).",
        "Draft follow-up reminders tied to application records.",
        "Hand confirmed drafts to the connected calendar — only after the "
        "user confirms each handoff.",
    ],
    why_it_may_be_blocked=[
        "No calendar is connected (the google-calendar skill is not "
        "connected).",
        "The interview details are missing a time — a draft is still "
        "built, but handoff waits for the user to set the time.",
        "The user did not confirm the handoff.",
    ],
    what_data_it_sends=[
        "On confirmed handoff only: event title, start/end time, "
        "description (role, company, prep checklist), and reminder "
        "offsets to the connected calendar service.",
        "Drafting sends nothing anywhere.",
    ],
    what_requires_confirmation=[
        "Every calendar write: confirm_and_handoff refuses without "
        "confirm=True.",
        "Attendee invites are never added without the user naming them "
        "explicitly.",
    ],
    official_interface="Connected calendar via the google-calendar skill",
    interface_basis="User's own calendar grant; Veto never invents events.",
)


@dataclass
class CalendarDraft:
    """One proposed calendar event. A draft is not a write."""

    title: str
    start_iso: str  # ISO-8601; "" when the time is not known yet
    end_iso: str
    description: str
    event_type: str  # "interview_prep" | "followup_reminder"
    application_id: str = ""
    company: str = ""
    role: str = ""
    reminders_min: list[int] = field(default_factory=lambda: [60, 1440])
    attendees: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def has_time(self) -> bool:
        return bool(self.start_iso and self.end_iso)


def _parse_when(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def propose_interview_prep(
    application: dict[str, Any],
    interview_at: Any = None,
    prep_minutes: int = 45,
) -> CalendarDraft:
    """Draft an interview-prep event. No side effects, no calendar touched.

    ``application`` is a record with company/title/job_id keys.
    ``interview_at`` is the confirmed interview time (ISO string or
    datetime); when unknown the draft is still returned with empty times
    so the user can set them at handoff.
    """
    application = application or {}
    company = str(application.get("company") or "Unknown company")
    role = str(application.get("title") or "Unknown role")
    when = _parse_when(interview_at or application.get("interview_at"))
    if when:
        start = when - timedelta(minutes=prep_minutes)
        start_iso, end_iso = start.isoformat(), when.isoformat()
    else:
        start_iso, end_iso = "", ""
    checklist = "\n".join(
        [
            "Prep checklist:",
            f"• Re-read the tailored resume + cover letter for {role}",
            "• 3 STAR stories mapped to the job requirements",
            "• 2 questions for the interviewer (role + team)",
            "• Logistics: link/location, contact, materials ready",
        ]
    )
    return CalendarDraft(
        title=f"Interview prep — {role} @ {company}",
        start_iso=start_iso,
        end_iso=end_iso,
        description=checklist,
        event_type="interview_prep",
        application_id=str(application.get("job_id") or application.get("id") or ""),
        company=company,
        role=role,
        reminders_min=[60, 1440],
    )


def propose_followup_reminder(
    application: dict[str, Any],
    days_after: int = 7,
    from_date: Any = None,
) -> CalendarDraft:
    """Draft a follow-up reminder. No side effects."""
    application = application or {}
    company = str(application.get("company") or "Unknown company")
    role = str(application.get("title") or "Unknown role")
    base = _parse_when(from_date) or datetime.now(timezone.utc)
    when = base + timedelta(days=days_after)
    return CalendarDraft(
        title=f"Follow up — {role} @ {company}",
        start_iso=when.isoformat(),
        end_iso=(when + timedelta(minutes=15)).isoformat(),
        description=(
            f"Check on the {role} application at {company}. "
            "Draft the follow-up with the gmail channel (draft first, "
            "send only on confirm)."
        ),
        event_type="followup_reminder",
        application_id=str(application.get("job_id") or application.get("id") or ""),
        company=company,
        role=role,
        reminders_min=[60],
    )


def confirm_and_handoff(
    drafts: list[CalendarDraft] | CalendarDraft,
    *,
    confirm: bool = False,
    destination: str = "connected calendar (google-calendar skill)",
) -> dict[str, Any]:
    """Hand confirmed drafts to the calendar — ONLY with confirm=True.

    Returns a handoff payload the wiring layer (server.py / cli.py /
    webui.py) executes against the connected calendar. This module never
    performs the write itself: the confirmation gate lives here, the
    transport lives at the edge with the user's own grant.
    """
    if isinstance(drafts, CalendarDraft):
        drafts = [drafts]
    drafts = [d for d in drafts if isinstance(d, CalendarDraft)]
    if not confirm:
        return {
            "ok": False,
            "handed_off": 0,
            "drafts": [d.to_dict() for d in drafts],
            "instructions": (
                "These are DRAFTS — nothing was written to any calendar. "
                "Review each draft (title, time, description), set any "
                "missing times, then call confirm_and_handoff with "
                "confirm=True to hand them to your connected calendar."
            ),
        }
    missing_time = [d.title for d in drafts if not d.has_time]
    if missing_time:
        return {
            "ok": False,
            "handed_off": 0,
            "drafts": [d.to_dict() for d in drafts],
            "error": "missing_time",
            "instructions": (
                "These drafts have no time set and were NOT handed off: "
                + "; ".join(missing_time)
                + ". Set start_iso/end_iso, then confirm again."
            ),
        }
    payload = {
        "ok": True,
        "handed_off": len(drafts),
        "destination": destination,
        "data_sent_per_event": [
            "title", "start/end time", "description", "reminder offsets"
        ],
        "events": [d.to_dict() for d in drafts],
        "note": (
            "Wiring layer: create these events through the user's connected "
            "calendar (google-calendar skill) now. Attendees were not added "
            "— the user must name them explicitly."
        ),
    }
    log.info("Calendar handoff confirmed: %d event(s) to %s", len(drafts), destination)
    return payload
