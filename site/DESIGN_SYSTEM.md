# VETO Design System — "Pixel Arcade"

The visual language of the Veto marketing site. Chunky 8-bit chrome over
clean primitives: pixel display type, terminal body type, hard offset
shadows, scanlines, zero border-radius. Everything looks like it could
run on a CRT.

## Principles

1. **The refusal is the brand.** Veto red (`--veto`) is reserved for the
   brand signal: vetoes, warnings-that-matter, primary CTAs, the logo.
2. **Terminals, not cards.** Content lives in bordered panels with hard
   shadows, not floating rounded cards.
3. **Two fonts, no more.** Press Start 2P for display, VT323 for
   terminal-flavored text, system sans for long-form body.
4. **Flat is a bug.** Every interactive surface has a 3px border and an
   offset shadow. Hover lifts it; active presses it.
5. **Honesty is a layout choice.** Limitations ("boss fights") get the
   same visual weight as features.

## Palette

| Token        | Value               | Use                                    |
|--------------|---------------------|----------------------------------------|
| `--bg`       | `#0d0d12`           | Page background                          |
| `--surface`  | `#14141c`           | Panels, cards                            |
| `--surface-2`| `#1b1b26`           | Raised surfaces, terminal bar            |
| `--terminal-bg` | `#08080c`        | Terminal / code interiors                |
| `--line`     | `#2c2c3d`           | Borders                                  |
| `--veto`     | `#ff4d5e`           | Brand red: vetoes, primary CTA, logo     |
| `--veto-dark`| `#b81f30`           | Deep red accents                         |
| `--go`       | `#3dff73`           | Success, terminal prompt, "go" states    |
| `--amber`    | `#ffb000`           | Warnings, secondary signals              |
| `--cyan`     | `#41e6ff`           | Code tokens, inline code                 |
| `--ink`      | `#f2f0e9`           | Primary text                             |
| `--ink-dim`  | `#a9a7ba`           | Secondary text                           |
| `--ink-faint`| `#6f6d84`           | Tertiary text, labels                    |

Shadows: `--shadow: 6px 6px 0 rgba(0,0,0,.55)`,
`--shadow-sm: 4px 4px 0 rgba(0,0,0,.55)`. Never blur, never spread.

## Typography

- **Display:** `'Press Start 2P'` (`--font-px`). Headings, buttons,
  wordmark, verdict marks. Always uppercase. Sizes: hero
  `clamp(26px, 4.4vw, 44px)`, section `clamp(17px, 2.6vw, 24px)`,
  buttons `11px` (nav `9px`), labels `10–13px`. Line-height ≥ 1.45 —
  the glyphs are tall.
- **Terminal:** `'VT323'` (`--font-term`). Tags, terminal output, nav
  links, FAQ questions, stat lines. Sizes `18–24px` (VT323 runs small;
  never use it under 18px). Uppercase with `0.04–0.14em` letter-spacing
  for labels.
- **Body:** system sans. Long-form paragraphs only
  (`.feature-body`, `.faq-a`, `.limit-item p`). `15.5–16.5px`,
  `line-height 1.6–1.65`.

### Glyph allowlist (do not regress)

Both fonts have **limited character sets**. Anything outside the
allowlist falls back to the system font and breaks pixel consistency.
Verified against the shipped TTFs with fontTools.

**Safe in both fonts:** ASCII letters/digits, `> < + - _ / $ # @ ! ? . , : ;`
`" ' ( ) [ ]`, space, `—` `–` `’` `…` `·` `«` `»` `©`.

**Press Start 2P only:** `→` `★` `▶`.

**NEVER use in either font:** `✓` `✕` `↻` `𝕏` `▸` `↑` `↓` `●` `■` `○`.

Substitutions (already applied site-wide):
`✓`→`+`, `✕`→`X`, `→`→`>`, `←`→`<`, `↻`→`>`, `𝕏`→plain text,
`▸`→`>`. The veto mark is the letter **X** — it echoes the logo.

## Spacing

Base unit **8px**. Scale: `8 / 12 / 14 / 16 / 20 / 24 / 28 / 30 / 36 / 44 / 56 / 64 / 88`.

