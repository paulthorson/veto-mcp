# Job Apply MCP Server

An MCP (Model Context Protocol) server that lets an AI agent **search jobs
across major boards** and **help apply without manual form filling**.

## Tools

| Tool | Description |
|---|---|
| `search_jobs(query, location, board="all", limit=10, remote_only=False)` | Search postings. Returns jobs with `id`, `title`, `company`, `location`, `url`, `board`, `snippet`. |
| `get_job_details(job_id)` | Full description, requirements, and `apply_url` for one job. |
| `apply_to_job(job_id, resume_path, cover_letter="", answers={}, confirm=False, profile=None, headless=True)` | **Dry-run preview by default.** With `confirm=True`: Phase 1 logs locally (default), or Phase 2 auto-fills + submits in headless Chromium when `JOB_MCP_BROWSER_APPLY=1` and a `profile` dict are provided. `profile` defaults to your saved wizard profile. Never submits without `confirm=True`. |
| `get_profile()` | Returns the applicant profile saved by the onboarding wizard (`profiles/profile.json`), or setup instructions if it doesn't exist yet. |
| `list_boards()` | Supported boards and their status (`active` / `stub`). |
| `track_applications()` | Everything recorded in `applications.json`. |

## Onboarding wizard

Run the interactive wizard once to build your saved profile — it asks
basic questions (name, contact, target titles, locations, remote
preference, salary, skills, work authorization) and can **ingest your
LinkedIn data** to pre-fill experience, education, and skills:

```bash
.venv/bin/python wizard.py        # or: .venv/bin/python cli.py wizard
```

LinkedIn ingestion options:

1. **Data-export ZIP (recommended).** In LinkedIn: *Settings & Privacy →
   Data Privacy → Get a copy of your data* → request and download the
   archive, then give the wizard the ZIP path. It parses `Profile.csv`,
   `Positions.csv`, `Education.csv`, and `Skills.csv` — no LinkedIn
   login or scraping needed.
2. **Public profile URL.** The wizard fetches your public LinkedIn page
   best-effort (LinkedIn usually blocks scraping, so this is limited —
   option 1 is better).
3. **Skip** — answer everything manually.

This writes `profiles/profile.json` (gitignored — your data stays
local). Then build your resume:

```bash
.venv/bin/python resume_builder.py
```

which emits `profiles/resume.md`, `profiles/resume.html`, and
`profiles/resume.pdf` (PDF needs `reportlab`, included in
requirements.txt). The saved profile is also the default `profile` for
`apply_to_job`'s Phase 2 browser auto-fill, and `get_profile()` exposes
it to the agent.

## Boards

- **Indeed** — active. Scrapes public search (`https://www.indeed.com/jobs`) with
  resilient selectors (falls back across markup generations).
- **LinkedIn** — active. Uses the public guest API
  (`/jobs-guest/jobs/api/seeMoreJobPostings/search`, no auth).
- **Greenhouse** — active. Public Job Board API, no auth
  (`boards-api.greenhouse.io`). Searches a curated employer list in
  `providers/boards.json` (Stripe, Airbnb, Coinbase, …) — add your own
  board tokens there.
- **Lever** — active. Public postings API, no auth (`api.lever.co`).
  Curated company list in `providers/boards.json`.
- **Ashby** — active. Public posting API, no auth (`api.ashbyhq.com`).
  Curated board list in `providers/boards.json`.
- **Adzuna** — key-gated stub. Set `ADZUNA_APP_ID` + `ADZUNA_APP_KEY`
  (from developer.adzuna.com) to activate; without them `search_jobs`
  returns a clear error.
- **Glassdoor / ZipRecruiter** — stubs with clear TODOs (JS-rendered and
  bot-protected; need the Phase 2 browser hook).

### Live-test status (2026-09-10, sandbox)

- **Greenhouse: working.** `search_jobs("software engineer", "",
  board="greenhouse", limit=5)` returned real postings (Stripe, Airbnb,
  Coinbase…); `get_job_details` round-trip returned a 2,890-char
  description. Dead tokens (`notion`, `openai`) were dropped from
  `boards.json`.
- **Lever: working.** Returned real postings (Spotify, Palantir…);
  details round-trip OK. Many curated tokens 404'd (those employers left
  Lever); `boards.json` keeps the verified four.
- **Ashby: working** via GET `posting-api/job-board/{board}` (POST
  401s — implemented with GET primary, POST fallback). Returned real
  postings (Ashby, OpenAI, Ramp…); details round-trip returned a
  21k-char description.
