import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'mock-interviews',
  tag: 'Train · interviews',
  tagVariant: '',
  title: 'REHEARSE THE REAL THING',
  lede: 'mock_interview.py runs five-question sessions, behavioral, technical, company-specific, then grades you deterministically: STAR coverage, specificity and numbers, answer length, I/we ownership. Sessions persist locally; output is WhatsApp-compatible so you can drill from your phone.',
  interactive: 'interview',
  points: [
    {
      icon: 'mic',
      tone: '',
      title: 'Five-question sessions',
      body: 'Behavioral, technical, and company-specific questions per session, the actual shape of a real loop, not a trivia quiz.',
    },
    {
      icon: 'check',
      tone: '',
      title: 'Deterministic feedback',
      body: 'STAR coverage, hard numbers, answer length, ownership language. No LLM grades your personality; the rubric checks the structure of your answers.',
    },
    {
      icon: 'chat',
      tone: '',
      title: 'WhatsApp-compatible',
      body: 'Questions and feedback render cleanly in a side chat. Drill on the train, in line, anywhere. Sessions sync to your local log.',
    },
    {
      icon: 'ledger',
      tone: '',
      title: 'Progress that persists',
      body: 'Every session lands in mock_sessions.json. Watch your STAR coverage climb week over week. The reps compound.',
    },
  ],
  demoTitle: 'Running a mock session',
  demoLines: [
    { text: '$ veto mock start --company AcmeCo --role "platform eng"', kind: 'cmd' },
    { text: 'Q1: Tell me about a system you scaled.', kind: 'info' },
    { text: '> I led the migration of 12 services to k8s, cutting deploy time 40%.', kind: 'cmd' },
    { text: '+ STAR complete · two hard numbers · I-ownership', kind: 'ok' },
    { text: '! Q1 feedback: name the blast radius: who relied on it?', kind: 'warn' },
    { text: '+ session saved. 4 questions to go.', kind: 'ok' },
  ],
  limits: [
    'Feedback is structural (STAR, numbers, length). It cannot judge charisma or correctness of technical depth.',
    'Questions are curated per role family, not generated from the actual posting.',
    'Five questions per session. Real loops are longer; run more sessions.',
    'It never claims to predict hiring outcomes. Practice is practice.',
  ],
  faq: [
    {
      q: 'Is this an AI interviewer chatting with me?',
      a: 'It is a structured drill: questions, your answers, rubric feedback. Deterministic and repeatable. The same answer gets the same feedback every time.',
    },
    {
      q: 'Where do my sessions go?',
      a: 'mock_sessions.json on your machine. Nothing is uploaded anywhere.',
    },
  ],
};

export default spec;
