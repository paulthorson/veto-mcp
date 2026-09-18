import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'extensions',
  tag: 'Extend · curated',
  tagVariant: '',
  title: 'EXTEND IT. SAFELY.',
  lede: 'A governed extension platform: a curated registry where every extension passes four review gates before it becomes installable, Ed25519-signed packages pinned to exact versions, and a sandbox that gives extension code only the capabilities it declares. Power without the supply-chain roulette.',
  points: [
    {
      icon: 'check',
      tone: '',
      title: 'Four gates, all recorded',
      body: 'Compatibility and security are checked by automation; UX and governance by named humans. Each gate records reviewer, verdict, date, and notes — and an extension is installable only when all four pass. Automated gates can only be overridden by a named human with a written justification.',
    },
    {
      icon: 'shield',
      tone: '',
      title: 'Signed, pinned, revocable',
      body: 'Packages are hashed deterministically and signed Ed25519. When a publisher key is provided, the registry pins it, so install-time verification is against the pinned key; without one, the entry is honestly recorded as self-asserted. Upgrades need a fresh review record and a strictly newer version; revoked versions refuse to install.',
    },
    {
      icon: 'lock',
      tone: 'amber',
      title: 'Sandboxed by construction',
      body: 'Extension code reaches the host only through a capability broker: the context methods are the entire surface. Import scans run clean, PII handling must match the declared mode, and confirm-required actions re-prompt through the host.',
    },
    {
      icon: 'doc',
      tone: '',
      title: 'Scaffold in one template',
      body: 'scaffold_extension writes a complete extension: manifest, entrypoint, policy-kit test suite, capability disclosure docs, dashboard card, wizard step, and CLI/MCP snippets — plus a retro template so the build teaches the ledger.',
    },
  ],
  demoTitle: 'Shipping an extension',
  demoLines: [
    { text: '>>> from initiatives.i11.scaffold.template import scaffold_extension', kind: 'cmd' },
    { text: ">>> scaffold_extension('role-radar-digest', out_dir='ext/')", kind: 'cmd' },
    { text: '+ manifest.json · extension.py · policy-kit tests · web card · docs', kind: 'ok' },
    { text: '>>> registry.record_gate(ext_id, "ux", verdict="pass", reviewer="Jane Doe")', kind: 'cmd' },
    { text: '>>> registry.record_gate(ext_id, "governance", verdict="pass", reviewer="Alex")', kind: 'cmd' },
    { text: '+ ux: pass · governance: pass (two named human reviewers)', kind: 'info' },
    { text: '! automated gates (compatibility, security) can only be overridden by a named human with written justification', kind: 'warn' },
    { text: '+ all four gates pass → signed, pinned, installable', kind: 'ok' },
  ],
  limits: [
    'A signature proves who published which bytes — it does not make code trustworthy. The four review gates do that; signing makes substitution and silent upgrades detectable.',
    'The registry is a local JSON file by default. A remote index is a distribution concern, not a trust upgrade.',
    'Revocation is append-only and checked at registry install time — but it cannot reach copies already installed elsewhere.',
    'Confirm-required actions always re-prompt through the host. An extension cannot silently escalate.',
  ],
  faq: [
    {
      q: 'Can anyone publish an extension?',
      a: 'Anyone can write one from the scaffold. Publishing to the registry means passing all four gates — two automated, two human. No gate, no listing.',
    },
    {
      q: 'What stops a malicious extension?',
      a: 'Layers: the import scan and security gate at review time, the sandbox at runtime, signed pinned packages against substitution, and revocation when something slips through.',
    },
  ],
};

export default spec;
