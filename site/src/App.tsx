import {
  useEffect,
  useRef,
  useState,
  type MouseEvent,
  type ReactNode,
} from 'react';
import {
  Card,
  CodeBlock,
  Heading,
  Link,
} from '@astryxdesign/core';
import FeaturePage from './pages/FeaturePage';
import DemoPage from './pages/DemoPage';
import DocsPage from './pages/DocsPage';
import DashboardPage from './pages/DashboardPage';
import DecoderPage from './pages/DecoderPage';
import DecoderSharePage from './pages/DecoderSharePage';
import type { PageSpec } from './pages/spec';
import { trackRouteView } from './lib/routeAnalytics';
import { PixelX, PxBtn, PxTag, PixelIcon, GITHUB_URL } from './px';
import disclaimerText from './content/disclaimer.txt?raw';
import privacyText from './content/privacy.txt?raw';
import specSearch from './pages/specs/multi-board-search';
import specGrill from './pages/specs/the-grill';
import specTailoring from './pages/specs/tailoring';
import specFillOnly from './pages/specs/fill-only-apply';
import specQueue from './pages/specs/drip-queue';
import specEmail from './pages/specs/email-sync';
import specPrep from './pages/specs/interview-prep';
import specAnalytics from './pages/specs/lifecycle-analytics';
import specVeto from './pages/specs/veto-gates';
import specHonesty from './pages/specs/honesty-check';
import specQual from './pages/specs/qualification-scoring';
import specLedger from './pages/specs/verdict-ledger';
import specFitScore from './pages/specs/fit-score';
import specJdDecoder from './pages/specs/jd-decoder';
import specReferrals from './pages/specs/referrals';
import specResumeDiffs from './pages/specs/resume-diffs';
import specCoverLetters from './pages/specs/cover-letters';
import specLinkedin from './pages/specs/linkedin';
import specMockInterviews from './pages/specs/mock-interviews';
import specSoftSkills from './pages/specs/soft-skills';
import specAiProficiency from './pages/specs/ai-proficiency';
import specMentors from './pages/specs/mentors';
import specOffers from './pages/specs/offers';
import specFollowups from './pages/specs/followups';
import specNetworkCrm from './pages/specs/network-crm';
import specAutopsy from './pages/specs/autopsy';
import specSkillGaps from './pages/specs/skill-gaps';
import specStreaks from './pages/specs/streaks';
import specCrew from './pages/specs/crew';
import { RadarDemo } from './demos';

const SPECS: Record<string, PageSpec> = {
  [specSearch.slug]: specSearch,
  [specGrill.slug]: specGrill,
  [specTailoring.slug]: specTailoring,
  [specFillOnly.slug]: specFillOnly,
  [specQueue.slug]: specQueue,
  [specEmail.slug]: specEmail,
  [specPrep.slug]: specPrep,
  [specAnalytics.slug]: specAnalytics,
  [specVeto.slug]: specVeto,
  [specHonesty.slug]: specHonesty,
  [specQual.slug]: specQual,
  [specLedger.slug]: specLedger,
  [specFitScore.slug]: specFitScore,
  [specJdDecoder.slug]: specJdDecoder,
  [specReferrals.slug]: specReferrals,
  [specResumeDiffs.slug]: specResumeDiffs,
  [specCoverLetters.slug]: specCoverLetters,
  [specLinkedin.slug]: specLinkedin,
  [specMockInterviews.slug]: specMockInterviews,
  [specSoftSkills.slug]: specSoftSkills,
  [specAiProficiency.slug]: specAiProficiency,
  [specMentors.slug]: specMentors,
  [specOffers.slug]: specOffers,
  [specFollowups.slug]: specFollowups,
  [specNetworkCrm.slug]: specNetworkCrm,
  [specAutopsy.slug]: specAutopsy,
  [specSkillGaps.slug]: specSkillGaps,
  [specStreaks.slug]: specStreaks,
  [specCrew.slug]: specCrew,
};

/* Pixel primitives live in ./px and are shared across pages. */

/* ------------------------------------------------------------------ */
/* Terminal demo                                                        */
/* ------------------------------------------------------------------ */

type DemoLine = { text: string; kind: 'cmd' | 'ok' | 'info' | 'warn' | 'veto' };

