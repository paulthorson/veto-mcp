import { Card, CodeBlock, Heading } from '@astryxdesign/core';
import { GITHUB_URL, PxBtn, PxTag } from '../px';

/* In-page TOC link: scrolls without touching the hash, so the
   hash router keeps rendering this page. */
function TocLink({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <a
      href="#/docs"
      onClick={(e) => {
        e.preventDefault();
        document.getElementById(id)?.scrollIntoView();
      }}
    >
      {children}
    </a>
  );
}

function Code({ code, language }: { code: string; language: string }) {
  return (
    <div className="px-code">
      <CodeBlock code={code} language={language} hasCopyButton />
    </div>
  );
}

const QUICKSTART = `git clone https://github.com/paulthorson/job-apply-mcp
cd job-apply-mcp
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python wizard.py        # or: .venv/bin/python cli.py wizard`;

const FIRST_SEARCH = `.venv/bin/python cli.py search "software engineer" --location "New York, NY"
.venv/bin/python cli.py show <job_id>
.venv/bin/python cli.py apply <job_id> --resume ~/resume.pdf            # dry run
.venv/bin/python cli.py apply <job_id> --resume ~/resume.pdf --confirm  # for real`;

const MCP_CONFIG = `{
  "mcpServers": {
    "veto": {
      "command": "/home/hatch/workspace/job-apply-mcp/.venv/bin/python",
      "args": ["/home/hatch/workspace/job-apply-mcp/server.py"],
      "env": {}
    }
  }
}`;

interface ToolRow {
  name: string;
  desc: string;
}

interface ToolGroup {
  label: string;
  tools: ToolRow[];
}

const TOOL_GROUPS: ToolGroup[] = [
  {
    label: 'Search',
    tools: [
      { name: 'search_jobs', desc: 'One query across every enabled board. Deduped, ranked, tier-tagged.' },
      { name: 'get_job_details', desc: 'Full posting text for a job id.' },
      { name: 'list_boards', desc: 'Which boards are enabled, their tier, and their current status.' },
    ],
  },
  {
    label: 'Apply',
    tools: [
      { name: 'apply_to_job', desc: 'Dry-run preview by default; confirm=True records it. Governed end to end.' },
      { name: 'tailor_application', desc: 'Per-job resume + cover letter from your profile. Never invents.' },
      { name: 'easy_apply_fill', desc: 'Fills the LinkedIn Easy Apply modal and stops at review. Never submits.' },
      { name: 'apply_via_ats', desc: 'Official ATS endpoints only; honest errors where nothing verified exists.' },
    ],
  },
  {
    label: 'Grill',
    tools: [
      { name: 'grill_start', desc: 'Opens a grill session: deterministic questions from the gaps in your profile.' },
      { name: 'grill_status', desc: 'Answers so far. The application stays grill_pending until you finish.' },
    ],
  },
  {
    label: 'Queue',
    tools: [
      { name: 'queue_add', desc: 'Parks a job in the paced application queue.' },
      { name: 'queue_list', desc: "What's queued, what's waiting on the grill, what's done. (CLI: queue-run)" },
    ],
  },
  {
    label: 'Email',
    tools: [
      { name: 'scan_recruiter_emails', desc: 'Classifies recruiter mail; proposes stage updates only on confident matches.' },
      { name: 'draft_followup_email', desc: 'Check-in / thank-you / nudge drafts. Sending needs your explicit confirm.' },
    ],
  },
  {
    label: 'Tracking',
    tools: [
      { name: 'track_applications', desc: 'Your recorded applications and their pipeline stages.' },
      { name: 'application_analytics', desc: 'Funnel, response rate by board, median time to reply, stale items.' },
    ],
  },
  {
    label: 'Prep',
    tools: [
      { name: 'company_brief', desc: 'Company facts. Anything unfetched is marked unverified, never invented.' },
      { name: 'prep_interview', desc: 'STAR stories built only from your real achievements, metrics verbatim.' },
    ],
  },
  {
    label: 'System',
    tools: [
      { name: 'risk_status', desc: 'Live audit: board tiers, budgets used, registered plugins, cooldowns.' },
      { name: 'doctor', desc: 'Setup health check: profile, keys, boards, channels. (Also a CLI command.)' },
    ],
  },
];

