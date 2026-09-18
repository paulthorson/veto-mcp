import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'ai-lab',
  tag: 'Train · the lab',
  tagVariant: '',
  title: 'REPS WITH A RUBRIC',
  lede: 'The interview & skills lab behind the lessons: five disclosed interview modes, role-based AI exercises (ethics calls, evaluation design, failure postmortems), and four soft-skill scenarios. Every round is checked against a published rubric with named scoring signals — nothing hidden, nothing graded on vibes.',
  points: [
    {
      icon: 'mic',
      tone: '',
      title: 'Five interview modes, disclosed',
      body: 'Recruiter screen, hiring manager, peer, executive, and an adversarial stress test. Each mode publishes its persona, what it is listening for, and its rubric weights — they sum to 1.0 and you see them before the round starts.',
    },
    {
      icon: 'bolt',
      tone: '',
      title: 'AI exercises that check judgment',
      body: 'Ethics scenarios, evaluation design, failure postmortems — per role track. The checker measures keyword-concept coverage with word-boundary matching, and tells you plainly what a pass does and does not mean.',
    },
    {
      icon: 'chat',
      tone: '',
      title: 'Soft-skill scenarios, three rounds each',
      body: 'Conflict, influence, negotiation, ambiguous stakeholder. The scenario card shows the setup, what good looks like, and every scoring signal by name — the triggers are visible to you, not hidden heuristics.',
    },
    {
      icon: 'shield',
      tone: 'amber',
      title: 'Voice stays off until you say so',
      body: 'Text is the default input everywhere. Voice is strictly opt-in: local mode keeps audio on your machine with a provider you supply; connected mode shows the full disclosure first and requires explicit consent. Disabled means transcribe() refuses.',
    },
  ],
  demoTitle: 'A lab round',
  demoLines: [
    { text: '>>> from initiatives.i06 import modes, scenarios', kind: 'cmd' },
    { text: ">>> print(modes.mode_card('adversarial'))", kind: 'cmd' },
    { text: 'persona: skeptical executive · probes the argument, never the person', kind: 'info' },
    { text: 'weights: 5 disclosed dimensions, sum to 1.0 — shown before the round', kind: 'info' },
    { text: ">>> print(scenarios.scenario_card('influence'))", kind: 'cmd' },
    { text: '+ setup: win a skeptical stakeholder with no authority · 3 rounds · signals named up front', kind: 'ok' },
    { text: '! the adversarial mode stress-tests the argument — insults are banned by the shared token list', kind: 'warn' },
  ],
  limits: [
    'The exercise checker measures keyword-concept coverage, not reasoning quality. A pass means you hit the concepts — it does not certify your judgment.',
    'Question banks are deterministic, indexed by a stable hash of mode, company, and role. Reproducible, not personalized.',
    'Voice has no microphone wiring of its own: in local mode you supply the transcription provider.',
    'Practice is practice. Lab scores are never presented as credentials.',
  ],
  faq: [
    {
      q: 'How is this different from mock interviews?',
      a: 'Mock interviews run five-question sessions shaped like a real loop. The lab is the practice room behind it: isolated modes, single-skill scenarios, and rubrics you can read before you start.',
    },
    {
      q: 'Does voice send my audio anywhere?',
      a: 'Not unless you configure it to. Default is text-only. Local mode states that no audio leaves your machine. Connected mode requires you to see the exact service, what is sent, and the retention terms — then grant explicit consent. Consent can be withdrawn.',
    },
  ],
};

export default spec;