const DEMO_LINES: DemoLine[] = [
  { text: 'cli.py search "software engineer" --location "New York, NY"', kind: 'cmd' },
  { text: '+ 24 jobs: Greenhouse · Lever · Ashby · Adzuna', kind: 'ok' },
  { text: '  senior backend eng · fintech · NYC · greenhouse', kind: 'info' },
  { text: '  platform eng · devtools · remote · greenhouse', kind: 'info' },
  { text: '  staff sre · infra · NYC · lever', kind: 'info' },
  { text: 'cli.py apply job:greenhouse:9f2c --resume ~/resume.pdf --confirm', kind: 'cmd' },
  { text: '> grill: 3 questions > WhatsApp ... 3/3 answered +', kind: 'info' },
  { text: '> honesty check: no invented skills +', kind: 'ok' },
  { text: '> qualification 0.87 · veto check passed +', kind: 'ok' },
  { text: '+ RECORDED: finish submitting at the apply link', kind: 'ok' },
  { text: 'cli.py apply job:lever:staff --resume ~/resume.pdf --confirm', kind: 'cmd' },
  { text: 'X VETOED: needs 8+ yrs, profile shows 3. Not applying.', kind: 'veto' },
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
        }, 6000);
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
        later(step, line.kind === 'veto' ? 1100 : 500);
      }
    };

    later(step, 800);
    return () => {
      cancelled = true;
      timers.current.forEach(clearTimeout);
    };
  }, []);

  return (
    <div className="terminal" role="img" aria-label="Animated demo: searching jobs, grill questions answered over WhatsApp, honesty and veto checks, one application recorded, one vetoed">
      <div className="terminal-bar">
        <span className="dot r" />
        <span className="dot y" />
        <span className="dot g" />
        <span className="terminal-title">veto - zsh</span>
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
/* Data                                                                 */
/* ------------------------------------------------------------------ */

const PROVIDERS = [
  { name: 'Greenhouse', note: 'public API', tier: 'go' as const },
  { name: 'Lever', note: 'public API', tier: 'go' as const },
  { name: 'Ashby', note: 'public API', tier: 'go' as const },
  { name: 'Adzuna', note: 'needs API key', tier: 'amber' as const },
  { name: 'Glassdoor', note: 'boss level: locked', tier: 'red' as const },
];

const FEATURES = [
  {
    slug: 'multi-board-search',
    icon: 'search',
    tone: '',
    title: 'Multi-board search',
    body: 'One query across the official-API boards (Greenhouse, Lever, Ashby, Adzuna) plus your saved listings. Deduped, tier-tagged, and ranked.',
  },
  {
    slug: 'the-grill',
    icon: 'question',
    tone: 'red',
    title: 'The grill',
    body: 'Before anything moves, Veto interrogates you: missing skills, unquantified wins, salary, logistics. Chat works by default; WhatsApp when bridged. The application waits for your answers.',
  },
  {
    slug: 'tailoring',
    icon: 'pencil',
    tone: '',
    title: 'Tailoring, minus the lies',
    body: 'Resume bullets reordered around the posting\u2019s keywords, cover letter referencing the actual role. Gaps are reported as gaps. Never padded.',
  },
  {
    slug: 'fill-only-apply',
    icon: 'clipboard',
    tone: 'amber',
    title: 'Fill-only applying',
    body: 'The agent fills the form and stops at the review screen. You click submit — the software never touches the submit button. Policy, not preference.',
  },
  {
    slug: 'drip-queue',
    icon: 'hourglass',
    tone: '',
    title: 'Drip queue',
    body: 'Applications queued at human pace: max 5 a day, random pauses between them. No bulk blasts, ever.',
  },
  {
    slug: 'email-sync',
    icon: 'envelope',
    tone: '',
    title: 'Recruiter email sync',
    body: 'When a private Gmail CLI is available, recruiter mail can be classified and follow-ups drafted. That CLI is not included in a normal install, so email sync is unavailable there. Sending always needs your confirm.',
  },
  {
    slug: 'interview-prep',
    icon: 'chat',
    tone: '',
    title: 'Interview prep',
    body: 'Company briefs with unverified facts marked as such. STAR stories built only from your real wins, metrics preserved verbatim.',
  },
  {
    slug: 'lifecycle-analytics',
    icon: 'chart',
    tone: '',
    title: 'Lifecycle + analytics',
    body: 'applied > interviewing > offer tracking, follow-up nudges, and response rate broken down by board.',
  },
];

const STEPS = [
  {
    n: '01',
    title: 'Build your profile',
    body: 'Run the wizard once. Import your LinkedIn export or answer a few questions. Chat is the default grill channel; WhatsApp when you bridge it.',
  },
  {
    n: '02',
    title: 'Search & grill',
    body: 'Your agent searches every board, scores each role against your profile, and grills you on the gaps before anything is allowed to move.',
  },
  {
    n: '03',
    title: 'Review & confirm',
    body: 'Every application starts as a dry-run preview. The veto checks run, you review, and only your explicit confirm records anything.',
  },
];

const NO_CARDS = [
  {
    slug: 'veto-gates',
    icon: 'x',
    tone: 'red',
    title: 'Veto gates',
    body: 'Every confirmed application passes a constitutional veto screen first. A trip blocks it outright, and only a human can clear a veto.',
  },
  {
    slug: 'honesty-check',
    icon: 'shield',
    tone: 'red',
    title: 'Honesty check',
    body: 'Cover letters are scanned for skills and years your profile can\u2019t back up. Invented experience blocks the application on the spot.',
  },
  {
    slug: 'qualification-scoring',
    icon: 'gauge',
    tone: 'amber',
    title: 'Qualification scoring',
    body: 'Requirements are extracted from the posting and scored against your profile. Clear misses are refused with an explanation; borderline ones proceed with a warning.',
  },
  {
    slug: 'verdict-ledger',
    icon: 'ledger',
    tone: '',
    title: 'Verdict ledger',
    body: 'Every pass and every block lands in an auditable ledger. Ask why anything happened and get an answer.',
  },
];

/* The playbooks: 17 modules grouped by job-hunt phase. Each card links
   to its drill-down feature page. */
const GROUPS = [
  {
    id: 'find',
    tag: 'FIND',
    tagVariant: 'red' as const,
    title: 'Find the right roles',
    sub: 'Score every posting, decode the language, and work your network, before you spend a minute applying.',
    demo: true,
    features: [
      {
        slug: 'fit-score',
        icon: 'target',
        tone: '',
        title: 'Fit score',
        body: 'Every posting scored 0–100 against your profile. Under 60 is vetoed with a reason.',
      },
      {
        slug: 'jd-decoder',
        icon: 'scan',
        tone: 'amber',
        title: 'JD decoder',
        body: 'Overwork language, vagueness, and green flags, called out with the exact quotes.',
      },
      {
        slug: 'referrals',
        icon: 'net',
        tone: '',
        title: 'Referral radar',
        body: 'Insiders at your target companies from your own connections, plus warm-path tracing.',
      },
    ],
  },
  {
    id: 'tailor',
    tag: 'TAILOR',
    tagVariant: '' as const,
    title: 'Tailor without lying',
    sub: 'Resumes, cover letters, and your LinkedIn profile, rewritten around the role. Never around fiction.',
    demo: false,
    features: [
      {
        slug: 'resume-diffs',
        icon: 'diff',
        tone: '',
        title: 'Resume diffs',
        body: 'Line-by-line diffs of every tailored variant, with an approval gate. Nothing ships unapproved.',
      },
      {
        slug: 'cover-letters',
        icon: 'doc',
        tone: '',
        title: 'Cover letters',
        body: 'Fact-grounded drafts, honesty-scanned three ways before you ever see them.',
      },
      {
        slug: 'linkedin',
        icon: 'badge',
        tone: 'amber',
        title: 'LinkedIn optimizer',
        body: 'Section-by-section audit with scores, plus headline and about rewrites from your facts only.',
      },
    ],
  },
  {
    id: 'train',
    tag: 'TRAIN',
    tagVariant: '' as const,
    title: 'Train like it matters',
    sub: 'Mock interviews, adversarial negotiation, AI fluency, and human mentors. The reps that compound.',
    demo: false,
    features: [
      {
        slug: 'mock-interviews',
        icon: 'mic',
        tone: '',
        title: 'Mock interviews',
        body: 'Five-question sessions with deterministic STAR feedback. WhatsApp-compatible.',
      },
      {
        slug: 'soft-skills',
        icon: 'swords',
        tone: 'red',
        title: 'Soft skills + negotiation',
        body: 'Spar against a hardball hiring manager (firm, hardball, brutal), with coach feedback between rounds.',
      },
      {
        slug: 'ai-proficiency',
        icon: 'bolt',
        tone: '',
        title: 'AI proficiency',
        body: 'Seven tracks, hands-on lessons, an ethics module in every one. Employers screen for this now.',
      },
      {
        slug: 'mentors',
        icon: 'chat',
        tone: '',
        title: 'Mentor matchmaking',
        body: 'Opt-in mentors matched deterministically, with first-session agendas and intro drafts you send yourself.',
      },
    ],
  },
  {
    id: 'win',
    tag: 'WIN',
    tagVariant: 'amber' as const,
    title: 'Win the endgame',
    sub: 'Compare offers, follow up relentlessly, learn from rejections, and keep the streak alive.',
    demo: false,
    features: [
      {
        slug: 'offers',
        icon: 'trophy',
        tone: '',
        title: 'Offer comparison',
        body: 'Four-year totals, your weights, and what would need to be true for each offer to win.',
      },
      {
        slug: 'followups',
        icon: 'envelope',
        tone: '',
        title: 'Smart follow-ups',
        body: 'Stage-aware drafts for stale threads. Sending needs your exact approval. Every byte.',
      },
      {
        slug: 'network-crm',
        icon: 'ledger',
        tone: '',
        title: 'Network CRM',
        body: 'Contacts, interaction history, warm paths, and a nudge list ranked by staleness.',
      },
      {
        slug: 'autopsy',
        icon: 'chart',
        tone: 'amber',
        title: 'Rejection autopsy',
        body: 'Where your funnel leaks, diagnosed and mapped to the module that fixes it.',
      },
      {
        slug: 'skill-gaps',
        icon: 'chart',
        tone: '',
        title: 'Skill-gap planner',
        body: 'The misses that keep costing you, ranked by frequency, each mapped to the lesson that closes it.',
      },
      {
        slug: 'streaks',
        icon: 'flame',
        tone: 'red',
        title: 'Streaks',
        body: 'Gamified reps with shareable progress cards built only from real numbers. The viral loop.',
      },
    ],
  },
  {
    id: 'govern',
    tag: 'GOVERN',
    tagVariant: 'red' as const,
    title: 'Governed, all the way down',
    sub: 'A crew of AI personas under a real governance framework. Every plan reviewed, every veto logged.',
    demo: false,
    features: [
      {
        slug: 'crew',
        icon: 'team',
        tone: 'red',
        title: 'Governed AI crew',
        body: 'Eleven personas (CEO, PM, eng, UX, QA, researcher, coach, Red) run spawn > work > review > merge.',
      },
    ],
  },
];

const FAQS = [
  {
    q: 'What are the playbooks?',
    a: 'Seventeen modules grouped by job-hunt phase. FIND scores postings, decodes JDs, and traces referral paths. TAILOR does resume diffs, cover letters, and LinkedIn. TRAIN runs mock interviews, negotiation sims, AI proficiency, and mentors. WIN compares offers, drafts follow-ups, runs the network CRM, autopsies rejections, plans skill gaps, and tracks streaks. GOVERN is the AI crew: every plan reviewed, every veto logged. The engine searches and fills; the playbooks cover everything around it.',
  },
  {
    q: 'Does it submit applications by itself?',
    a: 'No. apply_to_job returns a dry-run preview by default and records nothing. Only an explicit confirm records an application, and even then, Phase 1 just logs it locally and hands you the apply link to finish in your browser. With the browser hook enabled, Phase 2 fills the form and stops at the review screen. The final click is always yours.',
  },
  {
    q: 'What is the grill?',
    a: 'Before a confirmed application proceeds, Veto asks you deterministic questions derived from the gaps between the posting and your profile: missing skills, unquantified experience, salary, logistics, motivation. Chat is the default channel; WhatsApp works when bridged. Gmail grill needs a private CLI not included in a normal install. Answer however you like, even in one compressed line; the parser handles it. Nothing moves until the grill is complete.',
  },
  {
    q: 'Will I get banned from a job board?',
    a: 'The four active providers (Greenhouse, Lever, Ashby, Adzuna) use public or official APIs, so there is no scraping to get banned for. Veto stores no credentials, performs no logged-in automation, and caps recorded applications at 5 a day, paced like a human. Phase 2 browser form-filling can still trip a site\u2019s anti-bot measures, so the filled form is screenshotted for your review and you click submit yourself. Use it as an assistant, not a bulk blaster.',
  },
  {
    q: 'Which boards work best?',
    a: 'Greenhouse, Lever and Ashby: they expose public JSON APIs with no login, so they are fast and reliable. Adzuna needs a free API key from developer.adzuna.com. Glassdoor is a locked stub that performs no scraping, and the LinkedIn, Indeed, and ZipRecruiter providers were removed in the post-hardening pass. You can also paste any posting as a saved listing.',
  },
  {
    q: 'Do I need any API keys?',
    a: 'No. Everything works keyless except Adzuna, which needs a free developer key from developer.adzuna.com to activate. Without it, that provider simply reports itself as unavailable.',
  },
  {
    q: 'Which AI assistants can use it?',
    a: 'Any MCP-capable client: Claude Desktop, Muse CLI, Cursor, and anything else that speaks the Model Context Protocol. Prefer the terminal? cli.py exposes the same engine with no MCP setup at all.',
  },
];

const INSTALL_BASH = `git clone https://github.com/paulthorson/veto-mcp.git
cd veto-mcp
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python cli.py wizard   # profile + channel + risk acknowledgment`;

const INSTALL_MCP = `{
  "mcpServers": {
    "veto": {
      "command": "/absolute/path/to/veto-mcp/.venv/bin/python",
      "args": ["/absolute/path/to/veto-mcp/server.py"],
      "env": {}
    }
  }
}`;

const INSTALL_CLI = `.venv/bin/python cli.py search "software engineer" --location "New York, NY"
.venv/bin/python cli.py show <job_id>
.venv/bin/python cli.py apply <job_id> --resume ~/resume.pdf   # dry run
.venv/bin/python cli.py apply <job_id> --resume ~/resume.pdf --confirm`;

/* ------------------------------------------------------------------ */
/* Routing                                                              */
/* ------------------------------------------------------------------ */

function useRoute(): string {
  const [hash, setHash] = useState(() =>
    typeof window === 'undefined' ? '' : window.location.hash,
  );
  useEffect(() => {
    trackRouteView(window.location.hash);
    const onChange = () => {
      const h = window.location.hash;
      setHash(h);
      trackRouteView(h);
      if (h.startsWith('#/')) window.scrollTo({ top: 0, behavior: 'instant' });
    };
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return hash;
}

/* ------------------------------------------------------------------ */
/* Shared chrome                                                        */
/* ------------------------------------------------------------------ */

function SiteNav({ routeHash }: { routeHash: string }) {
  return (
    <header className="nav">
      <div className="nav-inner">
        <a className="brand" href="#/" aria-label="Veto home">
          <PixelX />
          <span className="brand-name">VETO<span className="x">_</span></span>
        </a>
        <nav className="nav-links" aria-label="Sections">
          <a href="#features">Features</a>
          <a href="#playbooks">Playbooks</a>
          <a href="#how">How it works</a>
          <a href="#why-no">Why it says no</a>
          <a href="#/demo">Demo</a>
          <a href="#/docs">Docs</a>
          <a href="#/install">Install</a>
          <a href="#faq">FAQ</a>
        </nav>
        <div className="nav-cta">
          <PxBtn variant="ghost" href={GITHUB_URL} label="GitHub repository">
            GitHub
          </PxBtn>
          <PxBtn variant="primary" href="#/install" label="Get started">
            Start
          </PxBtn>
        </div>
        <MobileNav routeHash={routeHash} />
      </div>
    </header>
  );
}

/* ------------------------------------------------------------------ */
/* Mobile navigation (<=960px): GitHub icon button + hamburger.         */
/* Links are plain anchors; the existing hash router does all the work. */
/* ------------------------------------------------------------------ */

const MOBILE_SECTIONS = [
  { href: '#features', label: 'Features' },
  { href: '#playbooks', label: 'Playbooks' },
  { href: '#how', label: 'How it works' },
  { href: '#why-no', label: 'Why it says no' },
  { href: '#faq', label: 'FAQ' },
];

const MOBILE_PAGES = [
  { href: '#/demo', label: 'Demo' },
  { href: '#/docs', label: 'Docs' },
  { href: '#/dashboard', label: 'Dashboard' },
];

/* #/install and #install land in the same place; treat them as one. */
const INSTALL_HASHES = new Set(['#/install', '#install']);

function MobileNav({ routeHash }: { routeHash: string }) {
  const [open, setOpen] = useState(false);
  const hamburgerRef = useRef<HTMLButtonElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const wasOpen = useRef(false);

  const close = () => setOpen(false);

  /* Close on any navigation, including browser back/forward while open. */
  useEffect(() => {
    if (wasOpen.current) close();
  }, [routeHash]);

  /* Scroll lock, Escape, focus in/out, and close on resize to desktop. */
  useEffect(() => {
    if (open) {
      wasOpen.current = true;
      document.body.style.overflow = 'hidden';
      closeBtnRef.current?.focus();
      const onKey = (e: KeyboardEvent) => {
        if (e.key === 'Escape') setOpen(false);
        /* Focus trap: keep Tab cycling inside the dialog. */
        if (e.key === 'Tab' && overlayRef.current) {
          const focusables = overlayRef.current.querySelectorAll<HTMLElement>(
            'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
          );
          if (focusables.length === 0) return;
          const first = focusables[0];
          const last = focusables[focusables.length - 1];
          if (e.shiftKey && document.activeElement === first) {
            e.preventDefault();
            last.focus();
          } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      };
      const onResize = () => {
        if (window.innerWidth > 960) setOpen(false);
      };
      window.addEventListener('keydown', onKey);
      window.addEventListener('resize', onResize);
      return () => {
        window.removeEventListener('keydown', onKey);
        window.removeEventListener('resize', onResize);
        document.body.style.overflow = '';
      };
    }
    if (wasOpen.current) {
      wasOpen.current = false;
      document.body.style.overflow = '';
      hamburgerRef.current?.focus();
    }
    return undefined;
  }, [open ]);

  const isActive = (href: string) =>
    href === '#/install' ? INSTALL_HASHES.has(routeHash) : routeHash === href;

  /* Script-set hash avoids Chrome's link-activation focus steal, which
     dropped focus to body after the menu unmounted and killed the
     hamburger.focus() restore. Same-hash taps still close via onClick
     even though no hashchange fires. */
  const link = (href: string, label: string, className: string) => (
    <a
      className={className}
      href={href}
      onClick={(e: MouseEvent<HTMLAnchorElement>) => {
        e.preventDefault();
        close();
        window.location.hash = href;
      }}
      aria-current={isActive(href) ? 'page' : undefined}
    >
      {label}
    </a>
  );

  return (
    <>
      <div className="nav-mobile-actions">
        <a
          className="nav-mobile-gh"
          href={GITHUB_URL}
          aria-label="GitHub repo"
        >
          <PixelIcon name="github" size={20} />
        </a>
        <button
          ref={hamburgerRef}
          type="button"
          className="hamburger"
          aria-expanded={open}
          aria-controls="mobile-menu"
          aria-label="Menu"
          onClick={() => setOpen((v) => !v)}
        >
          <span className="hb-bar" aria-hidden="true" />
          <span className="hb-bar" aria-hidden="true" />
          <span className="hb-bar" aria-hidden="true" />
        </button>
      </div>
      {open && (
        <div
          ref={overlayRef}
          className="mobile-menu"
          id="mobile-menu"
          role="dialog"
          aria-modal="true"
          aria-label="Site menu"
          onClick={close}
        >
          <div className="mobile-menu-head">
            <a
              className="brand"
              href="#/"
              aria-label="Veto home"
              onClick={(e: MouseEvent<HTMLAnchorElement>) => {
                e.preventDefault();
                close();
                window.location.hash = '#/';
              }}
            >
              <PixelX />
              <span className="brand-name">VETO<span className="x">_</span></span>
            </a>
            <button
              ref={closeBtnRef}
              type="button"
              className="mobile-menu-close"
              aria-label="Close menu"
              onClick={close}
            >
              X
            </button>
          </div>
          <nav className="mobile-menu-nav" aria-label="Mobile">
            <p className="mobile-menu-group-label">Sections</p>
            <ul className="mobile-menu-list">
              {MOBILE_SECTIONS.map((l) => (
                <li key={l.href}>
                  {link(l.href, l.label, 'mobile-menu-link')}
                </li>
              ))}
            </ul>
            <p className="mobile-menu-group-label">Pages</p>
            <ul className="mobile-menu-list">
              {MOBILE_PAGES.map((l) => (
                <li key={l.href}>
                  {link(l.href, l.label, 'mobile-menu-link')}
                </li>
              ))}
            </ul>
            <a
              className="mobile-menu-github"
              href={GITHUB_URL}
              aria-label="GitHub repo"
              onClick={close}
            >
              <PixelIcon name="github" size={20} />
              <span>GitHub</span>
            </a>
            <div className="mobile-menu-start">
              {link('#/install', '> Start with one job', 'px-btn secondary mobile-menu-start-btn')}
              <p className="mobile-menu-start-note">
                Nobody installs from a phone. Skim now, clone on a real
                keyboard.
              </p>
            </div>
          </nav>
        </div>
      )}
    </>
  );
}

const LICENSE_URL =
  'https://github.com/paulthorson/veto-mcp/blob/main/LICENSE';
const CONTACT_EMAIL = 'hello@vetomcp.com';

/** Cos SoT prose, byte-faithful; only license cite + mailto are linkified. */
function VerbatimLegal({ text }: { text: string }) {
  const parts: ReactNode[] = [];
  const re = /(Apache License 2\.0|hello@vetomcp\.com)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let key = 0;
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) {
      parts.push(text.slice(last, match.index));
    }
    if (match[0] === 'Apache License 2.0') {
      parts.push(
        <a
          key={key++}
          href={LICENSE_URL}
          target="_blank"
          rel="noreferrer"
        >
          Apache License 2.0
        </a>,
      );
    } else {
      parts.push(
        <a key={key++} href={`mailto:${CONTACT_EMAIL}`}>
          {CONTACT_EMAIL}
        </a>,
      );
    }
    last = match.index + match[0].length;
  }
  if (last < text.length) {
    parts.push(text.slice(last));
  }
  return <p className="footer-legal-text">{parts}</p>;
}

function scrollToPrivacy(e: MouseEvent<HTMLAnchorElement>) {
  e.preventDefault();
  document.getElementById('privacy')?.scrollIntoView({ behavior: 'smooth' });
}

function SiteFooter() {
  return (
    <footer className="footer">
      <div className="wrap footer-inner">
        <div>
          <span className="brand">
            <PixelX size={26} />
            <span className="brand-name">VETO<span className="x">_</span></span>
          </span>
          <p className="footer-note">
            Open source. Veto applies at human pace. Verify every posting on
            the live site before treating an application as complete.
          </p>
        </div>
        <div className="footer-links">
          <Link href={GITHUB_URL} label="GitHub repository" target="_blank">{'>'} GitHub repository</Link>
          <Link href="#/docs" label="Documentation">{'>'} Documentation</Link>
          <Link href="#/install" label="Install">{'>'} Install</Link>
          <Link href="#/dashboard" label="Mission-control dashboard">{'>'} Dashboard</Link>
          <a href="#privacy" onClick={scrollToPrivacy}>
            Privacy
          </a>
        </div>
      </div>
      <div className="wrap footer-legal">
        <section id="privacy" className="footer-privacy" aria-labelledby="privacy-heading">
          <h2 id="privacy-heading" className="footer-privacy-heading">
            Privacy
          </h2>
          <VerbatimLegal text={privacyText} />
        </section>
        <section className="footer-disclaimer" aria-label="Disclaimer">
          <VerbatimLegal text={disclaimerText} />
        </section>
      </div>
      <div className="wrap footer-base">
        <span>Built with Meta&rsquo;s Astryx design system.</span>
        <span>No CAPTCHAs were harmed.</span>
      </div>
    </footer>
  );
}

/* ------------------------------------------------------------------ */
/* Home page                                                            */
/* ------------------------------------------------------------------ */

function HomePage({ routeHash }: { routeHash: string }) {
  useEffect(() => {
    if (routeHash === '#/install' || routeHash === '#install') {
      document.getElementById('install')?.scrollIntoView();
    } else if (
      routeHash.startsWith('#') &&
      !routeHash.startsWith('#/') &&
      routeHash.length > 1
    ) {
      document.getElementById(routeHash.slice(1))?.scrollIntoView();
    } else if (!routeHash.startsWith('#/')) {
      window.scrollTo({ top: 0, behavior: 'instant' });
    }
  }, [routeHash]);

  return (
    <div className="page">
      <main id="top">
        {/* HERO */}
        <section className="hero">
          <div className="hero-inner">
            <div className="hero-copy">
              <PxTag>Open-source MCP server</PxTag>
              <Heading level={1} type="display-1" className="hero-title">
                The job bot that <span className="no">says&nbsp;no.</span>
              </Heading>
              <p className="hero-sub">
                <strong>Veto</strong> plugs your AI assistant into 4 job
                boards (Greenhouse, Lever, Ashby, Adzuna). Its modules handle the rest: fit scoring, radar charts,
                tailored resumes, cover letters, mock interviews, brutal
                negotiation sims, offer comparison, streaks, and a governed AI
                crew. It fills the forms. You click submit. Nothing ships
                without your say-so.
              </p>
              <div className="hero-ctas">
                <PxBtn variant="primary" href="#/install" label="Try it">
                  {'>'} Try it
                </PxBtn>
                <PxBtn variant="secondary" href={GITHUB_URL} label="Star on GitHub">
                  {'*'} Star on GitHub
                </PxBtn>
              </div>
              <p className="hero-note">
                {'>'} works with Claude Desktop, Cursor, Muse CLI, any MCP client_
              </p>
              <p className="hero-note">
                <a href="#/demo" className="demo-docs">or skip ahead: get vetoed in the demo&nbsp;{'>'}</a>
              </p>
              <p className="hero-note">
                {'>'} it won&rsquo;t apply while you sleep, and it won&rsquo;t get you hired. It does the homework.
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
            <p className="strip-label">One query · four boards</p>
            <div className="provider-row">
              {PROVIDERS.map((p) => (
                <span key={p.name} className="provider">
                  <span className={`p-dot ${p.tier}`} aria-hidden="true" />
                  {p.name}
                  <span className="provider-note">{p.note}</span>
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* FEATURES */}
        <section id="features" className="section">
          <div className="wrap">
            <PxTag variant="red">The engine</PxTag>
            <Heading level={2} className="section-title">
              Everything between &ldquo;find me jobs&rdquo; and &ldquo;you&rsquo;re hired&rdquo;
            </Heading>
            <p className="section-sub">
              One engine, two ways in: an MCP server for your agent, a CLI
              for you. Click any card for the full breakdown.
            </p>
            <div className="grid">
              {FEATURES.map((f) => (
                <a
                  key={f.slug}
                  href={`#/features/${f.slug}`}
                  className="card-anchor"
                  aria-label={`${f.title} - learn more`}
                >
                  <Card className="feature-card">
                    <div className={`feature-icon ${f.tone}`} aria-hidden="true"><PixelIcon name={f.icon} /></div>
                    <Heading level={3} className="feature-title">{f.title}</Heading>
                    <p className="feature-body">{f.body}</p>
                    <span className="card-more">Read more&nbsp;{'>'}</span>
                  </Card>
                </a>
              ))}
            </div>
          </div>
        </section>

        <div className="px-hr" aria-hidden="true" />

        {/* PLAYBOOKS */}
        <section id="playbooks" className="section">
          <div className="wrap">
            <PxTag variant="amber">The playbooks</PxTag>
            <Heading level={2} className="section-title">
              17 more modules. One job hunt.
            </Heading>
            <p className="section-sub">
              The engine finds jobs and files applications. The playbooks are
              everything around that, grouped by phase. Each has its own page.
              Most have a live demo.
            </p>
          </div>
          {GROUPS.map((g) => (
            <div key={g.id} className="wrap group-sec">
              <div className="group-head">
                <PxTag variant={g.tagVariant}>{g.tag}</PxTag>
                <Heading level={3} className="section-title">
                  {g.title}
                </Heading>
                <p className="section-sub">{g.sub}</p>
              </div>
              {g.demo ? <RadarDemo /> : null}
              <div className="grid">
                {g.features.map((f) => (
                  <a
                    key={f.slug}
                    href={`#/features/${f.slug}`}
                    className="card-anchor"
                    aria-label={`${f.title} - learn more`}
                  >
                    <Card className="feature-card">
                      <div className={`feature-icon ${f.tone}`} aria-hidden="true"><PixelIcon name={f.icon} /></div>
                      <Heading level={3} className="feature-title">{f.title}</Heading>
                      <p className="feature-body">{f.body}</p>
                      <span className="card-more">Read more&nbsp;{'>'}</span>
                    </Card>
                  </a>
                ))}
              </div>
            </div>
          ))}
        </section>

        <div className="px-hr" aria-hidden="true" />

        {/* HOW IT WORKS */}
        <section id="how" className="section">
          <div className="wrap">
            <PxTag variant="amber">How it works</PxTag>
            <Heading level={2} className="section-title">
              Three steps. Zero forms.
            </Heading>
            <div className="steps">
              {STEPS.map((s) => (
                <Card key={s.n} className="step-card">
                  <div className="step-n" aria-hidden="true">[{s.n}]</div>
                  <Heading level={3} className="feature-title">{s.title}</Heading>
                  <p className="feature-body">{s.body}</p>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* WHY IT SAYS NO */}
        <section id="why-no" className="section gov">
          <div className="wrap">
            <PxTag variant="red">The differentiator</PxTag>
            <Heading level={2} className="section-title">
              Why it says no
            </Heading>
            <p className="section-sub">
              Every other apply-bot is optimized for volume. Veto is optimized
              for not embarrassing you. The refusals are mechanical, not vibes.
              They are enforced by a governance framework with an audit trail.
            </p>
            <div className="grid gov-grid">
              {NO_CARDS.map((c) => (
                <a
                  key={c.slug}
                  href={`#/features/${c.slug}`}
                  className="card-anchor"
                  aria-label={`${c.title} - learn more`}
                >
                  <Card className="feature-card">
                    <div className={`feature-icon ${c.tone}`} aria-hidden="true"><PixelIcon name={c.icon} /></div>
                    <Heading level={3} className="feature-title">{c.title}</Heading>
                    <p className="feature-body">{c.body}</p>
                    <span className="card-more">Read more&nbsp;{'>'}</span>
                  </Card>
                </a>
              ))}
            </div>
          </div>
        </section>

        {/* INSTALL */}
        <section id="install" className="section">
          <div className="wrap">
            <PxTag>Install</PxTag>
            <Heading level={2} className="section-title">
              Running in five minutes
            </Heading>
            <div className="install-grid">
              <div>
                <Heading level={3} className="install-h"><span className="n">[1]</span> Clone &amp; set up</Heading>
                <div className="px-code">
                  <CodeBlock code={INSTALL_BASH} language="bash" hasCopyButton />
                </div>
              </div>
              <div>
                <Heading level={3} className="install-h"><span className="n">[2]</span> Connect your AI assistant</Heading>
                <p className="install-p">
                  Paste into Claude Desktop&rsquo;s config (or any MCP client&rsquo;s{' '}
                  <code>mcpServers</code>), replacing{' '}
                  <code>/absolute/path/to</code> with your checkout&rsquo;s path:
                </p>
                <div className="px-code">
                  <CodeBlock code={INSTALL_MCP} language="json" hasCopyButton />
                </div>
              </div>
              <div>
                <Heading level={3} className="install-h"><span className="n">[3]</span> Or just use the terminal</Heading>
                <div className="px-code">
                  <CodeBlock code={INSTALL_CLI} language="bash" hasCopyButton />
                </div>
              </div>
            </div>
          </div>
        </section>

        <div className="px-hr" aria-hidden="true" />

        {/* FAQ */}
        <section id="faq" className="section">
          <div className="wrap narrow">
            <PxTag variant="amber">FAQ</PxTag>
            <Heading level={2} className="section-title">
              Asked a lot
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
            <p className="game-over">- insert coin -</p>
            <Heading level={2} className="section-title">
              Stop filling out forms.
            </Heading>
            <p className="section-sub">
              Point your agent at the job market. Answer the grill. Confirm the
              ones worth your time. Veto handles the rest, and refuses the rest.
            </p>
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

function NotFoundPage({ slug }: { slug: string }) {
  return (
    <main id="top">
      <section className="page-hero">
        <div className="wrap">
          <a className="back-link" href="#/">
            {'<'} Home
          </a>
          <div className="page-hero-inner">
            <PxTag variant="red">404</PxTag>
            <h1 className="page-title">No such module.</h1>
            <p className="page-lede">
              There is no feature page for &ldquo;{slug}&rdquo;. It may have
              been renamed, or the link is wrong. The full list lives on the
              features index.
            </p>
            <div className="hero-ctas">
              <PxBtn variant="primary" href="#features" label="Browse features">
                {'>'} Browse features
              </PxBtn>
              <PxBtn variant="secondary" href="#/" label="Back home">
                Back home
              </PxBtn>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

/* ------------------------------------------------------------------ */
/* Router                                                               */
/* ------------------------------------------------------------------ */

export default function App() {
  const hash = useRoute();

  useEffect(() => {
    if (hash === '#/demo') {
      document.title = 'Get vetoed - interactive demo - Veto';
    } else if (hash === '#/docs') {
      document.title = 'Docs - Veto';
    } else if (hash === '#/dashboard') {
      document.title = 'Mission control - Veto dashboard';
    } else if (hash === '#/decoder/try') {
      document.title = 'Decode a posting - Veto';
    } else if (hash.startsWith('#/decoder/r/')) {
      document.title = 'Shared decode - Veto';
    } else if (hash.startsWith('#/features/')) {
      const slug = hash.slice('#/features/'.length);
      const spec = SPECS[slug];
      document.title = spec
        ? `${spec.title} - Veto`
        : 'Not found - Veto';
    } else {
      document.title = 'Veto - the AI job applier that says no';
    }
  }, [hash]);

  if (hash === '#/demo') {
    return (
      <div className="page">
        <SiteNav routeHash={hash} />
        <DemoPage />
        <SiteFooter />
      </div>
    );
  }

  if (hash === '#/docs') {
    return (
      <div className="page">
        <SiteNav routeHash={hash} />
        <DocsPage />
        <SiteFooter />
      </div>
    );
  }

  if (hash === '#/dashboard') {
    return (
      <div className="page">
        <SiteNav routeHash={hash} />
        <DashboardPage />
        <SiteFooter />
      </div>
    );
  }

  if (hash === '#/decoder/try') {
    return (
      <div className="page">
        <SiteNav routeHash={hash} />
        <DecoderPage />
        <SiteFooter />
      </div>
    );
  }

  if (hash.startsWith('#/decoder/r/')) {
    return (
      <div className="page">
        <SiteNav routeHash={hash} />
        <DecoderSharePage />
        <SiteFooter />
      </div>
    );
  }

  if (hash.startsWith('#/features/')) {
    const slug = hash.slice('#/features/'.length);
    const spec = SPECS[slug];
    if (spec) {
      return (
        <div className="page">
          <SiteNav routeHash={hash} />
          <FeaturePage spec={spec} />
          <SiteFooter />
        </div>
      );
    }
    return (
      <div className="page">
        <SiteNav routeHash={hash} />
        <NotFoundPage slug={slug} />
        <SiteFooter />
      </div>
    );
  }

  return (
    <div className="page">
      <SiteNav routeHash={hash} />
      <HomePage routeHash={hash} />
      <SiteFooter />
    </div>
  );
}
