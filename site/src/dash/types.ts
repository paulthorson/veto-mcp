/* Dashboard data model. Mirrors the Python backend where it exists:
   - applications: lifecycle.load_entries() rows (job_id, stage, stage_history)
   - report numbers: analytics.generate_report() (funnel, response_rate_by_board)
   Plus dashboard-only concepts: 'vetoed' stage (grill refusals) and
   watch_hits (watch.py new-posting diffs). A real export can be dropped
   into localStorage under VETO_DASH_KEY to replace the demo dataset. */

export const VETO_DASH_KEY = 'veto.dashboard.v1';

export type Stage =
  | 'found'
  | 'grilled'
  | 'vetoed'
  | 'applied'
  | 'interviewing'
  | 'offer'
  | 'rejected'
  | 'withdrawn'
  | 'ghosted';

export interface StageEvent {
  stage: Stage;
  at: string; // ISO-8601
  note?: string;
}

export interface PostingSnapshot {
  salary?: string;
  requirements?: string[];
}

export interface Application {
  job_id: string;
  title: string;
  company: string;
  board: string;
  salary?: string;
  stage: Stage;
  applied_at?: string; // ISO-8601
  stage_history: StageEvent[];
  posting_snapshot?: PostingSnapshot;
}

export interface WatchHit {
  watch: string;
  job_id: string;
  title: string;
  company: string;
  board: string;
  first_seen: string; // ISO-8601
}

export type DeltaTone = 'go' | 'veto' | 'amber' | '';

export interface Delta {
  id: string;
  kind: 'stage' | 'new_match' | 'posting_edit' | 'stale' | 'veto';
  at: string; // ISO-8601
  title: string;
  detail: string;
  tone: DeltaTone;
  icon: string; // PixelIcon name
}

export interface BoardStat {
  board: string;
  applied: number;
  responded: number;
  rate: number; // 0..1
}

export interface Kpis {
  active: number; // applied + interviewing
  vetoRate: number; // vetoed / (vetoed + applied+...)
  responseRate: number; // (interviewing + offer) / applied-base
  interviews: number;
  offers: number;
  medianDaysToResponse: number | null;
  total: number;
}

export interface DashboardData {
  generated_at: string;
  prev_snapshot_at: string;
  applications: Application[];
  prev_applications: Application[];
  watch_hits: WatchHit[];
}
