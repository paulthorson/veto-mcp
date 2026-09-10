import type { PageSpec } from '../spec';

const spec: PageSpec = {
  slug: 'ai-proficiency',
  tag: 'Train · AI fluency',
  tagVariant: '',
  title: 'EMPLOYERS SCREEN FOR THIS NOW',
  lede: 'ai_proficiency.py takes you from zero to demonstrably AI-fluent: seven tracks (engineer, product, data, design, marketing, sales, generalist), deterministic diagnostics, 6–7 hands-on lessons per track — and an ethics lesson in every single one.',
  interactive: 'tracks',
  points: [
    {
      icon: 'bolt',
      tone: '',
      title: 'Seven tracks',
      body: 'Engineer, product, data, design, marketing, sales, generalist — each with 6–7 hands-on lessons built around doing real work with AI, not reading about it.',
    },
    {
      icon: 'target',
      tone: '',
      title: 'Diagnostics place you',
      body: 'A deterministic diagnostic finds your level before you start, so lesson one is never insulting or overwhelming.',
    },
    {
      icon: 'shield',
      tone: 'amber',
      title: 'Ethics in every track',
      body: 'Every track includes an ethics lesson: disclosure, data boundaries, when not to use AI. Fluency without judgment is a liability.',
    },
    {
      icon: 'chart',
      tone: '',
      title: 'Streaks keep you honest',
      body: 'Lessons log reps to the streak system. Progress, streaks, and practice history — the grind, gamified.',
    },
  ],
  demoTitle: 'Starting a track',
  demoLines: [
    { text: '$ veto ai diagnostic --track engineer', kind: 'cmd' },
    { text: '+ level 2/5: comfortable prompting, weak on review discipline', kind: 'ok' },
    { text: '+ placed at lesson 3: "Ship a PR reviewed by AI, then review the AI"', kind: 'ok' },
    { text: '$ veto ai lesson engineer 3', kind: 'cmd' },
    { text: '+ exercise session open. Ethics module unlocks at lesson 5.', kind: 'info' },
    { text: '+ rep logged: ai_lesson (engineer). Streak: 6 days.', kind: 'ok' },
  ],
  limits: [
    'Practice is practice — it is never presented as a credential or certification.',
    'Lessons are hands-on exercises, not lectures; they demand real work.',
    'AI tools change fast; lessons teach durable habits (review discipline, disclosure) over specific products.',
    'The diagnostic is deterministic — it places you by demonstrated answers, not self-rating.',
  ],
  faq: [
    {
      q: 'Will this get me an "AI certified" badge?',
      a: 'No, deliberately. Employers screen for demonstrated fluency; the lessons build the skill, and your work is the proof.',
    },
    {
      q: 'Which track should I pick?',
      a: 'Your role family. Generalist if you are switching. The diagnostic will tell you if you picked wrong.',
    },
  ],
};

export default spec;
