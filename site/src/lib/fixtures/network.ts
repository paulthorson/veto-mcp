/* Feature F fixture: fictional professional network.
 *
 * All names, companies, and titles are invented for the demo. No real
 * people, no PII. Companies are fictional ("Acme Robotics",
 * "Northwind Labs", "Beacon Analytics", "Copperline Systems",
 * "Halcyon Health", "Vandelay Industries").
 *
 * Shaped so warm paths resolve for demo prospects:
 *  - Acme Robotics: close contacts (1st-degree paths)
 *  - Northwind Labs: a close contact plus a weak tie (2nd-degree path
 *    via the close colleague)
 *  - Vandelay Industries: nobody here (no-path case)
 */

import type { NetworkContact } from '../companionTypes';

export const FIXTURE_NETWORK: NetworkContact[] = [
  {
    id: 'nc-01',
    name: 'Jordan Ellis',
    company: 'Acme Robotics',
    title: 'Senior Backend Engineer',
    closeness: 1,
  },
  {
    id: 'nc-02',
    name: 'Priya Natarajan',
    company: 'Acme Robotics',
    title: 'Engineering Manager',
    closeness: 2,
  },
  {
    id: 'nc-03',
    name: 'Sam Okafor',
    company: 'Northwind Labs',
    title: 'Product Designer',
    closeness: 1,
  },
  {
    id: 'nc-04',
    name: 'Dana Whitfield',
    company: 'Northwind Labs',
    title: 'Data Scientist',
    closeness: 3,
  },
  {
    id: 'nc-05',
    name: 'Marcus Webb',
    company: 'Beacon Analytics',
    title: 'DevOps Lead',
    closeness: 2,
  },
  {
    id: 'nc-06',
    name: 'Lena Kowalski',
    company: 'Beacon Analytics',
    title: 'Frontend Engineer',
    closeness: 1,
  },
  {
    id: 'nc-07',
    name: 'Theo Marchetti',
    company: 'Copperline Systems',
    title: 'CTO',
    closeness: 2,
  },
  {
    id: 'nc-08',
    name: 'Aisha Bello',
    company: 'Halcyon Health',
    title: 'ML Engineer',
    closeness: 1,
  },
];