const TROUBLESHOOTING = [
  {
    q: 'Indeed returns 403s',
    a: 'Indeed is heavily bot-protected from datacenter IPs. This is expected, not a bug. The fallback is the browser hook with a logged-in session: set JOB_MCP_BROWSER_APPLY=1 and confirm explicitly.',
  },
  {
    q: 'LinkedIn rate-limits (429)',
    a: 'Back off and let the circuit breaker do its job — it cools the board down for an hour, doubling on repeat blocks. Hammering it will only make the timeout longer.',
  },
  {
    q: 'A board shows as unavailable',
    a: 'Glassdoor is a stub — it says so to your face instead of failing weirdly. Adzuna needs a free API key from developer.adzuna.com before it activates.',
  },
  {
    q: 'Easy Apply fill broke',
    a: 'Scraping-tier boards change their markup without telling anyone. If the modal flow breaks after a LinkedIn redesign, report it on GitHub — selectors get fixed, it just takes a few days.',
  },
  {
    q: 'The grill never completes',
    a: 'The application stays grill_pending until every question is answered. Check grill_status for what\u2019s missing. Gmail replies need the [grill:<id>] subject tag to be matched.',
  },
];

export default function DocsPage() {
  return (
    <div className="page">
      <main>
        {/* HERO */}
        <section className="hero page-hero">
          <div className="wrap">
            <a className="back-link" href="#/">
              ← Home
            </a>
            <PxTag>Docs</PxTag>
            <Heading level={1} className="hero-title page-title">
              READ THE MANUAL.
            </Heading>
            <p className="hero-sub">
              Everything you need to run Veto. No sales pitch — you already
              read that part.
            </p>
            <nav className="docs-toc" aria-label="Docs sections">
              <TocLink id="quickstart">Quickstart</TocLink>
              <TocLink id="connect">Connect</TocLink>
              <TocLink id="wizard">Wizard</TocLink>
              <TocLink id="tools">Tools</TocLink>
              <TocLink id="risk">Risk policy</TocLink>
              <TocLink id="troubleshooting">Troubleshooting</TocLink>
            </nav>
          </div>
        </section>

        {/* QUICKSTART */}
        <section id="quickstart" className="section docs-sec">
          <div className="wrap">
            <PxTag variant="amber">01</PxTag>
            <Heading level={2} className="section-title">
              Quickstart
            </Heading>
            <p className="section-sub">
              Five minutes, no API keys. (Adzuna is the one exception — more
              below.)
            </p>
            <Code code={QUICKSTART} language="bash" />
            <p className="section-sub">Then take it for a spin:</p>
            <Code code={FIRST_SEARCH} language="bash" />
          </div>
        </section>

        <div className="px-hr" aria-hidden="true" />

        {/* CONNECT */}
        <section id="connect" className="section docs-sec">
          <div className="wrap">
            <PxTag variant="amber">02</PxTag>
            <Heading level={2} className="section-title">
              Connect your assistant
            </Heading>
            <p className="section-sub">
              Paste into your MCP client&rsquo;s config (Claude Desktop,
              Cursor, Muse CLI — anything speaking MCP). Merge it into the
              existing <code>mcpServers</code> object; don&rsquo;t replace the
              file. Restart the client afterwards.
            </p>
            <Code code={MCP_CONFIG} language="json" />
          </div>
        </section>

        <div className="px-hr" aria-hidden="true" />

        {/* WIZARD */}
        <section id="wizard" className="section docs-sec">
          <div className="wrap">
            <PxTag variant="amber">03</PxTag>
            <Heading level={2} className="section-title">
              The wizard
            </Heading>
            <p className="section-sub">
              Run it once. It collects exactly three things and then gets out
              of your way.
            </p>
            <div className="steps">
              <Card className="step-card">
                <div className="step-n" aria-hidden="true">[01]</div>
                <Heading level={3} className="feature-title">Profile</Heading>
                <p className="feature-body">
                  Import a LinkedIn data-export ZIP (recommended) or answer a
                  few questions. This is the ground truth every veto check
                  runs against — keep it honest.
                </p>
              </Card>
              <Card className="step-card">
                <div className="step-n" aria-hidden="true">[02]</div>
                <Heading level={3} className="feature-title">Channel</Heading>
                <p className="feature-body">
                  Where the grill reaches you: chat (default, zero setup),
                  WhatsApp, or Gmail. Each downstream user connects their own.
                </p>
              </Card>
              <Card className="step-card">
                <div className="step-n" aria-hidden="true">[03]</div>
                <Heading level={3} className="feature-title">Risk acknowledgment</Heading>
                <p className="feature-body">
                  You explicitly accept the scraping-tier ToS risk before
                  those boards unlock. Recorded with a timestamp in{' '}
                  <code>compliance.json</code>. No acknowledgment, no scraping.
                </p>
              </Card>
            </div>
          </div>
        </section>

        <div className="px-hr" aria-hidden="true" />

        {/* TOOL REFERENCE */}
        <section id="tools" className="section docs-sec">
          <div className="wrap">
            <PxTag variant="amber">04</PxTag>
            <Heading level={2} className="section-title">
              Tool reference
            </Heading>
            <p className="section-sub">
              Every MCP tool, one line each. Same names in the CLI where a
              twin exists (<code>search</code>, <code>show</code>,{' '}
              <code>apply</code>, <code>doctor</code>, <code>queue-add</code>,{' '}
              <code>queue-list</code>, <code>queue-run</code>).
            </p>
            {TOOL_GROUPS.map((g) => (
              <div key={g.label} className="tool-group">
                <h4>{g.label}</h4>
                {g.tools.map((t) => (
                  <div key={t.name} className="tool-row">
                    <span className="tool-name">{t.name}</span>
                    <p className="tool-desc">{t.desc}</p>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </section>

        <div className="px-hr" aria-hidden="true" />

        {/* RISK POLICY */}
        <section id="risk" className="section docs-sec">
          <div className="wrap narrow">
            <PxTag variant="red">05</PxTag>
            <Heading level={2} className="section-title">
              Risk policy
            </Heading>
            <p className="section-sub">
              The rules the agent cannot argue with. Enforced in code, not in
              prompts.
            </p>
            <div className="limits">
              <div className="limit-item">
                <span className="limit-n" aria-hidden="true">▸</span>
                <p>
                  <strong>Two tiers.</strong> Official (Greenhouse, Lever,
                  Ashby, Adzuna) vs scraping (LinkedIn, Indeed, ZipRecruiter).
                  Glassdoor stays locked.
                </p>
              </div>
              <div className="limit-item">
                <span className="limit-n" aria-hidden="true">▸</span>
                <p>
                  <strong>Search budgets:</strong> 1000/day per official
                  board, 40/day per scraping board. Small by design.
                </p>
              </div>
              <div className="limit-item">
                <span className="limit-n" aria-hidden="true">▸</span>
                <p>
                  <strong>Application cap:</strong> 5 per day across all
                  boards, with random 2–7 minute pauses between them. No bulk
                  blasts, ever.
                </p>
              </div>
              <div className="limit-item">
                <span className="limit-n" aria-hidden="true">▸</span>
                <p>
                  <strong>Circuit breaker:</strong> a 403, 429, or CAPTCHA
                  trips a 1-hour cooldown, doubling on repeat blocks, capped at
                  24 hours. CAPTCHAs are never bypassed.
                </p>
              </div>
              <div className="limit-item">
                <span className="limit-n" aria-hidden="true">▸</span>
                <p>
                  <strong>Fill-only:</strong> on scraping-tier boards the
                  agent may fill a form but never perform the final submit
                  click. The human reviews and submits. Policy, not preference.
                </p>
              </div>
            </div>
          </div>
        </section>

        <div className="px-hr" aria-hidden="true" />

        {/* TROUBLESHOOTING */}
        <section id="troubleshooting" className="section docs-sec">
          <div className="wrap narrow">
            <PxTag variant="red">06</PxTag>
            <Heading level={2} className="section-title">
              Troubleshooting
            </Heading>
            <p className="section-sub">
              The greatest hits. If it&rsquo;s not here, it&rsquo;s a bug —
              report it.
            </p>
            <div className="faq">
              {TROUBLESHOOTING.map((t) => (
                <details key={t.q} className="faq-item">
                  <summary className="faq-q">{t.q}</summary>
                  <p className="faq-a">{t.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="section cta">
          <div className="wrap narrow cta-inner">
            <p className="game-over">— press start —</p>
            <Heading level={2} className="section-title">
              Manual read. Now play.
            </Heading>
            <div className="hero-ctas center">
              <PxBtn variant="primary" href="#/install" label="Get started">
                ▶ Get started
              </PxBtn>
              <PxBtn variant="secondary" href={GITHUB_URL} label="View on GitHub">
                View on GitHub
              </PxBtn>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