- **Adzuna: stub verified.** Without API keys, `search_jobs` raises a
  clear `ValueError` pointing at `developer.adzuna.com`.

### Earlier results (2026-09-09, sandbox)

- **LinkedIn: working.** `search_jobs("software engineer", "New York, NY",
  board="linkedin")` returned real postings (JPMorganChase, AWS, Plaid,
  Whatnot…); `get_job_details` returned full descriptions via the
  `/jobs-guest/jobs/api/jobPosting/{id}` endpoint. Occasional HTTP 429
  rate-limits occur — the provider logs a warning and returns what it got.
- **Indeed: bot-blocked from datacenter IPs.** Indeed returned HTTP 403 /
  dropped connections from this sandbox's egress IP. The provider handles
  this gracefully (warning + empty results, no crash). **Fallbacks:** run
  from a residential IP, add longer delays, or use the Phase 2 browser hook
  with a logged-in session.

## Setup

```bash
cd ~/workspace/job-apply-mcp
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

The server speaks MCP over stdio:

```bash
.venv/bin/python server.py
```

## CLI

`cli.py` exposes the same tools from a terminal — no MCP client config
needed:

```bash
.venv/bin/python cli.py boards
.venv/bin/python cli.py search "software engineer" --location "New York, NY"
.venv/bin/python cli.py search "software engineer" --board linkedin --limit 5
.venv/bin/python cli.py search "software engineer" --remote --json
.venv/bin/python cli.py show <job_id>
.venv/bin/python cli.py applications
.venv/bin/python cli.py profile
.venv/bin/python cli.py wizard
```

Applying is a two-step flow. First a dry run (prints a preview, exits
non-zero, records nothing):

```bash
.venv/bin/python cli.py apply <job_id> --resume ~/resume.pdf
```

Then, when you're happy with the preview, record it:

```bash
.venv/bin/python cli.py apply <job_id> --resume ~/resume.pdf --confirm
```

Add `--json` to `search`, `show`, or `applications` for machine-readable
output, and `--profile path/to/profile.json` to `apply` to pass applicant
details for Phase 2 browser auto-fill. `wizard` launches the interactive
onboarding wizard (builds your saved profile, optionally ingesting your
LinkedIn export); `profile` shows the saved profile summary.

Note: each CLI invocation is a fresh process, so the dry-run preview
shows job title/company as "Unknown" — the job id itself is
self-describing, so `show` and `apply` still resolve the right posting.

## Connect

A ready-to-paste stdio config lives at
[`mcp-config.json`](sandbox://workspace/job-apply-mcp/mcp-config.json):

```json
{
  "mcpServers": {
    "job-apply": {
      "command": "/home/hatch/workspace/job-apply-mcp/.venv/bin/python",
      "args": ["/home/hatch/workspace/job-apply-mcp/server.py"],
      "env": {}
    }
  }
}
```

The server communicates over stdio using **newline-delimited JSON-RPC**
(one JSON message per line), as implemented by MCP Python SDK 2.x.

### Claude Desktop

Add the `job-apply` entry above to your Claude Desktop config
(`~/Library/Application Support/Claude/claude_desktop_config.json`
on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows —
merge it into the existing `mcpServers` object, don't replace the file).
Restart Claude Desktop afterwards.

### Muse CLI / other MCP clients

Muse CLI and most MCP clients accept the same `mcpServers` shape — point
them at the command/args above. For clients that take a single server
entry, drop the `mcpServers` wrapper and use just the `job-apply` object.

### Note: this Muse environment

This sandbox *is* the machine at `/home/hatch`. If an MCP-capable client
is running here, the config above works verbatim — the venv interpreter
is at `/home/hatch/workspace/job-apply-mcp/.venv/bin/python` and the
server speaks stdio, so no network ports or extra setup are needed. There
is currently no system-level MCP client config on this machine
(`~/.config/Claude/claude_desktop_config.json`, `~/.claude.json`, and
`~/.config/mcp*` were checked and do not exist), so copy
`mcp-config.json` into whichever client you use rather than relying on an
auto-discovered location.

## How applying works

1. `search_jobs` → pick a job → `get_job_details` to read the description.
2. `apply_to_job(job_id, resume_path, ...)` **without** `confirm` returns a
   dry-run preview: job info, resume check, typical form fields, direct
   `apply_url`.
3. Re-call with `confirm=True` → the application is appended to
   `applications.json` with status `confirmed`, and you get the `apply_url`
   to finish submitting in your browser.

**Phase 2 (browser automation):** `browser_apply.py` implements Playwright-based
form filling. It detects visible inputs/textareas/selects/file-uploads,
fills them from a `profile` dict, uploads the resume, screenshots the form,
and — only with `confirm=True` — clicks the submit button. Without
`confirm=True` it fills + screenshots and returns `submitted=False`.

## Phase 2: browser automation

`browser_apply.py` (Playwright, sync API) fills and submits application
forms in headless Chromium:

- `extract_form_fields(page)` → list of `{name, label, type, selector}`
  for visible inputs / textareas / selects / file inputs.
- `fill_application(page, profile, resume_path)` → dict of fields actually
  filled. `full_name` is split into first/last when the form asks for them
  separately; the resume is uploaded to file inputs when it exists on disk.
  Checkboxes/radios (attestations, EEO questions) are intentionally left
  for the human.
- `apply_via_browser(apply_url, profile, resume_path, headless=True, confirm=False)`
  → `{ok, submitted, fields_filled, fields_detected, screenshot,
  screenshot_after_submit, final_url, error}`. It **never clicks submit
  unless `confirm=True`**. Cookie/consent banners are dismissed
  best-effort; failures return error dicts, never exceptions.

### Enabling Phase 2

```bash
.venv/bin/pip install -r requirements.txt   # includes playwright
.venv/bin/python -m playwright install chromium
export JOB_MCP_BROWSER_APPLY=1
```

> **Sandbox note (2026-09-09):** the Chromium binary download failed from
> this sandbox's network — both `playwright install chromium` and
> `playwright install chromium --only-shell` ended in a download error —
> so browser mode could not be live-tested here. The `playwright` Python
> package itself installs fine, and `browser_apply` degrades gracefully
> (returns an error dict) when the browser binary is missing. Install
> Chromium on your own machine with the command above.

Then call:

```python
apply_to_job(
    job_id,
    resume_path="~/resume.pdf",
    confirm=True,
    profile={
        "full_name": "Ada Lovelace",
        "email": "ada@example.com",
        "phone": "+1 555-0100",
        "location": "New York, NY",
        "linkedin_url": "https://www.linkedin.com/in/adalovelace",
        "website": "https://adalovelace.dev",
        "cover_letter": "Dear hiring team, ...",
    },
)
```

Without `JOB_MCP_BROWSER_APPLY=1`, `confirm=True` keeps the Phase 1
behavior (local log only + direct `apply_url` for manual submission).

Screenshots land in `job-apply-mcp/screenshots/` (pre-fill preview and,
after a confirmed submit, a post-submit shot). Each confirmed Phase 2
attempt appends to `applications.json` with `status` of
`browser_submitted` or `browser_failed`, the screenshot paths, and the
`submitted` flag — always verify on the live site before treating an
application as complete.

### Profile schema

All keys optional. Explicit `first_name`/`last_name` win over splitting
`full_name`.

| Key | Used for |
|---|---|
| `full_name` / `first_name` / `last_name` | Name fields |
| `email` | Email fields |
| `phone` | Phone/tel fields |
| `location` | Location/city/address fields |
| `linkedin_url` | LinkedIn URL fields |
| `website` | Website/portfolio fields |
| `cover_letter` | Cover-letter textareas |

### Persistent login sessions

Phase 2 used to launch a fresh browser every run, so logins (LinkedIn
Easy Apply, Indeed, etc.) never survived. `browser_apply.py` now supports
saved sessions:

- `login_session(board)` — opens a **headed** browser on the board's login
  page. You log in manually (MFA/CAPTCHA included); the function watches
  for the login to complete (up to 5 minutes), then saves
  `sessions/{board}.json` (gitignored, `chmod 600`). **Passwords are
  never typed or stored** — only the resulting session cookies/storage.
- `apply_via_browser(..., board="linkedin")` — when a saved session exists
  for the board, it is loaded into the browser context automatically.

```python
from browser_apply import login_session
login_session("linkedin")   # log in in the opened window, then it closes itself
```

```bash
export JOB_MCP_BROWSER_APPLY=1
# apply_to_job(..., confirm=True) now reuses the LinkedIn session
```

Sessions expire like normal logins — re-run `login_session(board)` when a
site starts asking you to log in again.

## ⚠️ Risks / Terms-of-Service warning

- **Scraping LinkedIn and Indeed may violate their Terms of Service.**
  LinkedIn in particular aggressively blocks automation; the guest API used
  here can return HTTP 403/429 or CAPTCHAs at any time.
- Consequences can include **IP rate-limiting, CAPTCHA loops, and account
  restrictions** if you later automate logged-in actions. This server stores
  **no credentials** and performs **no logged-in automation**.
- The server adds 1–2s politeness delays and rotates user agents, but that
  only reduces load — it does not make scraping ToS-compliant.
- **Never auto-submit applications** without the user's explicit review:
  `apply_to_job` requires `confirm=True`, and even then Phase 1 only
  *records* the application locally — the human completes the final submit.
- **Phase 2 automated applying carries extra risk.** Driving real
  application forms with a headless browser can trigger **anti-bot
  measures (CAPTCHAs, IP throttles) and account limits or bans on
  LinkedIn, Indeed, and other boards** — especially on logged-in flows
  like LinkedIn Easy Apply or Workday. Mitigations built in: no
  credential storage, explicit `confirm=True` required to click submit,
  screenshots for human review, one application per tool call. Still,
  **apply at a human pace** (a handful of applications per day, not
  bulk blasts), expect some sites to block automation outright, and
  always verify the submission on the live site.
- Job data returned is a snapshot; always verify details on the live posting
  before applying.

## Project layout

```
job-apply-mcp/
├── server.py           # MCP server (providers, tools, Phase 2 wiring)
├── cli.py              # terminal CLI mirroring the MCP tools
├── wizard.py           # onboarding wizard → profiles/profile.json
├── resume_builder.py   # resume.md / resume.html / resume.pdf from profile
├── browser_apply.py    # Phase 2 Playwright form-fill/submit automation
├── providers/          # API-based board providers (no auth needed)
│   ├── __init__.py
│   ├── _common.py      # shared HTTP/polite-delay/id helpers
│   ├── boards.json     # curated Greenhouse/Lever/Ashby board tokens
│   ├── greenhouse.py
│   ├── lever.py
│   ├── ashby.py
│   └── adzuna.py       # key-gated stub (ADZUNA_APP_ID/ADZUNA_APP_KEY)
├── profiles/           # your data (gitignored: profile.json)
│   ├── profile.json    # wizard output — your saved applicant profile
│   ├── resume.md
│   ├── resume.html
│   └── resume.pdf
├── screenshots/        # Phase 2 form screenshots (created on first run)
├── requirements.txt    # includes playwright (Phase 2) + reportlab (resume PDF)
├── README.md
├── mcp-config.json     # ready-to-paste stdio client config
├── applications.json   # local application log (starts empty)
└── .venv/              # Python virtualenv (not committed)
```

## Quick self-test

```bash
.venv/bin/python - <<'EOF'
import server
print(server.list_boards())
jobs = server.search_jobs("software engineer", "New York, NY", limit=5)
print(f"{len(jobs)} jobs")
for j in jobs[:5]:
    print(j["board"], "|", j["title"], "|", j["company"], "|", j["location"])
