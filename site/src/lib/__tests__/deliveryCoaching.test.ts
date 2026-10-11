/* Feature H: delivery coaching tests. All deterministic — same in, same out. */
import { describe, expect, it } from 'vitest';
import { analyzeDelivery, analyzeDeliveryAcross, pacingNoteFor } from '../deliveryCoaching';

const words = (n: number): string => Array.from({ length: n }, () => 'word').join(' ');

describe('analyzeDelivery filler counting', () => {
  it('counts single and multi-word fillers case-insensitively', () => {
    const fb = analyzeDelivery('um, I like, um, you know, um like um');
    expect(fb.fillerTotal).toBe(7);
    expect(fb.fillerWords).toEqual([
      { word: 'um', count: 4 },
      { word: 'like', count: 2 },
      { word: 'you know', count: 1 },
    ]);
  });

  it('matches filler words regardless of case', () => {
    const fb = analyzeDelivery('UM, Uh, LIKE the thing');
    expect(fb.fillerTotal).toBe(3);
    expect(fb.fillerWords).toEqual([
      { word: 'like', count: 1 },
      { word: 'uh', count: 1 },
      { word: 'um', count: 1 },
    ]);
  });

  it('counts well, and so, only at sentence starts', () => {
    const fb = analyzeDelivery(
      'Well, I did the thing. It went well, honestly. So, we shipped the release today.',
    );
    expect(fb.fillerWords).toEqual([
      { word: 'so,', count: 1 },
      { word: 'well,', count: 1 },
    ]);
    expect(fb.fillerTotal).toBe(2);
  });

  it('does not count mid-sentence so as a filler', () => {
    const fb = analyzeDelivery('the work was so, very impressive');
    expect(fb.fillerTotal).toBe(0);
  });

  it('ranks ties byte-wise for deterministic order', () => {
    const fb = analyzeDelivery('basically I actually did it');
    expect(fb.fillerWords).toEqual([
      { word: 'actually', count: 1 },
      { word: 'basically', count: 1 },
    ]);
  });

  it('documents the bare-word policy: content uses count too', () => {
    /* 'like' is a verb here, not a filler — the documented policy counts
       it anyway (text has no prosody), and the copy says "you said",
       which is literally true. */
    const fb = analyzeDelivery('I like this framework and I like it');
    expect(fb.fillerWords).toEqual([{ word: 'like', count: 2 }]);
    expect(fb.suggestions[0]).toBe(
      "You said 'like' 2 times — trade the filler uses for a silent pause.",
    );
  });

  it('counts sentence-start fillers after ! and ?', () => {
    const fb = analyzeDelivery('Great! Well, we did it. Really? So, what now.');
    expect(fb.fillerWords).toEqual([
      { word: 'so,', count: 1 },
      { word: 'well,', count: 1 },
    ]);
    expect(fb.fillerTotal).toBe(2);
  });
});

describe('analyzeDelivery hedging scoring', () => {
  it('scores 1 hedge in 20 words as 20 (400/20)', () => {
    const text =
      'I built the cache layer over three weekends and maybe cut p99 latency with a simple eviction policy fix today';
    expect(analyzeDelivery(text).hedgingScore).toBe(20);
  });

  it('caps the score at 100', () => {
    expect(analyzeDelivery('maybe probably sure thing').hedgingScore).toBe(100);
  });

  it('scores zero hedges as zero', () => {
    expect(analyzeDelivery('I built the cache and cut p99 latency').hedgingScore).toBe(0);
  });

  it('counts multi-word hedge phrases', () => {
    /* 7 words, 1 hedge ("i think") -> round(400/7) = 57 */
    expect(analyzeDelivery('I think this fix is correct now').hedgingScore).toBe(57);
  });
});

describe('analyzeDelivery pacing', () => {
  it('documents the <10 / 10-60 / >60 thresholds', () => {
    expect(pacingNoteFor(9)).toBe('Very brief — the grill reads short answers as evasive.');
    expect(pacingNoteFor(10)).toBe('Good length for a spoken-style answer.');
    expect(pacingNoteFor(60)).toBe('Good length for a spoken-style answer.');
    expect(pacingNoteFor(61)).toBe(
      'Thorough, but watch rambling — tighten to the strongest point.',
    );
  });

  it('applies pacing thresholds to the answer', () => {
    expect(analyzeDelivery(words(9)).pacingNote).toContain('Very brief');
    expect(analyzeDelivery(words(30)).pacingNote).toContain('Good length');
    expect(analyzeDelivery(words(61)).pacingNote).toContain('rambling');
  });
});

