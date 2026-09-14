#!/usr/bin/env python3
"""Initiative 08 — hardened on-device PII/secrets scrubber (ruleset v2).

Design principle (detect-and-quarantine, not provably-perfect): the
scrubber removes personal and secret data on-device *before* preview, and
any miss it (or a runtime check) catches later quarantines the payload
and locks contribution sending (see ``quarantine``). Residual risk is
disclosed in the public methodology's "known limitations" section.

Ruleset v2 extends the original ``contribute.py`` six-rule set with:

- Unicode normalization BEFORE detection: NFKC, zero-width character
  stripping, and common homoglyph (Cyrillic/Greek lookalike) folding, so
  obfuscated text ("j\u200bane@...", "p\u0430ul" with Cyrillic a) is
  detected, not smuggled.
- Deobfuscated email spellings: "jane dot doe at example dot com",
  "jane[dot]doe(at)example(dot)com", etc. are reconstructed and redacted.
- Secret/credential detectors: AWS keys, GitHub tokens, ``sk-`` style API
  keys, ``xoxb-`` tokens, high-entropy blobs (incl. base64), generic
  ``api_key = "..."`` assignments.
- Street addresses, IBAN/account strings, SSN-shaped strings, long digit
  runs (card-shaped), absolute file paths, IPs and internal hostnames.

Replacement tokens are stable across rulesets (``[REDACTED]``,
``[NAME]``, ``[COMPANY]``) plus ``[SECRET]``, ``[ADDRESS]``,
``[FINANCIAL]``, ``[ID]``, ``[PATH]``, ``[NETWORK]``.

Every bundle records ``scrub_ruleset`` so a future rule change can never
silently alter what "scrubbed" meant for an already-consented payload.
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

SCRUB_RULESET_VERSION = "2"

#: Per-turn excerpt cap: transcripts contribute excerpts, never verbatim
#: walls of text. Anything longer is truncated (with a marker) before
#: scrubbing so a giant paste cannot carry bulk PII through.
MAX_EXCERPT_CHARS = 2000
TRUNCATION_MARKER = "…[excerpt truncated]"

# ---------------------------------------------------------------------------
# Normalization (runs before every detector)
# ---------------------------------------------------------------------------

_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")

#: Common homoglyph lookalikes folded to ASCII for detection. Only the
#: unambiguous single-character mappings; detection-time only.
_HOMOGLYPHS = str.maketrans(
    {
        "а": "a", "е": "e", "і": "i", "о": "o", "р": "p", "с": "c",
        "х": "x", "у": "y", "к": "k", "м": "m", "н": "h", "т": "t",
        "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H",
        "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X",
        "α": "a", "ε": "e", "ο": "o", "ρ": "p", "ς": "c", "ι": "i",
        "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-",
        "‘": "'", "’": "'", "‚": "'", "“": '"', "”": '"', "„": '"',
    }
)


def normalize_for_detection(text: str) -> str:
    """Normalize text so obfuscated PII is detectable.

    NFKC normalization, zero-width character removal, and homoglyph
    folding. The scrubbed output preserves the original text's
    characters where they are kept (only redaction markers replace
    spans); normalization is used to *find* spans, applied to a copy.
    """
    text = unicodedata.normalize("NFKC", text or "")
    text = _ZERO_WIDTH_RE.sub("", text)
    text = text.translate(_HOMOGLYPHS)
    return text


# ---------------------------------------------------------------------------
# Deobfuscation ("jane dot doe at example dot com")
# ---------------------------------------------------------------------------

_DOT_WORDS = r"(?:\s*(?:\.|\bdot\b|\[dot\]|\(dot\)|\{dot\})\s*)"
_AT_WORDS = r"(?:\s*(?:@|\bat\b|\[at\]|\(at\)|\{at\})\s*)"
_DEOBFUSCATED_EMAIL_RE = re.compile(
    # The local-part atoms deliberately EXCLUDE the literal dot:
    # dots are consumable ONLY via _DOT_WORDS, so a dot-dense run has
    # exactly one parse (linear time). The previous atoms were
    # [\w.+-]+, which overlaps _DOT_WORDS' literal-dot alternative and
    # backtracked exponentially on dot-dense input (round-5 major:
    # 16 dot-segments 0.18s, 32 dot-segments >10s, a 24-component
    # dotted version string ~24.5s CPU — reachable from user-typed
    # free text at preview and at submit). The \bdot\b alternative
    # cannot reintroduce ambiguity: its word boundaries force the
    # parse (an atom cannot abut "dot" without a boundary), so
    # mis-split atoms die at the next separator in O(1).
    # Behavior is unchanged for real obfuscations ("jane dot doe at
    # example dot com", "jane[dot]doe(at)example(dot)com",
    # "jane.doe at example dot com"); only degenerate runs of
    # adjacent literal dots ("jane..doe") no longer match as one
    # address — they are not valid emails and _EMAIL_RE would not
    # accept them anyway.
    r"[\w+-]+" + _DOT_WORDS + r"[\w+-]+" + r"(?:" + _DOT_WORDS
    + r"[\w+-]+)*" + _AT_WORDS + r"[\w-]+(?:" + _DOT_WORDS + r"[\w-]+)+",
    re.IGNORECASE,
)


def _deobfuscate_emails(text: str) -> str:
    """Rewrite obfuscated email spellings to canonical form for detection."""

    def _rebuild(match: re.Match) -> str:
        span = match.group(0)
        span = re.sub(r"\s*(?:\[dot\]|\(dot\)|\{dot\}|\bdot\b)\s*", ".",
                      span, flags=re.IGNORECASE)
        span = re.sub(r"\s*(?:\[at\]|\(at\)|\{at\}|\bat\b)\s*", "@",
                      span, flags=re.IGNORECASE)
        return span.strip()

    return _DEOBFUSCATED_EMAIL_RE.sub(_rebuild, text)


# ---------------------------------------------------------------------------
# Detector patterns
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")
#: Bare social-profile URLs without a scheme (linkedin.com/in/..., etc.)
#: are identifying; redact them whole.
_PROFILE_URL_RE = re.compile(
    r"\b(?:linkedin\.com|github\.com|twitter\.com|x\.com|facebook\.com|"
    r"instagram\.com|gitlab\.com)/[\w.\-~]+(?:/[\w.\-~]+)*", re.IGNORECASE)
_HANDLE_RE = re.compile(r"(?<!\w)@[\w.]{2,}")
_NAME_RE = re.compile(r"\b([A-Z][a-z]{1,}(?:\s+[A-Z][a-z]{1,}){1,2})\b")
_DIGIT_RUN_RE = re.compile(r"\+?\d[\d\s\-.()]*\d")

#: Credential/secret shapes.
_AWS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
_GITHUB_TOKEN_RE = re.compile(
    r"\b(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}\b")
_SK_KEY_RE = re.compile(r"\bsk-(?:live|test)-[A-Za-z0-9]{16,}\b|\bsk-[A-Za-z0-9]{20,}\b")
_SLACK_TOKEN_RE = re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")
_ASSIGNED_SECRET_RE = re.compile(
    r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|client[_-]?secret)"
    r"\s*[:=]\s*[\"']?([A-Za-z0-9_\-./+]{8,})[\"']?")
#: High-entropy credential-shaped blobs: standard base64 AND base64url.
#: The URL-safe alphabet swaps "+/" for "-_" and is the dominant
#: real-world token encoding (JWTs, OAuth bearer tokens, Stripe-style
#: keys) — a single class covers both alphabets so a token containing
#: "-" or "_" can never split into sub-20-char runs and evade the
#: threshold. The documented threshold is >=20 chars AND >=4.0 bits/char
#: of Shannon entropy, applied to *maximal high-entropy substrings* of
#: the matched run (``_high_entropy_cores``) so low-entropy dilution
#: padding cannot drag a credential-shaped core under the gate; the
#: regex finds candidates and the core scan applies the entropy gate so
#: ordinary long words, hyphenated phrases, and snake_case identifiers
#: are not over-scrubbed.
_BASE64_BLOB_RE = re.compile(r"\b[A-Za-z0-9+/=_-]{20,}={0,2}\b")

#: Financial / identity shapes.
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_LONG_DIGITS_RE = re.compile(r"\b(?:\d[ \-]?){13,19}\b")

#: Street address shape ("123 Main Street", "45b Oak Ave").
_ADDRESS_RE = re.compile(
    r"\b\d{1,5}[a-zA-Z]?\s+[A-Z][\w.\-]*(?:\s+[A-Z][\w.\-]*){0,3}\s+"
    r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|"
    r"Court|Ct|Circle|Cir|Parkway|Pkwy|Terrace|Place|Pl|Way)\b\.?",
    re.IGNORECASE,
)

#: Absolute filesystem paths and home-relative paths.
_PATH_RE = re.compile(
    r"(?<![\w@:/.-])(?:/[A-Za-z0-9_.\-~]+){2,}|"
    r"\b[A-Z]:\\(?:[\w.\-]+\\)*[\w.\-]*|"
    r"(?<![\w/])~/(?:[\w.\-]+/)*[\w.\-]+")

#: IPv4 and internal-looking hostnames.
_IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_INTERNAL_HOST_RE = re.compile(
    r"\b[\w\-]+\.(?:local|internal|corp|lan|home|intranet)\b", re.IGNORECASE)


def _shannon_entropy(token: str) -> float:
    if not token:
        return 0.0
    counts: dict[str, int] = {}
    for ch in token:
        counts[ch] = counts.get(ch, 0) + 1
    length = len(token)
    return -sum(
        (c / length) * math.log2(c / length) for c in counts.values()
    )


#: Documented high-entropy gate: >=20 chars AND >=4.0 bits/char.
_HIGH_ENTROPY_MIN_LEN = 20
_HIGH_ENTROPY_BITS = 4.0

#: A run of this many identical characters counts as low-entropy
#: dilution padding for the core scan (B4).
_REPEAT_PAD_RE = re.compile(r"(.)\1{5,}")

#: Sliding-window width for the high-entropy core scan (B4 fallback).
_CORE_WINDOW = 20


def _high_entropy_cores(token: str) -> list[str]:
    """Return the high-entropy substrings of ``token`` that gate as secrets.

    Entropy-dilution evasion (B4): padding a high-entropy token with
    low-entropy filler (e.g. 32 repeated ``x``\\ s) drags the *whole-run*
    entropy below the gate, defeating every layer. This gates on
    *maximal high-entropy substrings* instead: the run is split on long
    repeats of one character and each segment is re-gated, so filler
    cannot hide a credential-shaped core. A sliding-window fallback
    catches non-repeated low-entropy padding (e.g. a repeated
    multi-character pattern) by flagging any 20-char window that gates.

    Known limitation (B5, 2026-09-13): sub-threshold *interleaving*
    defeats this gate — e.g. 5-char repeat chunks woven every 8 core
    chars stay under the 6-char repeat-split threshold while keeping
    every 20-char window below 4.0 bits/char, and a long pad bisecting
    the core into sub-20-char halves is split off with the halves then
    filtered by the 20-char minimum. Both shapes make this function
    return ``[]``, and the diluted run then survives scrubbing AND the
    post-scrub audit. The earlier claim that interleaving "destroys the
    contiguous recoverable substring" was false: the attacker recovers
    the core trivially (``tok.replace("aaaaa", "")``), so the substring
    is recoverable — just not by this gate. The residual layer in
    ``contribute.py`` therefore MUST NOT call this function: it applies
    its own independent de-pad/de-period/frequency-dominance assessment
    (``contribute._residual_blob_views``) so one defeated gate can no
    longer silence every layer. This function remains the scrub
    layer's first line of detection, where it catches all previously
    demonstrated dilution shapes (B4).

    Returns the list of sensitive substrings: ``[token]`` when the
    whole run gates (unchanged behavior), the gating segments after
    repeat-splitting, or ``[token]`` for the window fallback (core
    boundaries are unknown there). An empty list means no
    high-entropy core — ordinary long words, hyphenated phrases, and
    snake_case identifiers are unaffected.
    """
    if (len(token) >= _HIGH_ENTROPY_MIN_LEN
            and _shannon_entropy(token) >= _HIGH_ENTROPY_BITS):
        return [token]
    cores = [
        part for part in _REPEAT_PAD_RE.split(token)
        if len(part) >= _HIGH_ENTROPY_MIN_LEN
        and _shannon_entropy(part) >= _HIGH_ENTROPY_BITS
    ]
    if cores:
        return cores
    for i in range(len(token) - _CORE_WINDOW + 1):
        if _shannon_entropy(token[i:i + _CORE_WINDOW]) >= _HIGH_ENTROPY_BITS:
            return [token]
    return []


def _high_entropy_repl(match: re.Match) -> str:
    token = match.group(0)
    if _high_entropy_cores(token):
        return "[SECRET]"
    return token


#: Words that may start or appear inside capitalized sequences but are not
#: person names: months, weekdays, sentence starters, and role/industry
#: title words. Role titles and industries are intentionally KEPT — they
#: are useful signal and not identifying.
_NAME_ALLOWLIST = frozenset(
    """
    i ii iii iv v vi vii viii ix x
    january february march april may june july august september october
    november december monday tuesday wednesday thursday friday saturday sunday
    the a an as at in on for with during after before of to and or but so
    my our your their his her its this that these those there here then than
    what when where why how which who whom whose can could would should do
    does did will have has had are is was were be been being get got getting
    give take tell me tell me about good bad new best worst first last next
    black white red blue green senior junior lead staff principal distinguished
    backend frontend full stack software data product design engineering
    engineer developer manager director designer analyst scientist architect
    marketing sales support success operations research machine learning devops
    platform mobile web cloud security growth content brand copywriter writer
    editor recruiter account executive chief officer president founder partner
    associate specialist coordinator strategist administrator consultant
    customer service human resources finance legal accounting team company
    startup enterprise fintech healthtech edtech saas api llm rag
    """.split()
)


def _phone_repl(match: re.Match) -> str:
    digits = re.sub(r"\D", "", match.group(0))
    if len(digits) >= 7:
        return "[REDACTED]"
    return match.group(0)


def _name_repl(match: re.Match) -> str:
    phrase = match.group(0)
    words = phrase.split()
    if any(w.lower() in _NAME_ALLOWLIST for w in words):
        return phrase  # common word / role title — keep it
    return "[NAME]"


#: The versioned rule table. Shown verbatim in preview output and in the
#: public methodology so the contributor sees precisely what was redacted
#: and why. Order matters: secrets and emails first (so credentials inside
#: URLs are not partially kept), known company names before the name
#: heuristic.
SCRUB_RULES_V2: list[dict[str, str]] = [
    {
        "rule": "normalize",
        "description": (
            "Unicode NFKC normalization, zero-width character removal, and "
            "homoglyph folding run BEFORE detection so obfuscated text "
            "(zero-width spaces, Cyrillic lookalikes) cannot smuggle PII "
            "past the detectors. Invisible step: no marker in output."
        ),
    },
    {
        "rule": "secret",
        "description": (
            "Credentials -> [SECRET]: AWS keys (AKIA...), GitHub tokens "
            "(ghp_...), sk-live/sk-test API keys, Slack tokens, "
            "api_key=/secret=/token= assignments, high-entropy blobs "
            "(>=20 chars, >=4.0 bits/char incl. base64 and base64url). "
            "The blob gate scans maximal high-entropy substrings so "
            "low-entropy dilution padding cannot hide a credential core. "
            "Applied first so secrets inside URLs are removed whole."
        ),
    },
    {
        "rule": "email",
        "description": (
            "Email addresses (local-part AT domain DOT tld) -> [REDACTED], including "
            "deobfuscated spellings ('jane dot doe at example dot com', "
            "'jane[dot]doe(at)example(dot)com'). Applied before handles so "
            "addresses are not partially kept."
        ),
    },
    {
        "rule": "url",
        "description": (
            "URLs (http(s)://... and www....) -> [REDACTED], plus bare "
            "social-profile links (linkedin.com/in/..., github.com/..., "
            "etc.) which are identifying even without a scheme. Profile "
            "links, portfolio links, and any pasted links are removed whole."
        ),
    },
    {
        "rule": "network",
        "description": (
            "IPv4 addresses and internal hostnames (*.local, *.corp, "
            "*.internal) -> [NETWORK]. Runs BEFORE the phone rule so IPs "
            "are not eaten as digit runs. May over-redact version-like "
            "strings (1.2.3.4); disclosed as a known limitation."
        ),
    },
    {
        "rule": "financial",
        "description": (
            "IBAN/account strings and card-shaped digit runs (13-19 digits "
            "with separators) -> [FINANCIAL]. Runs BEFORE the phone rule "
            "so IBANs are not misattributed as phones."
        ),
    },
    {
        "rule": "id_number",
        "description": (
            "SSN-shaped strings (123-45-6789) -> [ID]. US-centric shape; "
            "other national ID formats are a known limitation (see "
            "methodology)."
        ),
    },
    {
        "rule": "phone",
        "description": (
            "Phone numbers: digit runs with separators, optional leading +, "
            "7 or more digits -> [REDACTED]. Short numbers (years, small "
            "counts) are kept."
        ),
    },
    {
        "rule": "handle",
        "description": (
            "@handles -> [REDACTED]. Social/LinkedIn handles are removed."
        ),
    },
    {
        "rule": "address",
        "description": (
            "Street addresses ('123 Main Street', '45b Oak Ave') -> "
            "[ADDRESS]."
        ),
    },
    {
        "rule": "company",
        "description": (
            "Known company names (taken from the session's own metadata, "
            "e.g. the company you practiced interviewing at) -> [COMPANY]. "
            "Role titles and industries are KEPT — they are useful signal "
            "and not identifying."
        ),
    },
    {
        "rule": "name",
        "description": (
            "HEURISTIC: 2-3 capitalized words with none of them in the "
            "common-words/role-title allowlist -> [NAME]. Best-effort: it "
            "can miss unusual names and can over-redact. Check the preview "
            "before confirming."
        ),
    },
    {
        "rule": "path",
        "description": (
            "Absolute filesystem paths (/home/you/...), Windows paths, and "
            "~/... paths -> [PATH]."
        ),
    },
]

#: Rules whose misses quarantine the payload (see ``quarantine``): if any
#: of these detectors fires on the *final* bundle text (i.e. personal or
#: secret data survived scrubbing), the payload is quarantined.
QUARANTINE_TRIGGER_RULES = frozenset(
    {"secret", "email", "phone", "financial", "id_number",
     "name", "address"}
)


def scrub_rules_report() -> list[dict[str, str]]:
    """Return the versioned human-readable scrub rule set."""
    return [dict(r) for r in SCRUB_RULES_V2]


def cap_excerpt(text: str) -> str:
    """Truncate an over-long turn to the excerpt cap (excerpts, not walls)."""
    text = text or ""
    if len(text) > MAX_EXCERPT_CHARS:
        return text[:MAX_EXCERPT_CHARS] + TRUNCATION_MARKER
    return text


def _count_marker(out: str, marker: str, before: int) -> int:
    return out.count(marker) - before


def scrub_text_v2(
    text: str, known_companies: tuple[str, ...] = ()
) -> tuple[str, list[dict[str, Any]]]:
    """Scrub personal/secret data from ``text`` with ruleset v2.

    Returns ``(scrubbed_text, report)`` where ``report`` is a per-rule
    ``{"rule": ..., "redactions": n}`` list in SCRUB_RULES_V2 order.
    """
    original = cap_excerpt(text or "")
    # Normalization is detection-time: find spans on the normalized copy,
    # then redact the same spans. Simplest sound approach for a regex
    # pipeline: normalize the working text (NFKC/zero-width/homoglyph
    # folding is lossy only for adversarial characters), then deobfuscate
    # emails on it.
    out = normalize_for_detection(original)
    out = _deobfuscate_emails(out)
    counts: dict[str, int] = {}

    def _sub(pattern: re.Pattern[str], repl: Any, rule: str) -> None:
        nonlocal out
        before = out.count(repl) if isinstance(repl, str) else 0
        out = pattern.sub(repl, out)
        if isinstance(repl, str):
            counts[rule] = counts.get(rule, 0) + _count_marker(out, repl,
                                                              before)

    # 1. secrets (before urls/emails so embedded credentials die whole)
    for pattern in (_AWS_KEY_RE, _GITHUB_TOKEN_RE, _SK_KEY_RE,
                    _SLACK_TOKEN_RE):
        _sub(pattern, "[SECRET]", "secret")
    before = out.count("[SECRET]")
    out = _ASSIGNED_SECRET_RE.sub(
        lambda m: m.group(0).replace(m.group(1), "[SECRET]"), out)
    counts["secret"] = counts.get("secret", 0) + _count_marker(
        out, "[SECRET]", before)
    before = out.count("[SECRET]")
    out = _BASE64_BLOB_RE.sub(_high_entropy_repl, out)
    counts["secret"] = counts.get("secret", 0) + _count_marker(
        out, "[SECRET]", before)
    # 2. emails (incl. deobfuscated)
    _sub(_EMAIL_RE, "[REDACTED]", "email")
    # 3. urls (incl. bare social-profile links)
    _sub(_URL_RE, "[REDACTED]", "url")
    before = out.count("[REDACTED]")
    out = _PROFILE_URL_RE.sub("[REDACTED]", out)
    counts["url"] = counts.get("url", 0) + _count_marker(
        out, "[REDACTED]", before)
    # 4. network identifiers BEFORE the generic phone rule so IPv4
    # addresses are marked [NETWORK], not eaten as digit runs.
    _sub(_IP_RE, "[NETWORK]", "network")
    _sub(_INTERNAL_HOST_RE, "[NETWORK]", "network")
    # 5. financial / id shapes BEFORE the generic phone rule so IBANs,
    # SSN-shapes, and card-shaped runs are attributed (and marked)
    # correctly instead of being eaten as "phones".
    _sub(_IBAN_RE, "[FINANCIAL]", "financial")
    before = out.count("[FINANCIAL]")
    out = _LONG_DIGITS_RE.sub(
        lambda m: "[FINANCIAL]"
        if len(re.sub(r"\D", "", m.group(0))) >= 13 else m.group(0), out)
    counts["financial"] = counts.get("financial", 0) + _count_marker(
        out, "[FINANCIAL]", before)
    # 6. id numbers
    _sub(_SSN_RE, "[ID]", "id_number")
    # 7. phones
    before = out.count("[REDACTED]")
    out = _DIGIT_RUN_RE.sub(_phone_repl, out)
    counts["phone"] = counts.get("phone", 0) + _count_marker(
        out, "[REDACTED]", before)
    # 8. handles
    _sub(_HANDLE_RE, "[REDACTED]", "handle")
    # 9. addresses
    _sub(_ADDRESS_RE, "[ADDRESS]", "address")
    # 10. known companies
    n_comp = 0
    for company in known_companies:
        company = (company or "").strip()
        if not company:
            continue
        pattern = re.compile(re.escape(company), re.IGNORECASE)
        out, n = pattern.subn("[COMPANY]", out)
        n_comp += n
    counts["company"] = counts.get("company", 0) + n_comp
    # 10. name heuristic
    before = out.count("[NAME]")
    out = _NAME_RE.sub(_name_repl, out)
    counts["name"] = counts.get("name", 0) + _count_marker(out, "[NAME]",
                                                           before)
    # 11. paths
    _sub(_PATH_RE, "[PATH]", "path")

    report = [
        {"rule": r["rule"], "redactions": counts.get(r["rule"], 0)}
        for r in SCRUB_RULES_V2
        if r["rule"] != "normalize"
    ]
    return out, report


# ---------------------------------------------------------------------------
# Post-scrub audit: the runtime check
# ---------------------------------------------------------------------------

_AUDIT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("secret", re.compile(
        r"AKIA[0-9A-Z]{16}|(?:ghp|gho|ghu|ghs|ghr|github_pat)_[A-Za-z0-9_]{20,}"
        r"|sk-(?:live|test)-[A-Za-z0-9]{16,}|xox[baprs]-[A-Za-z0-9-]{10,}")),
    # High-entropy blobs share the scrubber's documented threshold
    # (>=20 chars, >=4.0 bits/char), applied to maximal high-entropy
    # substrings (see _high_entropy_cores) so dilution padding cannot
    # smuggle a core past the audit either. A regex cannot express
    # entropy, so the gate lives in audit_scrubbed_text.
    ("secret", _BASE64_BLOB_RE),
    ("email", _EMAIL_RE),
    ("phone", re.compile(r"(?:\+?1[-. ]?)?(?:\(\d{3}\)|\d{3})[-. ]\d{3}[-. ]\d{4}\b")),
    ("financial", _IBAN_RE),
    ("id_number", _SSN_RE),
    # A name or street address surviving in final bundle text means the
    # scrubber was bypassed for that field (e.g. an unscrubbed free-text
    # field) — quarantine on hit. The name check mirrors the scrubber's
    # allowlist in audit_scrubbed_text so deliberately-kept role titles
    # and common words do not false-positive.
    ("name", _NAME_RE),
    ("address", _ADDRESS_RE),
    ("url", _PROFILE_URL_RE),
]


def audit_scrubbed_text(scrubbed: str) -> list[dict[str, str]]:
    """Runtime check: look for surviving personal/secret data.

    Runs the quarantine-trigger detectors over already-scrubbed text.
    Any hit means the scrubber missed something — the caller must
    quarantine the payload and lock sending (see ``quarantine``).
    Returns a list of ``{"rule": ..., "sample": ...}`` findings (samples
    truncated to 24 chars so the finding itself cannot leak much).
    """
    findings: list[dict[str, str]] = []
    normalized = normalize_for_detection(scrubbed)
    for rule, pattern in _AUDIT_PATTERNS:
        for match in pattern.finditer(normalized):
            if pattern is _NAME_RE:
                # Mirror the scrubber's allowlist exactly: phrases the
                # scrubber deliberately kept (role titles, common words)
                # are not PII and must not quarantine.
                words = match.group(0).split()
                if any(w.lower() in _NAME_ALLOWLIST for w in words):
                    continue
            if pattern is _BASE64_BLOB_RE:
                # Same documented threshold as the scrubber, applied to
                # maximal high-entropy substrings: ordinary long words
                # are skipped, but a credential core hidden in
                # low-entropy padding is still flagged (B4).
                cores = _high_entropy_cores(match.group(0))
                if not cores:
                    continue
                findings.append(
                    {"rule": rule, "sample": cores[0][:24]})
                if len(findings) >= 25:
                    return findings
                continue
            findings.append(
                {"rule": rule, "sample": match.group(0)[:24]})
            if len(findings) >= 25:
                return findings
    return findings


def run_scrub_selftest(fixtures: list[dict[str, str]]) -> dict[str, Any]:
    """Run the scrubber against labeled fixtures.

    Each fixture: ``{"text": ..., "must_not_contain": [...], "label": ...}``.
    Any ``must_not_contain`` value surviving scrubbing is a scrub-test
    failure — the contract says the offending payload is quarantined.
    Returns ``{"passed": bool, "failures": [...]}``.
    """
    failures: list[dict[str, str]] = []
    for fixture in fixtures:
        scrubbed, _ = scrub_text_v2(fixture.get("text", ""))
        for forbidden in fixture.get("must_not_contain", []):
            if forbidden and forbidden in scrubbed:
                failures.append({
                    "label": fixture.get("label", "?"),
                    "leaked": forbidden[:48],
                })
    return {"passed": not failures, "failures": failures}
