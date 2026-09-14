# Veto Terms of Use

*Version 2026-09-14-hardened. Written in plain English on purpose — every section says
what it means. This is not legal advice, and a lawyer should review it before
Veto's public launch.*

## 1. Who this agreement is between

These terms are a contract between you and **Paul Thorson** ("we", "us", "our"),
the maker of Veto. If you are using Veto for a company, you are agreeing on its
behalf too, and you confirm you have authority to do so.

## 2. Accepting these terms

On first launch, Veto shows you these terms and asks you to check a box that says
"I agree to the Terms of Use and confirm I am 18 or older." Veto does not start
until you do. We log when you agreed and which version you agreed to, and we
keep those logs for as long as needed to prove the agreement. A link
buried in a footer is not agreement; the checkbox is.

## 3. Your license to use Veto

The source code and the binaries we distribute are licensed under the Apache
License 2.0 (see LICENSE) — a perpetual, irrevocable grant. We cannot take
those rights back. On top of that, we grant you a personal, non-exclusive,
non-transferable license to use Veto's connected services (syncing, updates,
and any server-side features) for your own job search, under the terms below —
including a job search you run in the course of employment or on behalf of a
company you are authorized to represent (see §1). We may suspend or revoke
access to the connected services as described in §19; that never revokes your
Apache 2.0 rights in code you already have.

If these terms and the LICENSE ever conflict about your rights in the source
code or binaries, the LICENSE controls.

You may not present a modified or redistributed version as the official Veto,
or resell access to our connected services as your own service.

## 4. Age requirement

You must be at least 18 years old to use Veto.

## 5. The deal: free product, telemetry in return

Veto is free to use. To keep it free and maintain it, Veto collects two kinds of
telemetry as a condition of use. This is the trade-off, stated plainly:

- **(a) Crash and problem reports — required.** When something breaks, Veto sends
  a report so we can fix it. These are required for Veto to function as a free product;
  without them we cannot maintain the product you are getting for free.
- **(b) Usage analytics — optional.** Which features get used and performance
  timings. This is off unless you turn it on in Settings, and you can turn it off
  again at any time. We do not bundle it into the mandatory checkbox.

If you are not comfortable with (a), Veto is not for you — please do not use it.
This trades away a telemetry-free option to keep Veto free and sustainable.

## 6. Crash reports: what they contain and where they go

Before any report leaves your machine, it is scrubbed on your device: we remove
names, emails, resume text, tokens, and file paths that identify you. Reports are
filed under Veto's own identity — never attributed to you — into a private,
access-controlled issue tracker visible only to us. We do not post
them publicly. Because reports are not attributed to you, we cannot locate
server-side reports by user — access and deletion requests (§8) are fulfilled
from the copy kept on your device (Settings → "Data sent").

We design reports to avoid identifying you, but we will not promise the impossible:
a sufficiently motivated party studying technical details (stack traces, timings)
might correlate them. Treat crash reports as pseudonymous, not magically
anonymous.

Crash reports are kept for up to 24 months, then deleted. Analytics, when enabled,
are kept only in aggregated form from which individuals cannot be picked out.

## 7. What is designed never to be collected

Veto is designed so that your resume, cover letters, application materials,
emails, messages, name, or contact details are never collected: if the scrubber
cannot prove a field is clean, the field is withheld and the report says so.
Software has bugs, and we will not promise perfection — if a defect ever causes
such data to be included in a report, §24 (what we do about it) applies.

## 8. Where your data lives, and your rights

Data is stored and processed in the United States by our infrastructure providers.
If you are in the EU/UK, your use of Veto involves transferring your data to the
US. Before launch we will put Standard Contractual Clauses in place with those
providers; our lawyer confirms the final transfer mechanism.

We intend to rely on our legitimate interest in maintaining and securing a free
product as the lawful basis for required crash reports. Our lawyer is
validating this basis before launch, including a documented balancing test;
we will not rely on it for EU/UK users until it is validated, and if it does
not hold for your jurisdiction, we will change our approach and tell you.
Optional analytics are processed only with your consent, which you may withdraw
at any time in Settings.