describe('analyzeDelivery suggestions', () => {
  it('calls out the top filler with its count', () => {
    const fb = analyzeDelivery('um, I like, um, you know, um like um');
    expect(fb.suggestions[0]).toBe(
      "You said 'um' 4 times — trade the filler uses for a silent pause.",
    );
  });

  it('flags heavy hedging with an actionable swap', () => {
    const fb = analyzeDelivery('maybe I think this might hopefully be probably right I guess');
    expect(fb.suggestions[0]).toContain('Hedging like');
  });

  it('pins the HEDGE_SUGGESTION_THRESHOLD 39-vs-40 boundary', () => {
    /* 1 hedge in 10 words -> round(400/10) = 40: fires. */
    const at40 = analyzeDelivery('maybe word word word word word word word word word');
    expect(at40.hedgingScore).toBe(40);
    expect(at40.suggestions.some((s) => s.includes('Hedging like'))).toBe(true);
    /* 3 hedges in 31 words -> round(1200/31) = 39: stays quiet. */
    const at39 = analyzeDelivery(
      'maybe probably hopefully ' + words(28),
    );
    expect(at39.hedgingScore).toBe(39);
    expect(at39.suggestions.some((s) => s.includes('Hedging like'))).toBe(false);
  });

  it('keeps 1-3 suggestions', () => {
    const fb = analyzeDelivery(
      'um, maybe I think this might hopefully be probably right I guess but it is also kind of well known ' +
        words(70),
    );
    expect(fb.suggestions.length).toBeGreaterThanOrEqual(1);
    expect(fb.suggestions.length).toBeLessThanOrEqual(3);
  });

  it('praises clean delivery when nothing fires', () => {
    const fb = analyzeDelivery(
      'I ran the migration over one weekend and cut p99 latency by half',
    );
    expect(fb.suggestions).toEqual([
      'Clean delivery — read it out loud once; if it sounds steady, submit it.',
    ]);
  });
});

describe('analyzeDelivery empty input', () => {
  it.each(['', '   '])('zeroes feedback for %j', (text) => {
    const fb = analyzeDelivery(text);
    expect(fb.fillerWords).toEqual([]);
    expect(fb.fillerTotal).toBe(0);
    expect(fb.hedgingScore).toBe(0);
    /* Coherent with the suggestion: nothing to pace, nothing to analyze. */
    expect(fb.pacingNote).toBe('No answer to pace — nothing to read yet.');
    expect(fb.suggestions).toEqual([
      'No answer to analyze — even a rough answer beats silence.',
    ]);
  });
});

describe('pacingNoteFor', () => {
  it('pins the blank / brief / good / long boundaries', () => {
    expect(pacingNoteFor(0)).toBe('No answer to pace — nothing to read yet.');
    expect(pacingNoteFor(1)).toContain('Very brief');
    expect(pacingNoteFor(9)).toContain('Very brief');
    expect(pacingNoteFor(10)).toContain('Good length');
    expect(pacingNoteFor(60)).toContain('Good length');
    expect(pacingNoteFor(61)).toContain('rambling');
  });
});

