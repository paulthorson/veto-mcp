import { useEffect, useRef, useState } from 'react';
import {
  Badge,
  Button,
  Card,
  CodeBlock,
  Divider,
  Heading,
  Link,
} from '@astryxdesign/core';

const GITHUB_URL = 'https://github.com/paulthorson/job-apply-mcp';

/* ------------------------------------------------------------------ */
/* Terminal demo                                                       */
/* ------------------------------------------------------------------ */

type DemoLine = { text: string; kind: 'cmd' | 'ok' | 'info' | 'warn' };

const DEMO_LINES: DemoLine[] = [
  { text: 'cli.py search "software engineer" --location "New York, NY"', kind: 'cmd' },
  { text: '✓ 24 jobs — LinkedIn · Greenhouse · Lever · Ashby', kind: 'ok' },
  { text: '  senior backend engineer · fintech · NYC · linkedin', kind: 'info' },
  { text: '  platform engineer · devtools · remote · greenhouse', kind: 'info' },
  { text: '  staff sre · infra · NYC · lever', kind: 'info' },
  { text: 'cli.py apply job:linkedin:9f2c… --resume ~/resume.pdf', kind: 'cmd' },
  { text: '→ dry run: nothing submitted. re-run with --confirm.', kind: 'warn' },
  { text: '→ governance: qualified (0.87) · veto check passed', kind: 'ok' },
  { text: 'cli.py apply job:linkedin:9f2c… --resume ~/resume.pdf --confirm', kind: 'cmd' },
  { text: '✓ recorded — finish submitting at the apply link', kind: 'ok' },
];

