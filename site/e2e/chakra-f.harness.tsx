/* Chakra F E2E scratch harness entry.
 * Bundled by site/e2e/chakra-f.e2e.mjs with esbuild into a standalone page
 * so the companion dashboard can be driven via CDP before the integrator
 * wires it into DemoPage. Fictional data only.
 */

import { createRoot } from 'react-dom/client';
import CompanionDashboard from '../src/demos/grill/CompanionDashboard';
import PipelineBoard from '../src/demos/grill/PipelineBoard';
import { FIXTURE_NETWORK } from '../src/lib/fixtures/network';
import type { Prospect } from '../src/lib/companionTypes';

const NOW = '2026-10-11T12:00:00.000Z';

function fedJob(title: string, company: string) {
  return {
    title,
    company,
    rawText: `${title} — ${company} (fictional fixture posting)`,
    requirements: ['3+ years backend', 'Kubernetes in production'],
    roleKeywords: ['backend', 'platform'],
    source: 'paste' as const,
  };
}

const prospects: Prospect[] = [
  {
    id: 'demo-p1',
    job: fedJob('Staff Platform Engineer', 'Acme Robotics'),
    stage: 'interviewing',
    notes: ['phone screen done 2026-10-10'],
    lastActivity: '2026-10-10T15:00:00.000Z',
    addedAt: '2026-09-20T09:00:00.000Z',
  },
  {
    id: 'demo-p2',
    job: fedJob('Product Designer', 'Northwind Labs'),
    stage: 'applied',
    notes: [],
    lastActivity: '2026-10-01T09:00:00.000Z',
    addedAt: '2026-09-25T09:00:00.000Z',
  },
  {
    id: 'demo-p3',
    job: fedJob('Data Engineer', 'Vandelay Industries'),
    stage: 'interested',
    notes: ['saw posting, looks promising'],
    lastActivity: '2026-10-11T09:00:00.000Z',
    addedAt: '2026-10-11T09:00:00.000Z',
  },
];

const root = document.getElementById('root');
if (!root) throw new Error('harness: #root missing');
createRoot(root).render(
  <div>
    <PipelineBoard prospects={prospects} nowIso={NOW} />
    <CompanionDashboard
      prospects={prospects}
      network={FIXTURE_NETWORK}
      nowIso={NOW}
    />
  </div>,
);
