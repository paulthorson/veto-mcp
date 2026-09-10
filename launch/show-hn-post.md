# Show HN draft

**Title:** Show HN: An MCP server that applies to jobs, and refuses to lie for you

**Body:**

I built an MCP server that searches jobs across 8 boards (Greenhouse, Lever,
Ashby, Adzuna, LinkedIn, Indeed, ZipRecruiter; Glassdoor is a stub) and helps
an AI agent apply — with a twist: it's governed. It will refuse to submit an
application it can't defend.

The parts I think are actually new:

**Apply-time grilling.** Before an application proceeds, the agent generates
deterministic questions from the gaps between your profile and the job —
missing skills, unquantified experience, logistics, motivation — and sends
them over chat, WhatsApp, or Gmail. The application stays `grill_pending`
until you answer. Gmail replies are matched by a `[grill:<id>]` subject tag
and ingested automatically. It turns out a one-line "1. lots 2. 15GB 3. 2GB"
reply parses fine once you stop assuming one answer per message.

**A constitutional veto screen on every application.** Before anything is
submitted, the intended application goes through a veto check, a
cover-letter honesty scan (claims a skill your profile doesn't support?
blocked), and qualification scoring against the job description. Score under
0.40 and it's `governance_blocked`. Only a human can clear a veto.

**Fill-only on scraping-tier boards.** This is the policy I'm most opinionated
about: automation may fill an application form but must never perform the
final submit click on a scraping-tier site. The code enforces it — a submit
attempt raises a fill-only violation. Official ATS endpoints are the only
path to full automation, and I couldn't verify a safe anonymous one, so that
tool returns an honest "unsupported" instead of guessing.

**Boring-but-real compliance machinery:** ToS-risk acknowledgment before any
scraping-tier search, daily search budgets (1000 official / 40 scraping per
board), circuit breakers with exponential cooldown on 403/429/CAPTCHA, max 5
applications/day with 2–7 minute randomized pauses. Every allow/block decision
goes to a verdict ledger.

Also in the box: a paced application queue, recruiter-email classification
with stage-sync proposals, company briefs and interview prep built only from
real profile achievements (facts it can't verify are marked `unverified`,
never invented), and funnel analytics.

Honest limitations:

- No CAPTCHA bypass, ever. If a site pushes back, the circuit breaker backs
  off. Some runs will just return less.
- LinkedIn uses the guest API — it works but rate-limits (429s) from
  datacenter IPs. Indeed 403s from this sandbox entirely.
- Glassdoor is a stub. ZipRecruiter is real but scraping-tier.
- The governance framework is a separate install; without it the
  deterministic compliance gates still hold, marked `compliance-only`.

It's open source — repo link in my profile / link in bio. MIT-ish, standard
stuff.

What I'd actually like feedback on: the fill-only policy (too strict?
not strict enough?), and whether the grill questions are the right ones —
what would you want an agent to ask *you* before it applied in your name?