function TerminalDemo() {
  const [shown, setShown] = useState<DemoLine[]>([]);
  const [partial, setPartial] = useState('');
  const timers = useRef<number[]>([]);

  useEffect(() => {
    let lineIdx = 0;
    let charIdx = 0;
    let cancelled = false;

    const later = (fn: () => void, ms: number) => {
      const id = window.setTimeout(() => {
        if (!cancelled) fn();
      }, ms);
      timers.current.push(id);
    };

    const step = () => {
      if (lineIdx >= DEMO_LINES.length) {
        later(() => {
          lineIdx = 0;
          charIdx = 0;
          setShown([]);
          setPartial('');
          step();
        }, 5000);
        return;
      }
      const line = DEMO_LINES[lineIdx];
      if (line.kind === 'cmd') {
        if (charIdx <= line.text.length) {
          setPartial(line.text.slice(0, charIdx));
          charIdx += 1;
          later(step, 24 + Math.random() * 30);
        } else {
          setShown((s) => [...s, line]);
          setPartial('');
          lineIdx += 1;
          charIdx = 0;
          later(step, 350);
        }
      } else {
        setShown((s) => [...s, line]);
        lineIdx += 1;
        later(step, 500);
      }
    };

    later(step, 800);
    return () => {
      cancelled = true;
      timers.current.forEach(clearTimeout);
    };
  }, []);

  return (
    <div className="terminal" role="img" aria-label="Animated demo: searching jobs, dry-run apply, governance check, confirmed apply">
      <div className="terminal-bar">
        <span className="dot r" />
        <span className="dot y" />
        <span className="dot g" />
        <span className="terminal-title">jobapply — zsh</span>
      </div>
      <div className="terminal-body">
        {shown.map((l, i) => (
          <div key={i} className={`tline t-${l.kind}`}>
            {l.kind === 'cmd' ? <span className="prompt">$ </span> : null}
            {l.text}
          </div>
        ))}
        {partial && (
          <div className="tline t-cmd">
            <span className="prompt">$ </span>
            {partial}
            <span className="caret" />
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Data                                                                */
/* ------------------------------------------------------------------ */

const PROVIDERS = [
  { name: 'LinkedIn', note: 'guest API, no login', variant: 'success' as const },
  { name: 'Indeed', note: 'public search', variant: 'success' as const },
  { name: 'Greenhouse', note: 'public API', variant: 'success' as const },
  { name: 'Lever', note: 'public API', variant: 'success' as const },
  { name: 'Ashby', note: 'public API', variant: 'success' as const },
  { name: 'Adzuna', note: 'API key', variant: 'info' as const },
  { name: 'Glassdoor', note: 'soon', variant: 'neutral' as const },
  { name: 'ZipRecruiter', note: 'soon', variant: 'neutral' as const },
];

const FEATURES = [
  {
    icon: '◎',
    title: 'Multi-board search',
    body: 'One query fans out across LinkedIn, Indeed, Greenhouse, Lever, Ashby and Adzuna — deduped, ranked, returned as clean structured data.',
  },
  {
    icon: '▶',
    title: 'Agentic browser apply',
    body: 'Phase 2 drives a real Chromium form: detects fields, fills from your profile, uploads your resume, screenshots everything. Submit only ever fires on your explicit confirm.',
  },
  {
    icon: '✎',
    title: 'Per-job resume tailoring',
    body: 'Each application gets a resume and cover letter tuned to the posting — reordering and rephrasing what you actually have. Never invents experience.',
  },
  {
    icon: '◈',
    title: 'Governance & qualification gates',
    body: 'Every confirmed apply passes constitutional veto checks, a fit score against the job requirements, and lands in an auditable verdict ledger.',
  },
  {
    icon: '⌁',
    title: 'MCP + CLI, same engine',
    body: 'Any MCP client — Claude Desktop, Cursor, Muse CLI — gets the full toolset, and cli.py mirrors it all in the terminal with --json for scripting.',
  },
  {
    icon: '⛉',
    title: 'Onboarding wizard',
    body: 'Answer a few questions, drop in your LinkedIn data export, and get a saved profile plus a generated resume (Markdown, HTML, PDF).',
  },
  {
    icon: '◉',
    title: 'Job watches',
    body: 'Save a search and get alerted when new matching roles appear. Built cron-friendly so it can check on a schedule.',
  },
  {
    icon: '☰',
    title: 'Application lifecycle',
    body: 'Track every application from applied → interviewing → offer (or rejected), with follow-up nudges and response-rate analytics.',
  },
  {
    icon: '⬢',
    title: 'CI/CD + Docker',
    body: 'GitHub Actions runs the full test suite on every push; tagged releases ship a Docker image to GHCR. Dependabot keeps it fresh.',
  },
];

const STEPS = [
  {
    n: '01',
    title: 'Connect your profile',
    body: 'Run the onboarding wizard once. Answer a few questions or import your LinkedIn data export — it builds your saved applicant profile and generates your resume.',
  },
  {
    n: '02',
    title: 'Search & tailor',
    body: 'Your agent searches every board at once, reads the full descriptions, scores each role against your profile, and tailors your resume and cover letter per job.',
  },
  {
    n: '03',
    title: 'Review & confirm',
    body: 'Every application starts as a dry-run preview. Governance checks run, you review, and only your explicit confirm records or submits anything.',
  },
];

const FAQS = [
  {
    q: 'Does it submit applications by itself?',
    a: 'No. apply_to_job returns a dry-run preview by default and records nothing. Only an explicit confirm=True (or the CLI --confirm flag) records an application — and even then, Phase 1 just logs it locally and hands you the apply link to finish in your browser. Browser auto-submit is opt-in behind an environment variable.',
  },
  {
    q: 'Will I get banned from LinkedIn or Indeed?',
    a: 'Honest answer: scraping can violate their Terms of Service, and automated applying carries real risk — CAPTCHAs, throttles, account limits. The server stores no credentials, adds politeness delays, applies at human pace, and warns loudly. Use it as an assistant, not a bulk blaster.',
  },
  {
    q: 'Which boards work best?',
    a: 'Greenhouse, Lever and Ashby — they expose public JSON APIs with no login, so they are fast and reliable. LinkedIn\u2019s guest API works but rate-limits occasionally. Indeed is heavily bot-protected from datacenter IPs; the browser hook with a logged-in session is the fallback there.',
  },
  {
    q: 'Do I need any API keys?',
    a: 'No — everything works keyless except Adzuna, which needs a free developer key from developer.adzuna.com to activate. Without it, that provider simply reports itself as unavailable.',
  },
  {
    q: 'Which AI assistants can use it?',
    a: 'Any MCP-capable client: Claude Desktop, Muse CLI, Cursor, and anything else that speaks the Model Context Protocol. Prefer the terminal? cli.py exposes the same engine with no MCP setup at all.',
  },
];

const INSTALL_BASH = `git clone https://github.com/paulthorson/job-apply-mcp.git
cd job-apply-mcp
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python cli.py wizard   # build your profile (LinkedIn import optional)`;

const INSTALL_MCP = `{
  "mcpServers": {
    "job-apply": {
      "command": "/home/hatch/workspace/job-apply-mcp/.venv/bin/python",
      "args": ["/home/hatch/workspace/job-apply-mcp/server.py"],
      "env": {}
    }
  }
}`;

const INSTALL_CLI = `.venv/bin/python cli.py search "software engineer" --location "New York, NY"
.venv/bin/python cli.py show <job_id>
.venv/bin/python cli.py apply <job_id> --resume ~/resume.pdf   # dry run
.venv/bin/python cli.py apply <job_id> --resume ~/resume.pdf --confirm`;

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function App() {
  return (
    <div className="page">
      <header className="nav">
        <div className="nav-inner">
          <a className="brand" href="#top" aria-label="JobApply MCP home">
            <span className="brand-mark" aria-hidden="true">✓</span>
            <span className="brand-name">JobApply&nbsp;MCP</span>
          </a>
          <nav className="nav-links" aria-label="Sections">
            <a href="#features">Features</a>
            <a href="#how">How it works</a>
            <a href="#governance">Governance</a>
            <a href="#install">Install</a>
            <a href="#faq">FAQ</a>
          </nav>
          <div className="nav-cta">
            <Button variant="ghost" size="sm" href={GITHUB_URL} target="_blank" rel="noreferrer" label="GitHub repository">
              GitHub
            </Button>
            <Button variant="primary" size="sm" href="#install" label="Get started">
              Get started
            </Button>
          </div>
        </div>
      </header>

      <main id="top">
        {/* HERO */}
        <section className="hero">
          <div className="hero-inner">
            <div className="hero-copy">
              <Badge variant="success" label="MCP server for agentic job search" />
              <Heading level={1} type="display-1" className="hero-title">
                Apply to jobs while you&nbsp;sleep.
              </Heading>
              <p className="hero-sub">
                JobApply MCP gives your AI agent one interface to search LinkedIn,
                Indeed, Greenhouse, Lever, Ashby and more — then helps it apply
                without you ever touching a form. You stay in control: every
                application starts as a preview and only submits on your say-so.
              </p>
              <div className="hero-ctas">
                <Button variant="primary" href="#install" label="Get started">
                  Get started
                </Button>
                <Button variant="secondary" href={GITHUB_URL} target="_blank" rel="noreferrer" label="Star on GitHub">
                  ★ Star on GitHub
                </Button>
              </div>
              <p className="hero-note">
                Works with Claude Desktop, Cursor, Muse CLI — any MCP client.
              </p>
            </div>
            <div className="hero-demo">
              <TerminalDemo />
            </div>
          </div>
        </section>

        {/* PROVIDERS */}
        <section className="strip" aria-label="Supported job boards">
          <div className="wrap">
            <p className="strip-label">Searches across the boards you actually use</p>
            <div className="provider-row">
              {PROVIDERS.map((p) => (
                <span key={p.name} className="provider">
                  <Badge variant={p.variant} label={p.name} />
                  <span className="provider-note">{p.note}</span>
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* FEATURES */}
        <section id="features" className="section">
          <div className="wrap">
            <Badge variant="info" label="Features" />
            <Heading level={2} className="section-title">
              Everything between “find me jobs” and “you’re hired”
            </Heading>
            <p className="section-sub">
              One engine, two interfaces — an MCP server for your agent and a CLI
              for you — covering the whole application funnel.
            </p>
            <div className="grid">
              {FEATURES.map((f) => (
                <Card key={f.title} className="feature-card">
                  <div className="feature-icon" aria-hidden="true">{f.icon}</div>
                  <Heading level={3} className="feature-title">{f.title}</Heading>
                  <p className="feature-body">{f.body}</p>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <div className="wrap"><Divider /></div>

        {/* HOW IT WORKS */}
        <section id="how" className="section">
          <div className="wrap">
            <Badge variant="info" label="How it works" />
            <Heading level={2} className="section-title">
              Three steps. Zero forms.
            </Heading>
            <div className="steps">
              {STEPS.map((s) => (
                <Card key={s.n} className="step-card">
                  <div className="step-n" aria-hidden="true">{s.n}</div>
                  <Heading level={3} className="feature-title">{s.title}</Heading>
                  <p className="feature-body">{s.body}</p>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* GOVERNANCE */}
        <section id="governance" className="section gov">
          <div className="wrap">
            <Badge variant="warning" label="The differentiator" />
            <Heading level={2} className="section-title">
              Governed applying, not spray-and-pray
            </Heading>
            <p className="section-sub">
              JobApply MCP runs on an agentic governance framework, so the agent
              applying on your behalf is held to rules — mechanically, not by vibes.
            </p>
            <div className="grid gov-grid">
              <Card className="feature-card">
                <div className="feature-icon" aria-hidden="true">⛨</div>
                <Heading level={3} className="feature-title">Veto gates</Heading>
                <p className="feature-body">
                  Every confirmed application passes constitutional veto checks
                  first. A trip blocks the submission outright — and only a human
                  can clear a veto.
                </p>
              </Card>
              <Card className="feature-card">
                <div className="feature-icon" aria-hidden="true">◐</div>
                <Heading level={3} className="feature-title">Qualification checks</Heading>
                <p className="feature-body">
                  Your profile is scored against each posting’s requirements.
                  Clearly unqualified roles are blocked with an explanation;
                  borderline ones proceed with a visible warning.
                </p>
              </Card>
              <Card className="feature-card">
                <div className="feature-icon" aria-hidden="true">≣</div>
                <Heading level={3} className="feature-title">Verdict ledger</Heading>
                <p className="feature-body">
                  Every pass and block is recorded to an auditable ledger — what
                  was applied to, why it was allowed, and what was stopped.
                </p>
              </Card>
            </div>
          </div>
        </section>

        <div className="wrap"><Divider /></div>

        {/* INSTALL */}
        <section id="install" className="section">
          <div className="wrap">
            <Badge variant="info" label="Install" />
            <Heading level={2} className="section-title">
              Running in five minutes
            </Heading>
            <div className="install-grid">
              <div>
                <Heading level={3} className="install-h">1 · Clone &amp; set up</Heading>
                <CodeBlock code={INSTALL_BASH} language="bash" hasCopyButton />
              </div>
              <div>
                <Heading level={3} className="install-h">2 · Connect your AI assistant</Heading>
                <p className="install-p">
                  Paste into Claude Desktop’s config (or any MCP client’s{' '}
                  <code>mcpServers</code>):
                </p>
                <CodeBlock code={INSTALL_MCP} language="json" hasCopyButton />
              </div>
              <div>
                <Heading level={3} className="install-h">3 · Or just use the terminal</Heading>
                <CodeBlock code={INSTALL_CLI} language="bash" hasCopyButton />
              </div>
            </div>
          </div>
        </section>

        <div className="wrap"><Divider /></div>

        {/* FAQ */}
        <section id="faq" className="section">
          <div className="wrap narrow">
            <Badge variant="info" label="FAQ" />
            <Heading level={2} className="section-title">
              Honest answers
            </Heading>
            <div className="faq">
              {FAQS.map((f) => (
                <details key={f.q} className="faq-item">
                  <summary className="faq-q">{f.q}</summary>
                  <p className="faq-a">{f.a}</p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* FINAL CTA */}
        <section className="section cta">
          <div className="wrap narrow cta-inner">
            <Heading level={2} className="section-title">
              Stop filling out forms.
            </Heading>
            <p className="section-sub">
              Point your agent at the job market. Review the previews. Confirm
              the ones worth your time.
            </p>
            <div className="hero-ctas center">
              <Button variant="primary" href="#install" label="Get started">
                Get started
              </Button>
              <Button variant="secondary" href={GITHUB_URL} target="_blank" rel="noreferrer" label="View on GitHub">
                View on GitHub
              </Button>
            </div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="wrap footer-inner">
          <div>
            <span className="brand">
              <span className="brand-mark" aria-hidden="true">✓</span>
              <span className="brand-name">JobApply&nbsp;MCP</span>
            </span>
            <p className="footer-note">
              Open source. Use at a human pace — and always verify a posting on
              the live site before treating an application as complete.
            </p>
          </div>
          <div className="footer-links">
            <Link href={GITHUB_URL} label="GitHub repository" target="_blank">GitHub repository</Link>
            <Link href={`${GITHUB_URL}#readme`} label="Documentation" target="_blank">Documentation</Link>
            <Link href="#install" label="Install">Install</Link>
          </div>
        </div>
        <div className="wrap footer-base">
          <span>Built with Meta’s Astryx design system.</span>
        </div>
      </footer>
    </div>
  );
}
