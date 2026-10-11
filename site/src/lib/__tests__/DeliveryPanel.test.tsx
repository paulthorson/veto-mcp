/* Feature H tests: DeliveryPanel — the presentation layer had zero
 * component tests. Rendered with react-dom/server for deterministic HTML
 * assertions (no test renderer dependency), same as pipelineBoard.
 *
 * Pins: the data-testid contract (asserted by E2E), toneFor's red/amber/
 * green boundaries, the inverted hedging-meter math (green left, red
 * right — high hedging must NOT render a green leading edge), and the
 * fillers/pacing/suggestions rendering.
 */

import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import DeliveryPanel from '../../demos/grill/DeliveryPanel';
import type { DeliveryFeedback } from '../chakraTypes';

function feedback(overrides: Partial<DeliveryFeedback> = {}): DeliveryFeedback {
  return {
    fillerWords: [{ word: 'um', count: 4 }],
    fillerTotal: 4,
    hedgingScore: 80,
    pacingNote: 'Good length for a spoken-style answer.',
    suggestions: ["You said 'um' 4 times — trade the filler uses for a silent pause."],
    ...overrides,
  };
}

function render(fb: DeliveryFeedback): string {
  return renderToStaticMarkup(<DeliveryPanel feedback={fb} />);
}

describe('DeliveryPanel data-testid contract', () => {
  it('renders every contracted testid', () => {
    const html = render(feedback());
    for (const id of [
      'delivery-panel',
      'delivery-fillers',
      'delivery-hedging',
      'delivery-pacing',
      'delivery-suggestions',
    ]) {
      expect(html).toContain(`data-testid="${id}"`);
    }
  });

  it('renders fillers, pacing, and suggestions from the feedback', () => {
    const html = render(feedback());
    expect(html).toContain('Filler words — 4 total');
    expect(html).toContain('um');
    expect(html).toContain('4 times');
    expect(html).toContain('Pacing — Good length for a spoken-style answer.');
    expect(html).toContain('trade the filler uses for a silent pause');
  });

  it('renders the clean state when no fillers were spotted', () => {
    const html = render(
      feedback({ fillerWords: [], fillerTotal: 0, suggestions: ['Clean delivery.'] }),
    );
    expect(html).toContain('None spotted — clean delivery.');
  });

  it('labels the hedging meter for assistive tech', () => {
    const html = render(feedback({ hedgingScore: 80 }));
    expect(html).toContain('aria-label="Hedging: 80 out of 100"');
  });
});

describe('DeliveryPanel toneFor boundaries', () => {
  it('60+ hedging reads red, with the low-confidence caption', () => {
    const html = render(feedback({ hedgingScore: 60 }));
    expect(html).toContain('#ff4d5e');
    expect(html).toContain('Lots of hedging');
  });

  it('59 hedging reads amber', () => {
    const html = render(feedback({ hedgingScore: 59 }));
    expect(html).toContain('#ffb020');
    expect(html).toContain('Some hedging');
  });

  it('30 hedging reads amber', () => {
    const html = render(feedback({ hedgingScore: 30 }));
    expect(html).toContain('#ffb020');
    expect(html).toContain('Some hedging');
  });

  it('29 hedging reads green, with the steady caption', () => {
    const html = render(feedback({ hedgingScore: 29 }));
    expect(html).toContain('#3dff73');
    expect(html).toContain('Steady');
  });
});

describe('DeliveryPanel hedging meter math (inverted semantics)', () => {
  /* High hedging is bad: the meter gradient is the inverted mirror
     (green left, red right), so a bad score's leading edge lands on red —
     never a green leading edge under a red number. */

  it('uses the inverted gradient, not the red-left fluency gradient', () => {
    const html = render(feedback({ hedgingScore: 80 }));
    expect(html).toContain(
      'linear-gradient(90deg, #3dff73 0%, #ffb020 50%, #ff4d5e 100%)',
    );
    expect(html).not.toContain('linear-gradient(90deg, #ff4d5e');
  });

  it('clips the fill to the value and scales the child back to full width', () => {
    /* value 80: fill 80% wide, child 10000/80 = 125% wide. */
    const html80 = render(feedback({ hedgingScore: 80 }));
    expect(html80).toContain('width:80%');
    expect(html80).toContain('width:125%');
    /* value 25: fill 25% wide, child 10000/25 = 400% wide. */
    const html25 = render(feedback({ hedgingScore: 25 }));
    expect(html25).toContain('width:25%');
    expect(html25).toContain('width:400%');
  });

  it('renders no fill at zero', () => {
    const html = render(feedback({ hedgingScore: 0 }));
    expect(html).not.toContain('width:0%');
    expect(html).toContain('#3dff73'); // tone: green
  });

  it('the number color and the meter zone agree at a bad score', () => {
    /* 80: red number (#ff4d5e) AND an 80%-wide fill whose leading edge
       sits in the red zone of the inverted gradient. */
    const html = render(feedback({ hedgingScore: 80 }));
    expect(html).toContain('#ff4d5e');
    expect(html).toContain('width:80%');
    expect(html).toContain('Lots of hedging');
  });
});