describe('analyzeDeliveryAcross', () => {
  const answers = [
    { qid: 'q1', text: 'um, I like, um, you know, um like um' },
    { qid: 'q2', text: 'maybe I think this might hopefully be probably right I guess' },
  ];

  it('sums fillers and averages hedging across the run', () => {
    const fb = analyzeDeliveryAcross(answers);
    expect(fb.fillerTotal).toBe(7);
    expect(fb.fillerWords).toEqual([
      { word: 'um', count: 4 },
      { word: 'like', count: 2 },
      { word: 'you know', count: 1 },
    ]);
    /* per-answer hedging: 0 and 100 -> average 50 */
    expect(fb.hedgingScore).toBe(50);
  });

  it('renders suggestions from the most frequent themes', () => {
    const fb = analyzeDeliveryAcross(answers);
    expect(fb.suggestions[0]).toBe(
      "You said 'um' 4 times across your answers — trade the filler uses for a silent pause.",
    );
    expect(fb.suggestions).toContain(
      "Hedging like 'maybe' and 'I think' softened your answers — trade one hedge per answer for a claim you can defend.",
    );
    expect(fb.suggestions).toContain(
      'Your answers ran short on average — add one concrete example per answer.',
    );
  });

  it('renders the sentence-start branch of the aggregate filler suggestion', () => {
    const fb = analyzeDeliveryAcross([
      { qid: 'q1', text: 'Well, I did the thing. So, we shipped it today.' },
    ]);
    /* Tie 1-1: byte-wise 'so,' < 'well,' — the sentence-start phrasing. */
    expect(fb.suggestions[0]).toBe(
      "You started 1 sentence with 'so,' across your answers — let the pause do the work instead.",
    );
  });

  it('breaks theme ties byte-wise: filler before hedging', () => {
    const fb = analyzeDeliveryAcross([
      { qid: 'q1', text: 'um um um' }, // themes: filler, short
      { qid: 'q2', text: 'maybe maybe maybe maybe' }, // themes: hedging, short
    ]);
    /* filler:1, hedging:1, short:2 — short first, then byte-wise filler < hedging. */
    expect(fb.suggestions[0]).toContain('ran short on average');
    expect(fb.suggestions[1]).toContain("You said 'um' 3 times");
    expect(fb.suggestions[2]).toContain('Hedging like');
  });

  it('rounds the average word count before pacing', () => {
    /* (9 + 10) / 2 = 9.5 -> Math.round -> 10 -> 'Good length'. */
    const fb = analyzeDeliveryAcross([
      { qid: 'q1', text: words(9) },
      { qid: 'q2', text: words(10) },
    ]);
    expect(fb.pacingNote).toBe('Good length for a spoken-style answer.');
  });

  it('handles mixed blank/non-blank answers without borrowing blank themes', () => {
    const fb = analyzeDeliveryAcross([
      { qid: 'q1', text: '' },
      { qid: 'q2', text: 'um, I like, um, you know, um like um' },
    ]);
    expect(fb.fillerTotal).toBe(7);
    /* The blank answer's 'general' theme does not dilute the vote. */
    expect(fb.suggestions[0]).toContain("You said 'um' 4 times");
    expect(fb.suggestions).not.toContain(
      'Delivery held steady across your answers — keep it that way.',
    );
  });

  it('never reports "Delivery held steady" on a mostly-blank run', () => {
    const fb = analyzeDeliveryAcross([
      { qid: 'q1', text: '' },
      { qid: 'q2', text: '  ' },
      {
        qid: 'q3',
        text: 'I ran the migration over one weekend and cut p99 latency by half',
      },
    ]);
    expect(fb.suggestions).toEqual([
      'Most answers were blank — delivery coaching needs real answers to work with.',
    ]);
  });

  it('still reports steady delivery when every answer is real and clean', () => {
    const clean = 'I ran the migration over one weekend and cut p99 latency by half';
    const fb = analyzeDeliveryAcross([
      { qid: 'q1', text: clean },
      { qid: 'q2', text: clean },
    ]);
    expect(fb.suggestions).toEqual([
      'Delivery held steady across your answers — keep it that way.',
    ]);
  });

  it('handles an empty run', () => {
    const fb = analyzeDeliveryAcross([]);
    expect(fb.fillerWords).toEqual([]);
    expect(fb.fillerTotal).toBe(0);
    expect(fb.hedgingScore).toBe(0);
    expect(fb.suggestions).toEqual([
      'No answers to analyze — even a rough answer beats silence.',
    ]);
  });

  it('handles all-blank answers', () => {
    const fb = analyzeDeliveryAcross([
      { qid: 'q1', text: '' },
      { qid: 'q2', text: '  ' },
    ]);
    expect(fb.fillerTotal).toBe(0);
    expect(fb.suggestions).toEqual([
      'No answers to analyze — even a rough answer beats silence.',
    ]);
  });
});

describe('analyzeDelivery determinism', () => {
  const text = 'um, well, I think maybe I might be a good fit, sort of, for this role basically';
  const answers = [
    { qid: 'q1', text },
    { qid: 'q2', text: 'Actually the scale was large, you know' },
  ];

  it('returns identical feedback for identical input', () => {
    expect(analyzeDelivery(text)).toEqual(analyzeDelivery(text));
  });

  it('returns identical aggregates for identical runs', () => {
    expect(analyzeDeliveryAcross(answers)).toEqual(analyzeDeliveryAcross(answers));
  });
});