You have the right to see every report Veto has sent from your machine (Settings →
"Data sent"), to request a copy, to request deletion, and to withdraw consent for
optional analytics at any time. To exercise these rights, contact [contact email].
We respond within 30 days. Withdrawing consent for required crash reports means
discontinuing use, since they are a condition of the free license.

## 9. Beta

Veto is pre-release software. Expect bugs, rough edges, and breaking changes.
Do not rely on Veto for anything time-critical without your own backup plan.

## 10. AI-generated content, and the risk you accept by using it

Veto drafts resume bullets, cover letters, and messages with AI. AI makes things
up — outputs may be inaccurate, incomplete, or hallucinated. **Always review
anything Veto drafts before it matters; you are the decision-maker, not the AI.**
Nothing in Veto is professional career, legal, or financial advice, and using
Veto creates no fiduciary or agency relationship.

By using Veto's AI features you **assume the risk**, to the maximum extent
permitted by law, that its outputs are wrong, and you accept responsibility
for what you send, submit, or rely on. Veto does not guarantee any outcome —
no interviews, no offers, no particular results. Anything Veto drafts for you —
resume bullets, cover letters, messages — is yours: you may use, edit, and
submit it as you wish, subject to any third-party rights that may be embedded
in the outputs.

AI regulation is evolving, including rules for employment-related AI such as the
EU AI Act. Where the law requires additional disclosures, documentation, or
human-oversight measures, we will provide them; nothing in this section limits
rights the law gives you.

## 11. Third-party services

Veto connects to job boards, email providers, and messaging apps that belong to
other companies, and Veto's own connectors query job boards automatically
(designed to be polite, budgeted, and rate-limited, but no behavior is
guaranteed). Those platforms may still treat automated access as a violation of
*their* terms, which can get *your* accounts limited or banned. That risk is
yours: we do not control those platforms, we cannot restore your accounts, and
— to the maximum extent permitted by law and subject to the non-waivable
carve-outs in §18 — we are not responsible for how they respond to automation,
whether the automation was yours or Veto's.

## 12. Acceptable use, and your indemnity

Do not use Veto to spam, harass, scrape in violation of a site's terms, submit
false information, or break the law. We may suspend or terminate access for
misuse.

If a third party brings a claim against us arising to a material extent from
(a) your misuse of Veto, (b) your violation of these terms, (c) your violation
of any law or any third-party terms, or (d) anything you submit to or through
Veto (not including crash reports or telemetry generated by Veto itself), **you agree to indemnify, defend, and hold us harmless** — meaning you
cover our reasonable legal costs and any resulting damages or settlements,
except to the extent the claim was caused by our own gross negligence or
willful misconduct. This does not cover regulatory fines imposed on us, which
many jurisdictions do not allow to be shifted by contract. Where
consumer-protection law limits indemnity obligations, this section applies to
the maximum extent the law allows. We will notify you promptly of any such
claim; if our delay in notifying you prejudices your defense, your indemnity
obligation is reduced to the extent of that prejudice. This section does not
apply to claims arising solely from Veto's own default behavior — connector
behavior or telemetry and crash-reporting behavior — where the conduct was not
something you directed, configured, or customized beyond Veto's default
settings (connecting your accounts with credentials and using default
schedules does not count as directing or configuring the conduct). We may take over the exclusive defense and control of the claim; if we
do so at our own expense, we bear those defense costs, but that does not reduce
your indemnity for damages, settlements, or other amounts owed. You agree to
cooperate with us in the defense, and you may not settle a claim in a way that
admits fault on our part or imposes obligations on us without our written
consent.

## 13. Feedback

Anything you send us via "Report a problem" or otherwise — ideas, suggestions,
bug reports — we may use freely, without payment or credit, to improve Veto.

## 14. Intellectual property, contributions, and the Veto name

The Veto name, logos, and other brand assets are ours; do not use them without permission.
Nominative fair use is fine: you may truthfully say your project is "a fork of
Veto" or "compatible with Veto" to describe what it is — but not in a way that
suggests your project *is* Veto, is endorsed by us, or is the official release.

The application's source code is licensed under the Apache License 2.0 (see the
LICENSE file), which also gives you a patent license from contributors as
described there.

