/* Shared integration types for the Chakra-inspired grill features (A–E).
 * Builders implement against these seams; DemoPage wires them together.
 * Pure-data types only — no React, no side effects.
 */

/** Feature E: a user-fed job posting, parsed into structured context. */
export interface JobContext {
  title: string;
  company: string;
  /** Raw pasted text or fetched posting body (truncated). */
  rawText: string;
  /** Extracted requirement phrases, e.g. "8+ years backend", "Kubernetes in production". */
  requirements: string[];
  /** Lowercase keywords for matching (skills, tools, domains). */
  roleKeywords: string[];
  /** Source: 'paste' | 'url'. URLs are fetched at input time; paste is primary. */
  source: 'paste' | 'url';
}

/** Feature A: reasoning narrative attached to a verdict. */
export interface ReasoningNarrative {
  /** 2–3 sentence overall read on HOW the candidate approached the grill. */
  summary: string;
  /** Per-answer narrative, in question order. */
  perAnswer: { qid: string; narrative: string }[];
}

/** Feature B: AI fluency score dimensions. */
export interface AiFluencyDimensions {
  /** Did the candidate frame the problem well for/with AI? 0–100. */
  framing: number;
  /** Did they show judgment of AI output (not blind trust)? 0–100. */
  judgment: number;
  /** Did they steer/instruct effectively? 0–100. */
  steering: number;
}
export interface AiFluencyScore {
  /** Weighted overall 0–100. */
  score: number;
  dimensions: AiFluencyDimensions;
  /** One-line plain-English read. */
  note: string;
}

/** Feature C: defend-your-answer assessment. */
export interface DefenseAssessment {
  /** Did the defense demonstrate real understanding? */
  understood: boolean;
  /** 0–100. */
  score: number;
  /** Plain-English verdict on the defense, 1–2 sentences. */
  note: string;
}

/** Feature D: a task against a real repository fixture. */
export interface RepoTask {
  id: string;
  title: string;
  /** Path under the fixture root, e.g. 'fixtures/acme-api'. */
  repoPath: string;
  /** What the candidate must do, 1–3 sentences. */
  taskDescription: string;
  /** How the grill checks the outcome (deterministic). */
  checkDescription: string;
}

/** Feature G: resume-vs-job match. Gaps feed the grill's drill selection. */
export interface ResumeMatch {
  /** 0–100 overall match. */
  score: number;
  /** Keywords/skills present in both resume and posting. */
  matchedKeywords: string[];
  /** Posting keywords missing from the resume — these become grill drill topics. */
  missingKeywords: string[];
  /** Plain-English gap statements, e.g. "Resume doesn't mention Kubernetes; the posting asks for it." */
  gaps: string[];
}

/** Feature H: delivery coaching — HOW the candidate answers, not just what. */
export interface DeliveryFeedback {
  /** Filler-word hits, e.g. ["um", "like", "you know"]. */
  fillerWords: { word: string; count: number }[];
  /** Total filler count across the analyzed text. */
  fillerTotal: number;
  /** 0–100; higher = more hedging language detected. */
  hedgingScore: number;
  /** Words-per-answer pacing note, plain English. */
  pacingNote: string;
  /** 1–3 actionable suggestions, plain English, coach tone. */
  suggestions: string[];
}
