import { Heading } from '@astryxdesign/core';
import { PxTag } from '../px';

/* Changelog page (#/changelog).
   Mirrors the repo-root CHANGELOG.md (plain-English, user-facing release
   notes). Vite cannot import outside the site root, so the content is
   inlined here. Sync process: when CHANGELOG.md gains a release section,
   the project owner copies it over before the release ships; a stale page
   is caught by comparing this file against CHANGELOG.md at release time. */

interface ChangeRow {
  name: string;
  desc: string;
}

const UNRELEASED: ChangeRow[] = [
  {
    name: 'Pre-release name cleanup',
    desc: 'Renamed leftover pre-release product names to Veto throughout the docs and app.',
  },
  {
    name: 'Mentor matching',
    desc: "Get matched with mentors. Before you agree to share anything, you see an exact preview of what they'd see \u2014 nothing personal goes out without your explicit consent. Includes safety controls like blocking and quarantine.",
  },
  {
    name: 'Extension platform',
    desc: "Developers can build extensions for Veto. Extensions run in a secure sandbox, versions are signed, and banned versions stay banned \u2014 they can't be reinstalled through rollback.",
  },
  {
    name: 'Interview & skills lab',
    desc: 'Practice interviews with feedback, tracking of your progress over time, drill recommendations for weak spots, and a map of your skill gaps (including soft skills).',
  },
  {
    name: 'Application studio',
    desc: 'A workspace for building each application: checks your resume against applicant-tracking systems, explains what changed between drafts, and keeps a library of your evidence (achievements, numbers, proof).',
  },
  {
    name: 'Fit decoder & career graph',
    desc: "Explains in plain words why you're a good (or bad) fit for a job: which skills match, which are missing, and how your past roles connect to where you're headed.",
  },
  {
    name: 'Connector reliability',
    desc: "Keeps Veto's connections to job boards, email, and calendar working: follow-up messaging, handoffs that survive interruptions, and graceful recovery when something drops.",
  },
  {
    name: 'Distribution',
    desc: 'Install Veto as an app on your phone or desktop, and back up or restore your data.',
  },
];

export default function ChangelogPage() {
  return (
    <div className="page">
      <main>
        {/* HERO */}
        <section className="hero page-hero">
          <div className="wrap">
            <a className="back-link" href="#/">
              {'<'} Home
            </a>
            <PxTag>Changelog</PxTag>
            <Heading level={1} className="hero-title page-title">
              WHAT CHANGED.
            </Heading>
            <p className="hero-sub">
              Plain-English notes on what changed in Veto, most recent first.
              Written for users, not engineers. If something isn't listed here,
              it didn't ship.
            </p>
          </div>
        </section>

        {/* UNRELEASED */}
        <section className="section docs-sec">
          <div className="wrap">
            <PxTag variant="amber">Now</PxTag>
            <Heading level={2} className="section-title">
              Unreleased
            </Heading>
            <p className="section-sub">
              Built, reviewed, and committed to the main codebase. These land
              in the next versioned release.
            </p>
            <div className="tool-group">
              {UNRELEASED.map((c) => (
                <div key={c.name} className="tool-row">
                  <span className="tool-name">{c.name}</span>
                  <p className="tool-desc">{c.desc}</p>
                </div>
              ))}
            </div>
            <p className="feature-body" style={{ marginTop: '1.5rem' }}>
              Still being built: collective intelligence, outcomes &amp;
              lifecycle, adaptive fit engine, daily operating loop, P0 craft.
              Coming next for connector reliability: a human circuit breaker
              — every AI-drafted message waits for your review before it goes
              out, and the AI earns your trust over time before you can switch
              the breaker off.
            </p>
          </div>
        </section>

        <div className="px-hr" aria-hidden="true" />

        {/* V0.1.0 */}
        <section className="section docs-sec">
          <div className="wrap">
            <PxTag variant="red">Release</PxTag>
            <Heading level={2} className="section-title">
              v0.1.0 — 2026-09-12
            </Heading>
            <p className="section-sub">First release.</p>
            <p className="feature-body">
              Veto searches the 4 official board APIs (Greenhouse, Lever,
              Ashby, Adzuna). The LinkedIn, Indeed, and ZipRecruiter providers
              were removed in the post-hardening pass; Glassdoor remains a
              locked stub that performs no scraping. Veto grills you about the
              gaps in your resume over chat or WhatsApp, tailors every
              application to the role without inventing experience, fills in
              application forms but stops before submitting — you click
              submit — and tracks your applications, stages, and follow-ups.
              Runs as an MCP server with a terminal dashboard and a local web
              UI you can open on your phone over your home network.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
