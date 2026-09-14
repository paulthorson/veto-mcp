# Feedback & crash reporting — requirements

**Status:** Approved scope by Paul Thorson, 2026-09-14 (chat). Scoped as an
Initiative 10 (Distribution) follow-on — it concerns Veto running on user machines.
Queued after the 08 security work and the 09 circuit breaker.

## The requirement (Paul's words, condensed)

Veto needs a feedback mechanism: users can send bugs/issues they're having, and when
something crashes locally on the user's machine, Veto automatically sends a report to
the git repo as an auto-generated issue, so the team can see it and fix it.

## What to build

1. **"Report a problem" in-app.** One-tap from the dashboard and the web UI / PWA.
   Captures: what the user was doing, their description, app version, platform, and
   recent log tail. Previews everything before sending — the user sees exactly what
   leaves their machine.
2. **Automatic crash capture.** Unhandled exceptions are caught, fingerprinted
   (crash signature from stack frames, not messages), and stored locally.
3. **On-device PII scrub before anything leaves.** Veto handles resumes, emails, and
   job applications — a raw traceback can contain all of it. Every report goes
   through the Initiative 08 scrub/quarantine pipeline; anything that can't be
   proven clean is withheld, and the report says what was withheld.
4. **Automatic private issue filing.** Scrubbed reports are filed automatically into a
   **private** issue tracker visible only to the Veto team — never posted publicly,
   never attributed to the user (filed under Veto's own identity). Per Paul's
   2026-09-14 decision and the terms review: public GitHub issues are NOT the intake
   mechanism (adversarial legal review found public intake + anonymity promises
   deceptive — Rule 1 veto). Title from the crash signature; body with version,
   platform, scrubbed traceback, reproduction context.
5. **Dedup.** Same crash signature → comment on the existing open issue, not a new
   issue. Closed issues with a new occurrence get reopened with a fresh report.
6. **Rate limits & user control.** Cap on reports per day. In the terms (TERMS.md
   v2026-09-14): crash/problem reports are a **required** condition of the free
   license; usage analytics are a **separate opt-in toggle** (off by default) per
   GDPR. Every auto-filed issue links back to the local report the user can inspect
   in Settings → "Data sent."

## Open questions for Paul (at build time, not now)

- **GitHub token:** auto-filing needs credentials. Options: a bot/fine-grained PAT
  Paul provisions and Veto stores securely, or per-user tokens. Paul to decide.
- **Repo target:** file against the main repo or a dedicated `veto-feedback` repo
  (keeps crash noise out of the development tracker).

## Governance

- Full framework compliance (ag_review.py, blind review, append-only verdicts).
- Security-domain review is the critical gate: adversarial probes must attempt
  PII exfiltration through the report path (poisoned resume text, emails in
  tracebacks, tokens in log tails). The 07 WS1 consent saga is the cautionary tale:
  the scrubber will be attacked with confusables, bidi overrides, and unusual
  encodings until it holds.
- Privacy review: the "what leaves the machine" preview must be byte-accurate —
  no summarizing, no truncation that hides content.

## First-run consent gate (added 2026-09-14)

Paul's directive: Veto is free, and the price is anonymous telemetry — stated
upfront, accepted before first use. The terms live in `TERMS.md` (repo root,
plain English).

The feedback build therefore includes a first-run consent screen:
1. Shows the deal in plain words (free product ↔ anonymous analytics + problem
   reports), with concrete examples of what is and isn't sent.
2. "Preview a sample report" — the user can inspect a real scrubbed report before
   agreeing, so consent is informed, not blind. (Same pattern as 07's consent
   preview: show exactly what leaves, then ask.)
3. Accept → telemetry flows. Decline → Veto doesn't start. No silent opt-in, no
   pre-ticked boxes.
4. Settings keeps a permanent "what you've sent" log the user can review any time.

Note: TERMS.md is a product draft, not legal counsel — lawyer review required
before public launch.
