import { Card, CodeBlock, Heading } from '@astryxdesign/core';
import { GITHUB_URL, PxBtn, PxTag } from '../px';

/* In-page TOC link: scrolls without touching the hash, so the
   hash router keeps rendering this page. Offset is computed manually
   so the section lands below the sticky nav (scrollIntoView lands
   ~235px off on these padded sections). */
function TocLink({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <a
      href="#/docs"
      onClick={(e) => {
        e.preventDefault();
        const el = document.getElementById(id);
        if (!el) return;
        const top = el.getBoundingClientRect().top + window.scrollY - 96;
        window.scrollTo({ top, behavior: 'smooth' });
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

const QUICKSTART = `git clone https://github.com/paulthorson/veto-mcp
cd veto-mcp
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python wizard.py        # or: .venv/bin/python cli.py wizard`;

const FIRST_SEARCH = `.venv/bin/python cli.py search "software engineer" --location "New York, NY"
.venv/bin/python cli.py show <job_id>
.venv/bin/python cli.py apply <job_id> --resume ~/resume.pdf            # dry run
.venv/bin/python cli.py apply <job_id> --resume ~/resume.pdf --confirm  # for real`;

const MCP_CONFIG = `{
  "mcpServers": {
    "veto": {
      "command": "/absolute/path/to/veto-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/veto-mcp/server.py"],
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

const MODULE_GROUPS: ToolGroup[] = [
  {
    label: 'Score',
    tools: [
      { name: 'score / rank_jobs', desc: 'Fit score 0–100 per posting (skills 50, seniority 15, salary 15, location 15, recency 5). Under 60 is vetoed with a reason; rank_jobs returns the sorted shortlist.' },
      { name: 'decode-jd', desc: 'Reads a posting like a cynic: transparency score, overwork language, vagueness density, green flags. Verdicts of strong, mixed, or caution, every flag quoted.' },
    ],
  },
  {
    label: 'Tailor',
    tools: [
      { name: 'tailor --diff / approve', desc: 'Line-by-line diffs of tailored resume variants. Nothing is final until you approve; variants persist per job.' },
      { name: 'cover-letter draft|scan|approve', desc: 'Fact-grounded drafts; honesty_scan flags invented numbers, companies, and skills before you see the letter.' },
      { name: 'linkedin audit|headline|about|keywords', desc: 'Section scores with fixes, headline/about rewrites from profile facts only, target-role keyword gaps.' },
    ],
  },
  {
    label: 'Train',
    tools: [
      { name: 'mock_interview', desc: 'Five-question sessions (behavioral, technical, company-specific) with deterministic STAR feedback. WhatsApp-compatible output.' },
      { name: 'negotiate', desc: 'Adversarial negotiation sim: firm, hardball, brutal. Labeled coach feedback between rounds.' },
      { name: 'ai_proficiency', desc: 'Seven tracks (engineer, product, data, design, marketing, sales, generalist), diagnostics, 6–7 hands-on lessons each, ethics in every track.' },
      { name: 'mentors', desc: 'Opt-in mentor matching (industry 40, role 25, topics 25, availability 10), first-session agendas, sub-300-char intro drafts you send yourself.' },
    ],
  },
  {
    label: 'Win',
    tools: [
      { name: 'referrals', desc: 'Referral radar: insiders at your target companies from your own connections, with warm-path tracing to reach them.' },
      { name: 'network_crm', desc: 'Network CRM: contacts, interaction history, and warm paths, with a nudge list ranked by staleness.' },
      { name: 'followups', desc: 'Stage-aware follow-up drafts for stale entries. Sending needs your exact approval of recipient, subject, and body.' },
      { name: 'offers', desc: 'Four-year total compensation, adjustable weighted scoring, and what would need to be true for each offer to win.' },
      { name: 'autopsy', desc: 'Rejection autopsy: funnel leak by stage, ghosting rate, and a diagnosis mapped to the module that fixes it.' },
      { name: 'skill_gaps', desc: 'Skill-gap planner: the misses that keep costing you, ranked by frequency, each mapped to the lesson that closes it.' },
      { name: 'streaks', desc: 'Log reps, keep streaks, hit daily goals, and export share cards built only from real logged numbers.' },
    ],
  },
  {
    label: 'Govern',
    tools: [
      { name: 'crew', desc: 'Eleven governed personas (ceo, chief_of_staff, pm, eng, ux, qa, researcher, scout, tailor_agent, coach, red) plus 20 red-team specialists. Spawn > work > review > merge.' },
    ],
  },
];

const TROUBLESHOOTING = [
  {
    q: 'Glassdoor does nothing',
    a: 'Symptom: Glassdoor results never arrive and the board reports itself as unavailable. Why: Glassdoor is a deliberate stub. It stays locked rather than silently failing or returning junk. What to do: nothing; that is the intended behavior. Search the official-tier boards (Greenhouse, Lever, Ashby, Adzuna) for clean coverage.',
  },
  {
    q: 'Adzuna never activates',
    a: 'Symptom: Adzuna stays dark no matter what you do. Why: unlike the other official boards, Adzuna needs credentials before it serves you. What to do: get a free API key at developer.adzuna.com (free tier is enough for job search), then drop it into your config and restart. The board lights up immediately once the key is present.',
  },
  {
    q: 'The grill never completes (grill_pending)',
    a: 'Symptom: your application sits in grill_pending and nothing moves it. Why: the grill stays open until every question has an answer; an unanswered question is a stuck application, by design. What to do: call grill_status to see exactly which questions are still missing, then answer all of them over chat (default) or WhatsApp when bridged. Gmail grill needs a private CLI not included in a normal install — if you do have that CLI, the subject line must carry the [grill:<id>] tag.',
  },
  {
    q: 'Search is blocked: risk acknowledgment missing',
    a: 'Symptom: check_search_allowed refuses a scraping-tier board with a consent error even though nothing is down. Why: standard mode requires an explicit ToS-risk acknowledgment before the scraping tier is allowed; compliance.json has no timestamp for you. Glassdoor is the only board on that tier and is a locked stub (no scraping). What to do: run the wizard (step 03) or call acknowledge_risks to record your consent, or switch to strict mode and use the official-API boards only.',
  },
  {
    q: 'The MCP client does not see the tools',
    a: 'Symptom: Claude Desktop / Cursor / the CLI shows no Veto tools after you edited the config. Why: the usual three: you replaced the whole config file instead of merging into the existing mcpServers object, the command path points at the system python instead of the project .venv, or the client never restarted. What to do: merge, don\'t replace; set the command to the .venv python inside your own checkout (/absolute/path/to/veto-mcp/.venv/bin/python) with args [/absolute/path/to/veto-mcp/server.py]; restart the client completely. If it still fails, run server.py directly in a terminal and read the traceback.',
  },
  {
    q: 'The venv is broken (missing modules, weird errors)',
    a: 'Symptom: imports fail, playwright is "installed" but chromium is missing, or pip errors you have never seen before. Why: the venv got polluted or partially built, usually from mixing system pip with the venv. What to do: delete .venv and rebuild it cleanly: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m playwright install chromium. Reinstall from scratch every time; debugging a sick venv is slower than replacing it.',
  },
  {
    q: 'veto doctor fails',
    a: 'Symptom: veto doctor (or cli.py doctor) reports FAIL on one or more checks. Why: setup is incomplete, and the doctor exists precisely to say which part. What to do: run it with --json if you want machine output, then fix the profile first, it is the most common failure: check_profile wants profile.json with the browser-hook keys, check_preferences wants a parseable preferences.json (missing file means defaults, which is fine), and check_boards wants the board list importable. Errors are hard failures; warnings (Playwright browsers, saved sessions) only degrade Phase 2.',
  },
];

const FAQS = [
  {
    q: 'What is Veto?',
    a: 'A governed job-search machine that finds, tailors, applies, and tracks. Find: one search across every enabled board, deduped and ranked. Tailor: per-job resumes and cover letters grounded in your real profile. Apply: human-paced, confirm-gated, and always fill-only — the software never submits. Track: applications.json holds your pipeline, and the analytics module reads it. The governance is the product: budgets, circuit breakers, honesty checks, and consent gates run in code, not in prompts.',
  },
  {
    q: 'What is Veto not?',
    a: 'Not a mass-apply spammer: 5 applications a day, hard cap, no exceptions. Not a credential thief: nothing in the codebase stores credentials, and there are no logged-in browser sessions or scraping flows at all. Not a lie factory: the tailor module is forbidden from inventing experience, employers, skills, or metrics. Anything unfetched is marked unverified; anything quoted comes from a source you can check.',
  },
  {
    q: 'What does it cost?',
    a: 'Nothing. Free and open source; this GitHub is public, the code is the documentation, and there is no premium tier waiting behind a curtain. The only thing that costs money is infrastructure you choose yourself (API keys, hosting), and the wizard tells you exactly which pieces are paid.',
  },
  {
    q: 'What data does it keep?',
    a: 'Your profile (from the LinkedIn export or wizard answers), applications.json (your recorded applications and stages), compliance.json (mode, risk acknowledgment timestamp, budgets, cooldowns), and grill_sessions.json (your grill answers). compliance.json is gitignored so your consent state never lands in a repo. No credentials are stored anywhere, and no board sessions are created or kept.',
  },
  {
    q: 'Does it submit applications for me?',
    a: 'Never. Every apply starts as a dry-run preview and needs your explicit confirmation to record anything. It is always fill-only: the agent fills the form and stops at the review step; the final submit click is always yours. apply_via_ats returns a dry-run preview (zero network calls) and never submits.',
  },
  {
    q: 'Which boards are supported?',
    a: 'Greenhouse, Lever, and Ashby: public JSON APIs, no login. Adzuna needs a free key from developer.adzuna.com. Glassdoor is a locked stub that performs no scraping; the LinkedIn, Indeed, and ZipRecruiter providers were removed in the post-hardening pass. You can also search your own saved listings (board="user"). Every result is tagged with its risk tier, so you always know what you are looking at.',
  },
  {
    q: 'What honesty guarantees does it make?',
    a: 'The tailor, cover letter, and interview modules never invent experience, employers, skills, or metrics; achievements and numbers are copied verbatim from your profile. The decode-jd module quotes every flag it raises: flags are quoted, not invented. Fit scoring is deterministic, skills 50, seniority 15, salary 15, location 15, recency 5, and postings under 60 are vetoed with a written reason. When a fact is missing, it says unverified instead of filling the gap.',
  },
  {
    q: 'What happens when a board blocks me?',
    a: 'The circuit breaker handles it: a 403, 429, or CAPTCHA calls record_block, which cools the board for 1 hour, doubling on repeat blocks, capped at 24 hours. Cooldowns and timestamps are visible in risk_status any time. CAPTCHAs are never bypassed, full stop. The breaker clears itself after a successful request. If you keep getting blocked, that is the site telling you to stop; use the browser hook or switch boards.',
  },
  {
    q: 'How do the 5/day cap and the fit-score veto relate?',
    a: 'The veto decides who gets one of your five slots. Postings scoring under 60 are vetoed with a reason and never consume a slot. The cap then applies to the survivors: at most 5 applications a day, 2-7 minutes apart. The bar (quality) and the cap (pace) are separate gates; a posting has to clear both to become an application.',
  },
  {
    q: 'How do I get help?',
    a: 'Run veto doctor first. It checks profile, compliance, browsers, sessions, preferences, and boards, and tells you exactly which piece is broken. For bugs, selector drift, or feature ideas, open an issue on GitHub; the report lands in a public queue the maintainer actually reads. For how-it-works questions, this manual and the risk policy section above are the source of truth.',
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
              {'<'} Home
            </a>
            <PxTag>Docs</PxTag>
            <Heading level={1} className="hero-title page-title">
              READ THE MANUAL.
            </Heading>
            <p className="hero-sub">
              Everything you need to run Veto. No sales pitch. You already
              read that part.
            </p>
            <nav className="docs-toc" aria-label="Docs sections">
              <TocLink id="quickstart">Quickstart</TocLink>
              <TocLink id="connect">Connect</TocLink>
              <TocLink id="wizard">Wizard</TocLink>
              <TocLink id="tools">Tools</TocLink>
              <TocLink id="modules">New modules</TocLink>
              <TocLink id="risk">Risk policy</TocLink>
              <TocLink id="troubleshooting">Troubleshooting</TocLink>
              <TocLink id="faq">FAQ</TocLink>
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
              Five minutes, no API keys. (Adzuna is the one exception. More
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
              Cursor, or any MCP client). Merge it into the
              existing <code>mcpServers</code> object; don&rsquo;t replace the
              file. Use the absolute path of your own checkout in place of{' '}
              <code>/absolute/path/to</code>. Restart the client afterwards.
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
                  or WhatsApp when bridged. Gmail grill needs a private
                  CLI not included in a normal install. Each downstream
                  user connects their own.
                </p>
              </Card>
              <Card className="step-card">
                <div className="step-n" aria-hidden="true">[03]</div>
                <Heading level={3} className="feature-title">Risk acknowledgment</Heading>
                <p className="feature-body">
                  You acknowledge the scraping-tier ToS risk before that tier
                  is allowed. Recorded with a timestamp in{' '}
                  <code>compliance.json</code>. No live board scrapes today —
                  Glassdoor is a locked stub — but the gate still applies to
                  the tier machinery.
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

        {/* NEW MODULES */}
        <section id="modules" className="section docs-sec">
          <div className="wrap">
            <PxTag variant="red">05</PxTag>
            <Heading level={2} className="section-title">
              New modules
            </Heading>
            <p className="section-sub">
              The playbooks: seventeen modules around the engine, grouped by
              phase. Same contract everywhere: nothing invented,
              nothing sent without you.
            </p>
            {MODULE_GROUPS.map((g) => (
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
            <PxTag variant="red">06</PxTag>
            <Heading level={2} className="section-title">
              Risk policy
            </Heading>
            <p className="section-sub">
              The rules the agent cannot argue with. Enforced in code, not in
              prompts.
            </p>
            <div className="tool-group">
              <h4>Two tiers</h4>
              <p className="tool-desc">
                Every board is classified once, and every search result is
                stamped with its tier (<code>tos_risk_tier</code>, plus a
                plain-language notice). Official-tier boards expose public or
                official APIs, so they are ToS-friendly and always preferred.
                Scraping-tier boards are reached through HTML or
                guest-endpoint scraping: it works until it doesn&rsquo;t, it
                can violate the site&rsquo;s Terms of Service, and it triggers
                HTTP 403/429, CAPTCHAs, IP rate-limiting, or account
                restrictions. Glassdoor stays locked: it reports itself as a
                stub instead of failing weirdly. No live board currently
                scrapes — the LinkedIn, Indeed, and ZipRecruiter providers
                were removed.
              </p>
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  margin: '16px 0 4px',
                  fontSize: '16px',
                }}
              >
                <thead>
                  <tr
                    style={{
                      textAlign: 'left',
                      borderBottom: '2px solid var(--line)',
                      fontFamily: 'var(--font-px)',
                      fontSize: '12px',
                      color: 'var(--amber)',
                      letterSpacing: '0.04em',
                    }}
                  >
                    <th style={{ padding: '8px 12px 8px 0' }}>Tier</th>
                    <th style={{ padding: '8px 12px 8px 0' }}>Boards</th>
                    <th style={{ padding: '8px 0' }}>Source</th>
                  </tr>
                </thead>
                <tbody style={{ color: 'var(--ink-dim)', lineHeight: 1.5 }}>
                  <tr style={{ borderBottom: '2px dashed var(--line)' }}>
                    <td style={{ padding: '10px 12px 10px 0', fontFamily: 'var(--font-term)', color: 'var(--go)' }}>
                      official
                    </td>
                    <td style={{ padding: '10px 12px 10px 0' }}>
                      Greenhouse, Lever, Ashby, Adzuna
                    </td>
                    <td style={{ padding: '10px 0' }}>
                      Public or official APIs. ToS-clean, preferred.
                    </td>
                  </tr>
                  <tr>
                    <td style={{ padding: '10px 12px 10px 0', fontFamily: 'var(--font-term)', color: 'var(--go)' }}>
                      scraping
                    </td>
                    <td style={{ padding: '10px 12px 10px 0' }}>
                      Glassdoor (locked stub — performs no scraping)
                    </td>
                    <td style={{ padding: '10px 0' }}>
                      No live board scrapes. The tier machinery
                      (budgets, consent, breaker) remains; Glassdoor is
                      a locked stub.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="tool-group">
              <h4>Modes</h4>
              <p className="tool-desc">
                <code>strict</code>: official APIs only. ToS-clean by
                construction, no scraping at all. <code>standard</code>: the
                scraping tier requires explicit risk acknowledgment and keeps
                budgets, circuit-breaker, and tier tags. No live board scrapes;
                Glassdoor remains a locked stub. The mode persists in{' '}
                <code>compliance.json</code>.
              </p>
            </div>
            <div className="tool-group">
              <h4>Search budgets</h4>
              <p className="tool-desc">
                1000 searches per day per official board, 40 per day per
                scraping board. Scraping budgets are deliberately small:
                politeness delays reduce load but do not make scraping
                compliant. Budgets reset at midnight UTC, enforced by{' '}
                <code>check_search_allowed</code> and spent by{' '}
                <code>record_search</code>.
              </p>
            </div>
            <div className="tool-group">
              <h4>Application cap</h4>
              <p className="tool-desc">
                5 recorded applications per day across all boards, with random
                2-7 minute pauses between them (<code>APPLY_PACE_SECONDS</code>{' '}
                120-420), enforced by <code>check_apply_allowed</code>.
                Human-paced by construction. No bulk blasts, ever.
              </p>
            </div>
            <div className="tool-group">
              <h4>Circuit breaker</h4>
              <p className="tool-desc">
                A 403, 429, or CAPTCHA calls <code>record_block</code>, which
                trips a 1-hour cooldown, doubling on repeat blocks, capped at
                24 hours. CAPTCHAs are never bypassed. The breaker resets via{' '}
                <code>record_block_cleared</code> after a successful request.
              </p>
            </div>
            <div className="tool-group">
              <h4>Fill-only</h4>
              <p className="tool-desc">
                The agent fills application forms but never performs
                the final submit click. The human reviews and submits. Every
                apply flow must surface{' '}
                <code>apply_disclosure(board)</code> in its preview, spelling
                out the anti-bot risk and the mitigations in force.
              </p>
            </div>
            <div className="tool-group">
              <h4>Risk acknowledgment</h4>
              <p className="tool-desc">
                <code>acknowledge_risks</code> records your explicit consent,
                with timestamp, in <code>compliance.json</code> (gitignored).
                Until it is recorded, <code>check_search_allowed</code>{' '}
                blocks every scraping-tier board. No acknowledgment, no
                scraping.
              </p>
            </div>
            <div className="tool-group">
              <h4>Enforcement points</h4>
              <div className="tool-row">
                <span className="tool-name">search</span>
                <p className="tool-desc">
                  <code>check_search_allowed</code> gates every provider call;
                  <code>record_search</code> spends daily budget;{' '}
                  <code>record_block</code> trips the circuit breaker.
                </p>
              </div>
              <div className="tool-row">
                <span className="tool-name">apply</span>
                <p className="tool-desc">
                  <code>check_apply_allowed</code> enforces the 5/day cap;
                  apply previews must show{' '}
                  <code>apply_disclosure(board)</code>.
                </p>
              </div>
              <div className="tool-row">
                <span className="tool-name">mode gate</span>
                <p className="tool-desc">
                  <code>is_board_allowed</code> blocks scraping-tier boards
                  outright when the mode is <code>strict</code>.
                </p>
              </div>
              <div className="tool-row">
                <span className="tool-name">live audit</span>
                <p className="tool-desc">
                  The <code>risk_status</code> tool and{' '}
                  <code>status_summary()</code> report boards, budgets used,
                  cooldowns, and cooldown timestamps any time you ask.
                </p>
              </div>
            </div>
          </div>
        </section>

        <div className="px-hr" aria-hidden="true" />

        {/* TROUBLESHOOTING */}
        <section id="troubleshooting" className="section docs-sec">
          <div className="wrap narrow">
            <PxTag variant="red">07</PxTag>
            <Heading level={2} className="section-title">
              Troubleshooting
            </Heading>
            <p className="section-sub">
              The greatest hits. If it&rsquo;s not here, it&rsquo;s a bug.
              Report it.
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

        <div className="px-hr" aria-hidden="true" />

        {/* FAQ */}
        <section id="faq" className="section docs-sec">
          <div className="wrap narrow">
            <PxTag variant="amber">08</PxTag>
            <Heading level={2} className="section-title">
              FAQ
            </Heading>
            <p className="section-sub">
              The questions everyone asks. Short answers, no fog.
            </p>
            <div className="faq">
              {FAQS.map((t) => (
                <details key={t.q} className="faq-item">
                  <summary className="faq-q">{t.q}</summary>
                  <p className="faq-a">{t.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        <div className="px-hr" aria-hidden="true" />

        {/* CTA */}
        <section className="section cta">
          <div className="wrap narrow cta-inner">
            <p className="game-over">- press start -</p>
            <Heading level={2} className="section-title">
              Manual read. Now play.
            </Heading>
            <div className="hero-ctas center">
              <PxBtn variant="primary" href="#/install" label="Start with one job">
                {'>'} Start with one job
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