**Contributions.** If you contribute to the Veto project — pull requests,
patches, issue text, documentation — your contribution is submitted under the Apache License 2.0 unless you state
otherwise in writing and we agree in writing before merging it, and you confirm
you have the right to contribute it (it is your work or you
have permission to submit it). Before public launch we intend to require a
Developer Certificate of Origin sign-off (or a contributor license agreement)
on contributions; until that mechanism is in place, this section governs, and
we recommend treating a CLA/DCO as a launch blocker. We may use, modify, and
redistribute contributions as part of Veto without payment or credit beyond
what the Apache License 2.0 requires.

## 15. Copyright complaints (DMCA)

If you believe content in Veto infringes your copyright, send a notice to
[contact email] containing: (1) identification of the copyrighted work;
(2) identification of the infringing material and where it appears;
(3) your contact details; (4) a statement that you have a good-faith belief
the use is not authorized; (5) a statement under penalty of perjury that the
information is accurate and you are authorized to act for the copyright owner;
and (6) your physical or electronic signature.

If your content was removed because of a notice you believe was mistaken, you
may send a counter-notice with the same identifying information, a statement
under penalty of perjury that the removal was a mistake, and your consent to
the jurisdiction of the federal court for your district — and we will restore
it as the law requires.

We respond to valid notices, remove infringing material, and terminate the
accounts of repeat infringers. Before public launch we will designate a DMCA
agent with the US Copyright Office.

## 16. Export controls

Do not use Veto in any country under US embargo or if you are on a US restricted
party list.

## 17. No warranty

**PLEASE READ THIS SECTION CAREFULLY. IT LIMITS RIGHTS YOU MAY OTHERWISE HAVE.**

Veto is provided "AS IS" and "AS AVAILABLE," without warranties of any kind,
express or implied, including the implied warranties of **merchantability**,
fitness for a particular purpose, title, and non-infringement. We do not promise
that Veto will be error-free, uninterrupted, secure, or fit for any particular
job search, or that any defects will be corrected.

To the extent that implied warranties cannot be excluded under applicable law,
they are limited to the minimum scope and duration the law allows. Some
jurisdictions do not allow the exclusion or limitation of implied warranties, so
the above exclusions may not apply to you — but they apply to the maximum extent
the law of your jurisdiction permits. Nothing in this section limits statutory
conformity rights you may have for digital content under applicable law
(including the EU Digital Content Directive, where it applies); our lawyer will
confirm the position before launch.

## 18. Limitation of liability

**PLEASE READ THIS SECTION CAREFULLY. IT LIMITS WHAT YOU CAN RECOVER FROM US.**

