/* Feature F (BYOA daily companion loop): shared data types.
 * Pure-data types only — no React, no side effects.
 * Extends the Chakra grill features with the daily loop around the demo:
 * prospect pipeline tracking, check-ins, and warm-path networking.
 */

import type { JobContext } from './chakraTypes';

/** Feature F: pipeline stage for a tracked prospect. */
export type ProspectStage =
  | 'interested'
  | 'applied'
  | 'interviewing'
  | 'offer'
  | 'rejected';

/** Feature F: a job the user is pursuing, fed from feature E's JobContext. */
export interface Prospect {
  id: string;
  job: JobContext;
  stage: ProspectStage;
  /** Freeform activity log, newest last. */
  notes: string[];
  /** ISO date of the most recent activity (application, reply, interview…). */
  lastActivity: string;
  /** ISO date the prospect entered the pipeline. */
  addedAt: string;
}

/** Feature F: one daily check-in record. */
export interface CheckIn {
  /** ISO date (YYYY-MM-DD). */
  date: string;
  summary: string;
}

/** Feature F: one person in the user's network (fictional fixture data). */
export interface NetworkContact {
  id: string;
  name: string;
  company: string;
  title: string;
  /** 1 = inner circle, 2 = friendly, 3 = weak tie. */
  closeness: 1 | 2 | 3;
}

/** Feature F: a warm path toward a target company.
 * Mirrors network_crm.py's honesty contract: every path is derived only
 * from recorded contacts; an empty result means no path exists.
 */
export interface WarmPath {
  contact: NetworkContact;
  /** The mutual connection bridging a 2nd-degree path. */
  via?: NetworkContact;
  degrees: 1 | 2;
}
