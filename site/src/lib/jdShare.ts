/* Shareable JD decoder result links.
 *
 * A share link looks like #/decoder/r/<payload>. The payload is base64url
 * of a compact JSON object. It carries ONLY scores, verdict, and flags.
 * The raw posting text is never in the URL: postings can be long and can
 * contain personal data from the poster's clipboard. An excerpt (first
 * ~140 chars) is included only when the sharer explicitly opts in.
 *
 * Integrity: the payload carries "h", the first 12 hex chars of SHA-256
 * over the canonical JSON (fixed key order, no "h" field). Decoders
 * recompute and reject mismatches, so tampered links are detectable.
 *
 * Payload schema (v1), exact fields:
 *   v:    1 (schema version)
 *   ver:  "strong" | "mixed" | "caution"
 *   sc:   verdict score, integer 0-100
 *   ts:   transparency score, integer 0-100
 *   sal:  salary range raw text (e.g. "$120k-$150k"), or the salary
 *         mention raw text when no range was found, or null
 *   salm: true when sal is a mention without a range
 *   eq:   equity term matched (e.g. "RSUs"), or null
 *   eqc:  true when the equity detail was concrete
 *   ow:   [{ p: phrase, q: evidence quote, r: read }]
 *   rs:   [{ i: impact int, r: reason text, q: evidence quote | null }]
 *   x:    OPTIONAL excerpt, only when the sharer opted in
 *   h:    integrity hash, first 12 hex chars of sha256(canonical JSON)
 *
 * Canonical JSON for hashing: keys in exactly this order
 *   v, ver, sc, ts, sal, salm, eq, eqc, ow, rs[, x]
 * (x present only when opted in), JSON.stringify of that object,
 * UTF-8 encoded, SHA-256, hex, first 12 chars.
 */

import type { JdVerdict } from './jdDecoder';

export interface ShareOverwork {
  p: string;
  q: string;
  r: string;
}

export interface ShareReason {
  i: number;
  r: string;
  q: string | null;
}

export interface SharePayload {
  v: 1;
  ver: 'strong' | 'mixed' | 'caution';
  sc: number;
  ts: number;
  sal: string | null;
  salm: boolean;
  eq: string | null;
  eqc: boolean;
  ow: ShareOverwork[];
  rs: ShareReason[];
  /** Optional excerpt: only present when the sharer opted in. */
  x?: string;
  h: string;
}

export type ShareDecodeError =
  | 'malformed'
  | 'bad-hash'
  | 'bad-version'
  | 'oversize';

export type ShareDecodeResult =
  | { ok: true; payload: SharePayload }
  | { ok: false; error: ShareDecodeError };

/* ------------------------------------------------------------------ */
/* SHA-256 (compact sync implementation, standard FIPS 180-4)           */
/* ------------------------------------------------------------------ */

const SHA_K = [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
  0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
  0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
  0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
  0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
  0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

function rotr(x: number, n: number): number {
  return ((x >>> n) | (x << (32 - n))) >>> 0;
}

/** SHA-256 of UTF-8 bytes, returned as 64 lowercase hex chars. */
function sha256Hex(data: Uint8Array): string {
  let h0 = 0x6a09e667;
  let h1 = 0xbb67ae85;
  let h2 = 0x3c6ef372;
  let h3 = 0xa54ff53a;
  let h4 = 0x510e527f;
  let h5 = 0x9b05688c;
  let h6 = 0x1f83d9ab;
  let h7 = 0x5be0cd19;

  const bitLenHi = Math.floor((data.length * 8) / 0x100000000);
  const bitLenLo = (data.length * 8) >>> 0;
  const paddedLen = (((data.length + 8) >> 6) + 1) << 6;
  const m = new Uint8Array(paddedLen);
  m.set(data);
  m[data.length] = 0x80;
  const dv = new DataView(m.buffer);
  dv.setUint32(paddedLen - 8, bitLenHi >>> 0);
  dv.setUint32(paddedLen - 4, bitLenLo);

  const w = new Uint32Array(64);
  for (let off = 0; off < paddedLen; off += 64) {
    for (let i = 0; i < 16; i++) w[i] = dv.getUint32(off + i * 4);
    for (let i = 16; i < 64; i++) {
      const s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >>> 3);
      const s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >>> 10);
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
    }
    let a = h0, b = h1, c = h2, d = h3;
    let e = h4, f = h5, g = h6, h = h7;
    for (let i = 0; i < 64; i++) {
      const s1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const ch = (e & f) ^ (~e & g);
      const t1 = (h + s1 + ch + SHA_K[i] + w[i]) >>> 0;
      const s0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const maj = (a & b) ^ (a & c) ^ (b & c);
      const t2 = (s0 + maj) >>> 0;
      h = g;
      g = f;
      f = e;
      e = (d + t1) >>> 0;
      d = c;
      c = b;
      b = a;
      a = (t1 + t2) >>> 0;
    }
    h0 = (h0 + a) >>> 0;
    h1 = (h1 + b) >>> 0;
    h2 = (h2 + c) >>> 0;
    h3 = (h3 + d) >>> 0;
    h4 = (h4 + e) >>> 0;
    h5 = (h5 + f) >>> 0;
    h6 = (h6 + g) >>> 0;
    h7 = (h7 + h) >>> 0;
  }
  return [h0, h1, h2, h3, h4, h5, h6, h7]
    .map((x) => x.toString(16).padStart(8, '0'))
    .join('');
}

