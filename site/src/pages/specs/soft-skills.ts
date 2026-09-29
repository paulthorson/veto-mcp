import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'soft-skills',
  tag: 'Train · soft skills',
  tagVariant: 'red',
  title: 'SPAR WITH SOMEONE MEANER THAN THE INTERVIEW',
  lede: 'soft_skills.py trains communication clarity, STAR storytelling, leadership influence, negotiation, active listening, and executive presence. The negotiation sim puts you across the table from a hardball hiring manager, firm, hardball, or brutal, with labeled coach feedback between rounds.',
  interactive: 'negotiation',
  points: [
    {
      icon: 'swords',
      tone: 'red',
      title: 'Adversarial negotiation sim',
      body: 'Three rounds against an AI hiring manager that lowballs, reframes, and pressures. Three difficulties: firm, hardball, brutal. It attacks your arguments. Never you.',
    },
    {
      icon: 'chat',
      tone: '',
      title: 'Coach breaks character',
      body: 'Between rounds the sim drops the act and gives labeled COACH feedback: what worked, what leaked, the exact reframe to try next round.',
    },
    {
      icon: 'mic',
      tone: '',
      title: 'Six training areas',
      body: 'Communication clarity, STAR storytelling, leadership influence, negotiation, active listening, executive presence: diagnostics, drills, and progress trends per area.',
    },
    {
      icon: 'chart',
      tone: '',
      title: 'Weakness-driven practice',
      body: 'Your weakest drill areas feed the mentor matcher and the skill-gap planner. The system routes you to humans where humans help most.',
    },
  ],
  demoTitle: 'A brutal round',
  demoLines: [
    { text: '$ veto negotiate --difficulty brutal', kind: 'cmd' },
    { text: 'AI: "We can do 150 base. Already above band for this level."', kind: 'info' },
    { text: '> "I am targeting 175, the scope is owning the deploy path."', kind: 'cmd' },
    { text: 'AI: "Scope is aspirational until you prove it. 155, generous."', kind: 'info' },
    { text: 'COACH: Good anchor. Do not defend, ask what 175 would need to look like.', kind: 'warn' },
    { text: '+ round 2: you turn their pushback into a written Q1 commitment.', kind: 'ok' },
  ],
  limits: [
    'A simulator, not a real negotiator. Real humans are weirder and less fair.',
    'Brutal mode is deliberately uncomfortable. That is the point, but pace yourself.',
    'Feedback is tactical (framing, anchoring, trades), not legal or financial advice.',
    'It trains the conversation, not the market data. Know your numbers before you spar.',
  ],
  faq: [
    {
      q: 'Why is the AI mean?',
      a: 'Because real hiring managers anchor low and press. Training against a friendly coach teaches you to win friendly conversations. You need the other kind.',
    },
    {
      q: 'Does it store what I say?',
      a: 'Sessions and practice history persist locally (soft_skill_sessions.json). Nothing leaves your machine.',
    },
  ],
};

export default spec;
