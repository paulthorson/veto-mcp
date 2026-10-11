/* Feature B (Chakra B) E2E: AI fluency panel appears in/near the verdict.
 *
 * Drives the real demo via CDP: #/demo -> Standard level -> types rich
 * answers to all 5 grill questions -> walks honesty/score/tailor stages ->
 * asserts [data-testid="ai-fluency-panel"] is present at the verdict stage
 * with the overall score and the 3 dimensions, then screenshots to
 * /tmp/chakra-b-fluency.png.
 *
 * The panel is wired by the integrator (see demos/grill/INTEGRATION-B.md);
 * this script targets the intended [data-testid] contract. Run AFTER the
 * site is built (dist/) and the panel is mounted.
 *
 *   node site/e2e/chakra-b.e2e.mjs
 */
import { launch, newPage, serveDist } from './cdp-helper.mjs';

/* Answers engineered against the grill's deterministic classification rules
   (digit + domain-context => specific) and the AI-fluency heuristics
   (concrete numbers, tradeoff language, named tools, no hedge words). */
const ANSWERS = [
  '9 years of backend experience, mostly fintech payments processing',
  'ran EKS in production daily for 3 years; however upgrades are a tradeoff between speed and stability, and I review every rollout carefully',
  'about 50M req/day across 40 nodes, p99 latency 120ms at peak traffic, budget constraint on new instances',
  'US citizen, no sponsorship needed; 3 days a week hybrid in the NYC office works for me',
  'the payments-scale problem is exactly my thing: 50M req/day is where my EKS tuning experience pays off, though I would have to check how the on-call rotation works',
];

const PANEL = '[data-testid="ai-fluency-panel"]';

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

    // 5 grill questions: type a real answer into the input, click Send.
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

    // The AI-fluency panel: assert via its testid contract (click scrolls it
    // into view and throws if absent), then assert rendered content.
    await page.click(PANEL);
    for (const needle of ['AI fluency', 'Framing', 'Judgment', 'Steering']) {
      if (!(await page.hasText(needle))) {
        throw new Error(`verdict missing fluency content: ${needle}`);
      }
    }

    await page.screenshot('/tmp/chakra-b-fluency.png');
    console.log('PASS chakra-b: ai-fluency panel rendered at verdict, screenshot /tmp/chakra-b-fluency.png');
  } finally {
    await browser.close();
    stop();
  }
}

main().catch((e) => {
  console.error('FAIL chakra-b:', e.message);
  process.exit(1);
});