EOF
```

## CI/CD

[![CI](https://github.com/paulthorson/job-apply-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/paulthorson/job-apply-mcp/actions/workflows/ci.yml)

### Continuous integration

Every push and pull request to `main` runs `.github/workflows/ci.yml`
on Ubuntu with Python 3.12:

1. `pip install -r requirements.txt` (pip cache enabled)
2. `python -m playwright install --with-deps chromium` — if this fails,
   the step is allowed to fail and the E2E browser tests skip gracefully
   (skips don't fail the run)
3. Compile check over every `.py` file (excludes `.venv/`, `.git/`)
4. `python -m unittest discover -s tests -v`

### Releases

Push a tag like `v0.1.0` and `.github/workflows/release.yml`:

1. Builds the Docker image and pushes it to
   `ghcr.io/paulthorson/job-apply-mcp` with the version tag and `latest`
2. Creates a GitHub Release for the tag with auto-generated notes

```bash
git tag v0.1.0 && git push origin v0.1.0
```

### Docker

The image runs the MCP server on stdio (no ports — see
[`Dockerfile`](sandbox://workspace/job-apply-mcp/Dockerfile)):

```bash
docker run -i ghcr.io/paulthorson/job-apply-mcp:latest
```

To build locally:

```bash
docker build -t job-apply-mcp .
```

Dependency updates (pip, Docker base image, GitHub Actions) are handled
weekly by Dependabot (`.github/dependabot.yml`).

## Lifecycle & monitoring

### Application stages

Every recorded application now carries a pipeline stage. Stages:
`applied` → `interviewing` → `offer`, plus `rejected`, `withdrawn`,
`ghosted`. Each entry keeps a `stage_history` (`{stage, at, note}` events)
and an optional `follow_up_due` date.

| Tool | What it does |
|---|---|
| `update_application(job_id_or_index, stage, note="")` | Move an application to a new stage (validates the stage, appends history). Moving to `interviewing` sets a follow-up reminder 7 days out; terminal stages (`offer`/`rejected`/`withdrawn`) clear it. Accepts a `job_id` or a numeric index into `track_applications()`. |
| `application_stats()` | `{total, by_stage, by_board, response_rate}` — response rate = (interviewing + offer) / total. |
| `nudge_followups()` | Applications with `follow_up_due` today or earlier (stages `applied`/`interviewing`). |
| `export_applications_csv(path="applications.csv")` | Dump everything to CSV for spreadsheets / portability. |

Legacy entries (recorded before stages existed) are backfilled in memory
as `applied` on read — the file is only rewritten when you actually
update something.

### Job watches

Save a search once, get alerted only about *new* postings:

```bash
# via MCP tools
add_watch("swe-nyc", "software engineer", "New York, NY", "greenhouse")
check_watches()   # -> {watch_name: {new_jobs: [...], total_seen: N}}
```

The **first** check of a watch only records a baseline and reports no new
jobs — by design, so you're not spammed with everything that already
existed. Watches persist in `watches.json` (gitignored).

**Cron:** `python watch.py` checks all saved watches, prints JSON, exits 0:

```cron
0 9 * * * cd ~/workspace/job-apply-mcp && .venv/bin/python watch.py
```

### Multiple profiles

`profiles.py` adds named profiles (e.g. one per target role) without
breaking the wizard's single `profiles/profile.json`:

1. explicit name → `profiles/<name>.json`
2. `PROFILE_NAME` env var → `profiles/<env>.json`
3. `profiles/default.json` if it exists
4. legacy `profiles/profile.json`

```python
from profiles import load_profile, save_profile, list_profiles
load_profile("backend")          # explicit
load_profile()                   # PROFILE_NAME env -> default.json -> profile.json
save_profile({...}, "frontend")  # writes profiles/frontend.json
```

All `profiles/*.json` files are gitignored — profiles never get committed.

## Application quality

Features that keep search results clean and applications competitive:

- **Dedup** (`dedup.py`) — `search_jobs` automatically collapses duplicate
  postings: exact URL matches, exact (company, title) matches, and fuzzy
  title matches (≥0.85 similarity) for the same company. The most
  informative entry survives. Recall-friendly: nothing ambiguous is merged.
- **Tailoring** (`tailor.py`, `tailor_application` tool) — builds a
  per-job resume + 3-paragraph cover letter from your saved profile:
  keyword-matched experience bullets are front-loaded and the letter
  references the actual role/company. **Honesty rule:** it never invents
  skills, titles, or experience — gaps are reported as `missing_skills`,
  not added to the resume.
- **Search filters** — `search_jobs(..., salary_min=120000,
  seniority="senior")`. Post-filtering on listing text (`$150k`,
  `$150,000`, `$75/hr` → annualized; title keywords like senior/jr/staff/
  principal), because most boards don't expose these as search parameters.
  Jobs with no detectable salary/seniority are kept, never dropped.
- **Company preferences** (`prefs.py`, `update_preferences` tool) —
  `preferences.json` (gitignored; copy `preferences.example.json` to start)
  with `blocked_companies`, `preferred_companies`, `blocked_keywords`.
  Blocked matches are removed; preferred companies are flagged
  `"preferred": true` and sorted first.

```python
update_preferences(
    blocked_companies=["Acme Corp"],
    preferred_companies=["Initech"],
    blocked_keywords=["unpaid internship"],
)
search_jobs("software engineer", "New York, NY",
            salary_min=140000, seniority="senior")
tailor_application(job_id)  # uses your saved profile
```

## Governance

`apply_to_job(..., confirm=True)` is gated through your agentic governance
framework ([agentic-governance](https://github.com/paulthorson/agentic-governance))
when it is installed. Discovery order: `GOVERNANCE_ROOT` env var, then
`~/agentic-governance`, then `~/adversarial-agents`. Without it, behavior is
unchanged.

The gate runs **before** any browser submission or local logging, in this
order:

1. **Constitutional veto screen** (`universal` domain) on a neutral summary
   of the intended application, plus an advisory adversarial review whose
   prompt is returned for the calling agent to execute.
2. **Cover-letter honesty check** — the letter is veto-scanned, and any
   skills/years-of-experience it claims that your profile doesn't support
   block the application. Don't claim what you can't back up.
3. **Qualification assessment** — required skills and years of experience
   are extracted from the job description and scored against your profile
   (`profiles/profile.json`, via the onboarding wizard). Score ≥ 0.65
   proceeds silently; 0.40–0.65 proceeds with a `qualification_warning`;
   below 0.40 (or a severe experience gap) blocks.

Fail-open / fail-closed policy:

| Check | On framework error |
|---|---|
| Veto screen | **Fail closed** — blocks (`governance_error`) |
| Cover-letter honesty | Fail closed on framework errors; heuristic errors warn |
| Qualification | **Fail open** — warns, never blocks; missing profile warns (`qualification_unknown`) but never blocks |
| Adversarial review | Advisory — warns, never blocks |

A blocked application returns `{"status": "governance_blocked", "reason": ...}`
and records a veto verdict in the governance ledger — but **nothing is
submitted and nothing is logged to `applications.json`**. Only a human can
clear a veto: fix the application/profile/cover letter and re-run (the
framework's `overturn_verdict` tool also exists for its own ledger).

`governance_status()` reports whether the framework is active, its root, and
its domains. Verdicts are written to the framework's `runs/verdicts.jsonl`,
or to `runs/governance-verdicts.jsonl` here when the framework checkout
isn't writable; override with `GOVERNANCE_VERDICT_LOG`.

## Testing

The suite lives in `tests/` and uses only the standard library
(`unittest` — no extra test dependencies).

```bash
# run everything with a per-module summary table
.venv/bin/python tests/run.py
# or plain unittest discovery
.venv/bin/python -m unittest discover -s tests
# verbose
.venv/bin/python tests/run.py -v
```

| Module | What it covers |
|---|---|
| `test_sanity` | `py_compile` on every project `.py`; MCP stdio smoke test (initialize → `tools/list` shows the expected tools); CLI `--help` exits 0 and `boards` lists boards (read-only) |
| `test_unit_providers` | Provider parsers fed realistic fixtures (Greenhouse/Lever/Ashby API JSON, LinkedIn guest-API HTML cards, Indeed HTML): asserts the canonical job-dict shape (`id/title/company/location/url/board/snippet`) and job-ID encode→decode round-tripping. Unimplemented providers skip with a clear reason |
| `test_unit_forms` | Form logic on a fake page (no browser): hidden/submit/invisible inputs excluded from detection; `full_name` splitting (explicit first/last win); email/phone/location/linkedin/cover-letter mapping; resume uploaded only when the file exists; checkboxes/radios skipped; empty profile doesn't crash |
| `test_unit_profile_resume` | LinkedIn export-ZIP parsing (crafted `Profile.csv`/`Positions.csv`/`Education.csv`/`Skills.csv`), profile merging, interactive wizard via mocked input (writes to a temp dir, never the real profile), resume Markdown/HTML generation and escaping |
| `test_e2e` | **Real browsers**: drives headless Chromium *and* Firefox (Playwright) against a local test form — `confirm=False` fills + screenshots without submitting, `confirm=True` submits and lands on `?applied=1`. **Live**: `search_jobs("software engineer", "New York, NY", board="all")` through the real server code must return results from at least one provider |

### Installing browsers

```bash
.venv/bin/python -m playwright install chromium firefox
# smaller headless-only shell builds also work:
.venv/bin/python -m playwright install --only-shell chromium
```

On Debian/Ubuntu the browsers may also need system libraries:
`sudo .venv/bin/python -m playwright install-deps`.

### Sandbox caveat

In this sandbox the Playwright CDN (`cdn.playwright.dev`) accepts the
connection but the file transfer stalls, so neither Chromium nor Firefox
could be downloaded here. The browser E2E tests detect this at runtime
(`tests/browsers.py` probes each browser with a real launch) and **skip
gracefully** instead of failing. On any machine where the browsers install
cleanly, the same tests run for real — no code changes needed.

Note on Firefox: Playwright drives Firefox (Gecko) through its own driver
rather than the legacy Marionette protocol, but it exercises the same
Gecko engine end-to-end. The `browser_kind` parameter on
`browser_apply.apply_via_browser` (`"chromium"` default, `"firefox"`
optional) selects the engine.