- Section rhythm: `88px` vertical padding desktop, `64px` mobile.
- Tag → heading: `22–26px`.
- Heading → body: `14–22px`.
- Card padding: `24px` (panels `28px`).
- Grid gaps: `20px` cards, `12–14px` button rows, `14px` FAQ/limits stacks.
- Never let text touch a border: minimum `12px` inner clearance on
  chips/tags, `18px` on panels.

## Components

**`.px-btn`** — 3px solid black border, `--shadow-sm`, uppercase PS2P
11px, padding `15px 20px 13px`. Variants: `primary` (veto red bg, dark
text), `secondary` (transparent, veto border + text), `ghost`
(transparent, line border, no shadow). Hover: `translate(-2px,-2px)`,
shadow grows. Active: pressed `translate(2px,2px)`, shadow shrinks.
Motion uses `steps()` easing — no smooth tweening, ever.

**`.px-tag`** — 2px border, tinted translucent bg, VT323 19px uppercase,
`0.14em` tracking, padding `5px 12px 3px`. Variants: default green,
`.red`, `.amber`.

**`.px-hr`** — pixel divider: 8px tall repeating `8px on / 8px off`
squares in `--line`. `width: calc(100% - 48px)` under 620px so it never
touches screen edges.

**`.terminal`** — `--terminal-bg`, 3px `--line` border, `--shadow`,
VT323 20px/1.5, `min-height: 380px` (300px mobile). Bar with three
12px dots (red/amber/green). CRT scanlines via `::after` overlay.
`.t-veto` lines get a red left border and tinted bg, full-bleed within
padding via `-8px` horizontal margins. Lines wrap (`pre-wrap`).

**Panels** (`.feature-card`, `.step-card`, `.demo-job`, `.demo-q`,
`.demo-pass`, `.limit-item`, `.faq-item`) — `--surface`, 3px `--line`
border, `border-radius: 0`, `--shadow-sm`, `24–28px` padding. Astryx
`Card` defaults must always be overridden with `!important` —
unstyled Astryx cards are the #1 collision/visual-break source.

**`.faq-item`** — `details/summary`, `[+]` / `[–]` marker in veto red,
opens with red border. Question VT323 22px, answer sans 16px.

**`.px-code`** — 3px border, `--shadow-sm`, `--terminal-bg` interior,
Astryx `CodeBlock` inside with `pre { margin: 0 }`.

**Nav** — sticky, `rgba(13,13,18,.92)`, 3px bottom border. Links hidden
under 960px (CTA buttons remain).

## Page patterns

- **Hero:** tag → display title → sub → CTAs → terminal note. Page
  heroes use `.page-hero` (`76px 0 68px`) with a `< Home` back-link
  (`margin-bottom: 30px`).
- **Feature pages:** hero → "Under the hood" cards → static terminal
  demo → "Boss fights" limitations → FAQ → CTA.
- **Demo:** job card → grill questions → verdict terminal → share →
  play again.
- **Docs:** hero + TOC (hash-safe `scrollIntoView`, `scroll-margin-top:
  84px` under the sticky nav) → numbered sections → tool tables →
  risk limits → troubleshooting FAQ.

## Social cards

`public/og.png` — **1200×630**, rendered with PIL (never AI-generated,
so text stays exact). Layout: `--bg` with dot grid + scanlines, 10px
`--line` frame, pixel-X logo block, `VETO_` in Press Start 2P 92px,
`THE JOB BOT THAT SAYS NO.` in VT323 54px (NO. in veto red), terminal
strip with the veto line. Meta: `og:*` + `twitter: summary_large_image`,
absolute `https://job-apply-mcp.vercel.app/og.png` URLs.

## Responsive

- `≤960px`: hero stacks, grids go 2-col, nav links hide.
- `≤640/620px`: grids go 1-col, terminal shrinks, `.px-hr` insets,
  tool rows stack.
- Touch targets ≥ 44px. Buttons wrap with `flex-wrap`.

## Accessibility

- `prefers-reduced-motion`: caret blink off, smooth scroll off.
- Terminals are `role="img"` with `aria-label` descriptions.
- Decorative icons are `aria-hidden`.
- Contrast: veto-on-black and go-on-black pass; `ink-faint` is
  decorative/labels only, never body text.