To the maximum extent permitted by law, our total aggregate liability for any
and all claims arising out of or relating to Veto — whether in contract, tort
(including negligence), strict liability, or any other legal theory — **will not
exceed US$100**. This is a fixed, agreed cap. It does not depend on what you paid
(Veto's license is free), on the value of any telemetry, or on the number of
claims; it is the total for everything, combined.

In no event will we be liable for any indirect, incidental, special,
consequential, or punitive damages, or for any loss of profits, revenue, data,
goodwill, business opportunity, or anticipated savings — even if we were told
such damages were possible.

The limits in this section are a fundamental part of the deal: Veto is offered
free on the understanding that our exposure is capped as stated here.

This section does **not** limit liability where the law forbids it, including
(where applicable and non-waivable) liability for gross negligence, willful
misconduct, fraud, or personal injury or death caused by negligence. Some
jurisdictions do not allow the exclusion or limitation of certain damages; in
those places, our liability is limited to the maximum the law allows.

## 19. Termination

We may suspend or end your access to Veto's connected services at any time, for
any reason, including abuse. Because Veto runs on your machine, the copy you have
keeps working offline for what it can do locally — but syncing, updates, and any
server-side features stop. We will give 30 days' notice for termination without
cause where practical; no notice for abuse or legal necessity.

## 20. Governing law

These terms are governed by the laws of [STATE — your home state], without regard
to conflict-of-law rules. If you are a consumer habitually resident in the EU
or UK, your mandatory local consumer-protection rights apply regardless of the
governing law stated here, and you may bring claims in the courts of your place
of residence (see the §21 carve-out). For everyone else, courts (for matters
not arbitrated) sit in [STATE].

## 21. Disputes: binding arbitration

If we cannot resolve a dispute directly within 30 days of written notice, it goes
to binding individual arbitration — not a courtroom, not a class action:

- **No class actions.** You and we each waive any class, collective, or
  representative proceeding, to the extent the law allows.
- **Opt-out.** You may opt out of arbitration within 30 days of first accepting
  these terms by emailing [contact email] from an address we can reply to, with a
  clear statement that you opt out.
- **Rules and fees.** Arbitration follows the AAA Consumer Arbitration Rules. For
  claims under $10,000, we pay the filing and arbitrator fees.
- **Small claims.** Either of us may still use small-claims court for qualifying
  disputes instead of arbitration.
- **Where.** Arbitration takes place in [STATE], or another location we both
  agree on.
- **Who decides what.** The arbitrator decides whether a dispute belongs in
  arbitration (delegation), except enforceability of the class-action waiver,
  which a court decides.
- **Mass filings.** Coordinated mass filings are handled in staged bellwether
  batches under AAA's mass-arbitration procedures.
- **EU/UK consumers.** If you are a consumer habitually resident in the EU or
  UK, this §21 does not apply to you: you may bring claims in the courts of
  your place of residence, and nothing in these terms limits your mandatory
  consumer-protection rights.

## 22. If these terms change

We will notify you in the app (and show a summary of what changed — a redline,
not just "terms updated") at least 14 days before changes take effect. Material
changes — anything affecting your rights, your data, or the free-for-telemetry
deal — require you to check the box again before continuing to use Veto. "Material"
means a reasonable user would want to know. The version you accepted and when are
always visible in Settings. If you decline the new terms, you must stop using
Veto's connected services; the local copy keeps working offline for what it can
do locally (see §19).

## 23. Standard provisions

- **Severability.** If any part of these terms is found unenforceable, the rest
  still applies, and the bad part is read down to the minimum needed to make it
  enforceable.
- **Entire agreement.** These terms (plus the LICENSE for the code) are the whole
  deal between us about Veto.
- **Assignment.** You may not transfer your rights without our consent; we may
  assign ours in a merger or sale, with notice to you.
- **Waiver.** If we do not enforce a term once, we do not lose the right to
  enforce it later.
- **Force majeure.** Neither of us is liable for delays caused by events beyond
  reasonable control (outages, natural disasters, etc.).
- **Survival.** Sections 5 (the deal), 8 (data rights), 10 (AI outputs), 11 (third-party services), 12 (indemnity), 13 (feedback), 14 (IP and contributions), 17 (warranty), 18 (liability),
  20 (governing law), 21 (arbitration), 24 (data incidents), and 25 (forks) survive termination.
- **Notices.** Legal notices to us go to [contact email]; notices to you go
  in-app and to any email you provided.

## 24. If something goes wrong with your data

If we discover that a report ever exposed personal data despite scrubbing, we
will notify users as the law requires — via in-app broadcast notice, since we
cannot identify affected users individually (reports are not attributable —
see §6) — and publish a description of what happened and what we changed, to
the extent we can do so without compromising security or legal obligations.
Hiding it is not an option.

## 25. Forks and downstream distribution

The Apache 2.0 license lets you fork, modify, and redistribute Veto's code —
that is your right, and we mean it. But your fork is **yours**: if you
distribute a modified or rebranded version, you are its distributor, you are
responsible for it, and these terms do not cover it. We are not liable for what
downstream distributors do with the code, and a fork may not present itself as
the official Veto or use the Veto name and logos in a way that implies it is
(see §14).

## 26. The Veto website

The website in front of this project is operated by us and is informational:
documentation, downloads, and project news. Download Veto only from our
official site or repository — to the maximum extent permitted by law, we are
not responsible for copies obtained elsewhere, which may be modified or
malicious. The site may link to third-party
resources we do not control and are not responsible for, to the maximum extent
permitted by law. If website copy ever
conflicts with these terms or the LICENSE, these terms and the LICENSE
control.
