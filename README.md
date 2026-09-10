# Job Apply MCP Server

An MCP (Model Context Protocol) server that lets an AI agent **search jobs
across major boards** and **help apply without manual form filling**.

## Tools

| Tool | Description |
|---|---|
| `search_jobs(query, location, board="all", limit=10, remote_only=False)` | Search postings. Returns jobs with `id`, `title`, `company`, `location`, `url`, `board`, `snippet`. |
| `get_job_details(job_id)` | Full description, requirements, and `apply_url` for one job. |
| `apply_to_job(job_id, resume_path, cover_letter="", answers={}, confirm=False)` | **Dry-run preview by default.** Only with `confirm=True` is the application recorded in `applications.json`. Never auto-submits. |
| `list_boards()` | Supported boards and their status (`active` / `stub`). |
| `track_applications()` | Everything recorded in `applications.json`. |

## Boards

- **Indeed** — active. Scrapes public search (`https://www.indeed.com/jobs`) with
  resilient selectors (falls back across markup generations).
- **LinkedIn** — active. Uses the public guest API
  (`/jobs-guest/jobs/api/seeMoreJobPostings/search`, no auth).
- **Glassdoor / ZipRecruiter** — stubs with clear TODOs (JS-rendered and
  bot-protected; need the Phase 2 browser hook).

### Live-test status (2026-09-09, sandbox)

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

## How applying works (Phase 1)

1. `search_jobs` → pick a job → `get_job_details` to read the description.
2. `apply_to_job(job_id, resume_path, ...)` **without** `confirm` returns a
   dry-run preview: job info, resume check, typical form fields, direct
   `apply_url`.
3. Re-call with `confirm=True` → the application is appended to
   `applications.json` with status `confirmed`, and you get the `apply_url`
   to finish submitting in your browser.

**Phase 2 (stub):** a commented hook in `server.py` sketches Playwright-based
form filling for a future release. It is intentionally not implemented yet.

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
- Job data returned is a snapshot; always verify details on the live posting
  before applying.

## Project layout

```
job-apply-mcp/
├── server.py           # MCP server (providers, tools, Phase 2 stub)
├── requirements.txt
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