/* ------------------------------------------------------------------ */
/* base64url                                                            */
/* ------------------------------------------------------------------ */

function b64urlEncode(text: string): string {
  const bytes = new TextEncoder().encode(text);
  let bin = '';
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function b64urlDecode(s: string): string | null {
  if (!/^[A-Za-z0-9\-_]+={0,2}$/.test(s)) return null;
  let b = s.replace(/-/g, '+').replace(/_/g, '/');
  const pad = b.length % 4;
  if (pad) b += '='.repeat(4 - pad);
  try {
    const bin = atob(b);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
  } catch {
    return null;
  }
}

/* ------------------------------------------------------------------ */
/* Canonical JSON + integrity hash                                      */
/* ------------------------------------------------------------------ */

/** Canonical JSON: keys in fixed schema order, x present only if set. */
function canonicalJson(p: Omit<SharePayload, 'h'>): string {
  const obj: Record<string, unknown> = {
    v: p.v,
    ver: p.ver,
    sc: p.sc,
    ts: p.ts,
    sal: p.sal,
    salm: p.salm,
    eq: p.eq,
    eqc: p.eqc,
    ow: p.ow.map((o) => ({ p: o.p, q: o.q, r: o.r })),
    rs: p.rs.map((r) => ({ i: r.i, r: r.r, q: r.q })),
  };
  if (p.x !== undefined) obj.x = p.x;
  return JSON.stringify(obj);
}

/** Integrity hash: first 12 hex chars of SHA-256 over canonical JSON. */
function integrityHash(p: Omit<SharePayload, 'h'>): string {
  const bytes = new TextEncoder().encode(canonicalJson(p));
  return sha256Hex(bytes).slice(0, 12);
}

/* ------------------------------------------------------------------ */
/* Excerpt (opt-in only)                                                */
/* ------------------------------------------------------------------ */

export const EXCERPT_LEN = 140;

/** First ~140 chars of the posting, whitespace-collapsed, word-snapped. */
export function makeExcerpt(text: string): string {
  const flat = text.replace(/\s+/g, ' ').trim();
  if (flat.length <= EXCERPT_LEN) return flat;
  const cut = flat.slice(0, EXCERPT_LEN);
  const lastSpace = cut.lastIndexOf(' ');
  const snipped =
    lastSpace > EXCERPT_LEN - 30 ? cut.slice(0, lastSpace).trimEnd() : cut.trimEnd();
  return `${snipped}...`;
}

/* ------------------------------------------------------------------ */
/* Encode                                                               */
/* ------------------------------------------------------------------ */

/**
 * Build the URL payload from a decode result. Returns null when the
 * verdict carries no signals (the empty-input path).
 */
export function buildSharePayload(
  result: JdVerdict,
  excerpt: string | null,
): string | null {
  const s = result.signals;
  if (s == null) return null;
  const body: Omit<SharePayload, 'h'> = {
    v: 1,
    ver: result.verdict,
    sc: result.score,
    ts: s.transparency.score,
    sal: s.transparency.salary_range
      ? s.transparency.salary_range.raw
      : s.transparency.salary_mention
        ? s.transparency.salary_mention.raw
        : null,
    salm:
      s.transparency.salary_range == null &&
      s.transparency.salary_mention != null,
    eq: s.transparency.equity ? s.transparency.equity.term : null,
    eqc: s.transparency.equity ? s.transparency.equity.concrete : false,
    ow: s.overwork.map((o) => ({ p: o.phrase, q: o.quote, r: o.read })),
    rs: result.reasons.map((r) => ({ i: r.impact, r: r.reason, q: r.quote })),
    ...(excerpt != null && excerpt.length > 0 ? { x: excerpt } : {}),
  };
  const h = integrityHash(body);
  // h goes last; JSON.parse preserves the canonical key order.
  const finalObj = JSON.parse(canonicalJson(body)) as Record<string, unknown>;
  finalObj.h = h;
  return b64urlEncode(JSON.stringify(finalObj));
}

/** Full shareable URL for a payload, using the current page location. */
export function buildShareUrl(payload: string): string {
  return `${window.location.origin}${window.location.pathname}#/decoder/r/${payload}`;
}

/* ------------------------------------------------------------------ */
/* Decode + validate                                                    */
/* ------------------------------------------------------------------ */

const MAX_PAYLOAD_CHARS = 20000;
const MAX_CANONICAL_CHARS = 16000;
const MAX_STR = 1200;
const MAX_REASON = 600;
const MAX_OW = 40;

function isIntIn(x: unknown, lo: number, hi: number): x is number {
  return typeof x === 'number' && Number.isInteger(x) && x >= lo && x <= hi;
}

function isShortStr(x: unknown, max: number): x is string {
  return typeof x === 'string' && x.length <= max;
}

function validOverwork(o: unknown): o is ShareOverwork {
  if (typeof o !== 'object' || o == null) return false;
  const r = o as Record<string, unknown>;
  return (
    isShortStr(r.p, 80) && isShortStr(r.q, MAX_STR) && isShortStr(r.r, MAX_STR)
  );
}

function validReason(r: unknown): r is ShareReason {
  if (typeof r !== 'object' || r == null) return false;
  const x = r as Record<string, unknown>;
  return (
    isIntIn(x.i, -100, 100) &&
    isShortStr(x.r, MAX_REASON) &&
    (x.q === null || isShortStr(x.q, MAX_STR))
  );
}

export function decodeSharePayload(payload: string): ShareDecodeResult {
  if (typeof payload !== 'string' || payload.length === 0 || payload.length > MAX_PAYLOAD_CHARS) {
    return { ok: false, error: 'malformed' };
  }
  const json = b64urlDecode(payload);
  if (json == null || json.length > MAX_CANONICAL_CHARS) {
    return { ok: false, error: 'malformed' };
  }
  let raw: unknown;
  try {
    raw = JSON.parse(json);
  } catch {
    return { ok: false, error: 'malformed' };
  }
  if (typeof raw !== 'object' || raw == null) return { ok: false, error: 'malformed' };
  const o = raw as Record<string, unknown>;

  if (o.v !== 1) return { ok: false, error: 'bad-version' };
  if (o.ver !== 'strong' && o.ver !== 'mixed' && o.ver !== 'caution') {
    return { ok: false, error: 'malformed' };
  }
  if (!isIntIn(o.sc, 0, 100) || !isIntIn(o.ts, 0, 100)) {
    return { ok: false, error: 'malformed' };
  }
  if (o.sal !== null && !isShortStr(o.sal, 200)) return { ok: false, error: 'malformed' };
  if (typeof o.salm !== 'boolean') return { ok: false, error: 'malformed' };
  if (o.eq !== null && !isShortStr(o.eq, 80)) return { ok: false, error: 'malformed' };
  if (typeof o.eqc !== 'boolean') return { ok: false, error: 'malformed' };
  if (!Array.isArray(o.ow) || o.ow.length > MAX_OW || !o.ow.every(validOverwork)) {
    return { ok: false, error: 'malformed' };
  }
  if (!Array.isArray(o.rs) || o.rs.length > 3 || !o.rs.every(validReason)) {
    return { ok: false, error: 'malformed' };
  }
  if (o.x !== undefined && !isShortStr(o.x, EXCERPT_LEN + 10)) {
    return { ok: false, error: 'malformed' };
  }
  if (!/^[0-9a-f]{12}$/.test(String(o.h))) return { ok: false, error: 'malformed' };

  const { h, ...body } = o;
  const expected = integrityHash(body as Omit<SharePayload, 'h'>);
  if (h !== expected) return { ok: false, error: 'bad-hash' };

  return {
    ok: true,
    payload: {
      v: 1,
      ver: o.ver,
      sc: o.sc,
      ts: o.ts,
      sal: o.sal,
      salm: o.salm,
      eq: o.eq,
      eqc: o.eqc,
      ow: o.ow as ShareOverwork[],
      rs: o.rs as ShareReason[],
      ...(typeof o.x === 'string' ? { x: o.x as string } : {}),
      h: h as string,
    },
  };
}

/** Extract the payload segment from a #/decoder/r/<payload> hash. */
export function payloadFromHash(hash: string): string | null {
  const prefix = '#/decoder/r/';
  if (!hash.startsWith(prefix)) return null;
  const seg = hash.slice(prefix.length).split(/[?#]/, 1)[0];
  return seg.length > 0 ? seg : null;
}
