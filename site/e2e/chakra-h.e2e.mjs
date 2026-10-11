/* Feature H (Chakra H) E2E: delivery coaching panel appears in/near the verdict.
 *
 * Drives the real demo via CDP: #/demo -> Standard level -> types
 * deliberately filler-laden answers to all 5 grill questions -> walks
 * honesty/score/tailor stages -> asserts [data-testid="delivery-panel"]
 * is present at the verdict stage showing filler counts and suggestions,
 * then screenshots to /tmp/chakra-h-delivery.png.
 *
 * The panel is wired by the integrator (see demos/grill/INTEGRATION-H.md);
 * this script targets the intended [data-testid] contract. Run AFTER the
 * site is built (dist/) and the panel is mounted.
 *
 *   node site/e2e/chakra-h.e2e.mjs
 */
import { launch, newPage, serveDist } from './cdp-helper.mjs';

/* Answers deliberately loaded with fillers so the delivery panel has
   something to count: um/uh/like, sentence-start "well,"/"so,", plus
   hedging ("I think", "maybe", "might"). */
const ANSWERS = [
  'um, well, I think maybe I have like, around 5 years of backend experience, sort of',
  'uh, I actually worked with, you know, Kubernetes in production, basically ran clusters for like 2 years',
  'so, I think the scale was, um, pretty big, like maybe 10 million requests per day, kind of',
  'well, I am, you know, a US citizen, and I could be in the office, uh, a few days a week',
  'um, honestly I think this role is like, a really good fit, hopefully I can, you know, contribute',
];

const PANEL = '[data-testid="delivery-panel"]';

async function main() {
  const { url, stop } = await serveDist(4173);
  const browser = await launch();
  try {
    const page = await newPage(browser, `${url}/#/demo`);

    // Features E/G mount the job + resume input steps before the level
    // select: skip through them to reach the classic demo flow.
    for (const sel of ['[data-testid="job-skip"]', '[data-testid="resume-skip"]']) {
      try {
        await page.click(sel);
      } catch (e) {
        if (!/no such element/.test(String(e && e.message))) throw e;
      }
    }

    // Level select -> Standard (second .demo-level card).
    if (!(await page.hasText('Standard'))) throw new Error('no level select rendered');
    await page.click('.demo-levels .demo-level:nth-of-type(2)');

    // 5 grill questions: type a filler-laden answer into the input, click Send.
    for (let i = 0; i < ANSWERS.length; i++) {
      await page.type('.demo-input', ANSWERS[i]);
      await page.click('.demo-send');
    }
    if (!(await page.hasText('Grill complete'))) throw new Error('grill did not complete 5/5');

    // Walk the pipeline to the verdict: honesty -> score -> tailor -> verdict.
    await page.click('.demo-opts .demo-opt'); // > Run the honesty check
    if (!(await page.hasText('honesty check'))) throw new Error('honesty stage missing');
    await page.click('.demo-opts .demo-opt'); // > See the scoring
    // NOTE: .demo-step is CSS-uppercased, so innerText comes back uppercase.
    if (!(await page.hasText('QUALIFICATION SCORING'))) throw new Error('score stage missing');
    await page.click('.demo-opts .demo-opt'); // > Preview the tailoring
    if (!(await page.hasText('TAILORING PREVIEW'))) throw new Error('tailor stage missing');
    await page.click('.demo-opts .demo-opt'); // > Get the verdict
    if (!(await page.hasText('VERDICT'))) throw new Error('verdict stage missing');

    // The delivery panel: assert via its testid contract (click scrolls it
    // into view and throws if absent), then assert rendered content:
    // filler counts, hedging, pacing, and coach suggestions.
    await page.click(PANEL);
    for (const needle of [
      'Delivery coaching',
      'Filler words',
      'Hedging',
      'Pacing',
      "Coach's notes",
    ]) {
      if (!(await page.hasText(needle))) {
        throw new Error(`verdict missing delivery content: ${needle}`);
      }
    }
    // The filler-laden answers must show up as real counts + a suggestion.
    if (!(await page.hasText('um'))) throw new Error('delivery panel missing filler detail');
    if (!(await page.hasText('silent pause'))) {
      throw new Error('delivery panel missing filler suggestion');
    }

    await page.screenshot('/tmp/chakra-h-delivery.png');
    console.log('PASS chakra-h: delivery panel rendered at verdict, screenshot /tmp/chakra-h-delivery.png');
  } finally {
    await browser.close();
    stop();
  }
}

main().catch((e) => {
  console.error('FAIL chakra-h:', e.message);
  process.exit(1);
});
