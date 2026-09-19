# Veto Changelog

Plain-English notes on what changed in Veto, most recent first. Written for users,
not engineers. If something isn't listed here, it didn't ship.

## Unreleased (on main, not yet in a numbered release)

These are built, reviewed, and committed to the main codebase. They will be part of
the next versioned release.

- **Product naming** — Visitor-facing strings, theme identifiers, and governance
  ticket prefixes use the Veto / veto-mcp names.
- **Mentor matching** — Match with mentors. Before you share anything, you see an
  exact preview of what they would see. Sharing requires explicit consent. Includes
  blocking and quarantine controls.
- **Extension platform** — Extensions run in a sandbox, versions are signed, and
  banned versions stay banned (they cannot be restored by rollback).
- **Interview & skills lab** — Practice interviews with feedback, progress tracking,
  drill recommendations, and a skill-gap map (including soft skills).
- **Application studio** — A workspace for each application: ATS checks, draft diffs,
  and a library of evidence (achievements, metrics, proof).
- **Fit decoder & career graph** — Explains fit in plain language: matching skills,
  gaps, and how prior roles relate to the target.
- **Connector reliability** — Keeps board, email, and calendar connections working:
  follow-up messaging, durable handoffs, and recovery when a channel drops.
- **Distribution** — Install as a phone or desktop app; back up or restore local data.

Still being built (not claimed as shipped): collective intelligence, outcomes &
lifecycle, adaptive fit engine, daily operating loop, and related craft. Planned for
connector reliability: a human circuit breaker so every drafted outbound message
waits for your review until you raise the trust level.

## v0.1.0 — 2026-09-12

First release. Veto searches the official-API boards (Greenhouse, Lever, Ashby,
Adzuna — Adzuna needs a free API key), grills you about resume gaps over chat or
WhatsApp, tailors applications without inventing experience, fills forms but stops
before submit — you click submit — and tracks applications, stages, and follow-ups.
Glassdoor is a locked stub (no scraping). Runs as an MCP server with a terminal
dashboard and a local web UI usable on a phone over your home network.

> **Erratum:** an earlier draft of these notes listed eight boards including
> LinkedIn, Indeed, and ZipRecruiter. Those scrapers were removed before public
> distribution; the four official-API boards above are the accurate set.
