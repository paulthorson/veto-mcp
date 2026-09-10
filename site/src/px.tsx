/* Shared pixel-brand primitives for all site pages. */
import { useCallback, useRef, useState } from 'react';
import { BOT_FH, BOT_FW, BUILDER_STRIP, MINER_STRIP } from './botSprites';

export const GITHUB_URL = 'https://github.com/paulthorson/job-apply-mcp';
export const SITE_URL = 'https://job-apply-mcp.vercel.app';

export function PixelX({ size = 30 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      shapeRendering="crispEdges"
      className="brand-mark"
      aria-hidden="true"
    >
      <rect width="16" height="16" fill="#0d0d12" />
      <g fill="#ff4d5e">
        <rect x="3" y="3" width="2" height="2" />
        <rect x="11" y="3" width="2" height="2" />
        <rect x="5" y="5" width="2" height="2" />
        <rect x="9" y="5" width="2" height="2" />
        <rect x="7" y="7" width="2" height="2" />
        <rect x="5" y="9" width="2" height="2" />
        <rect x="9" y="9" width="2" height="2" />
        <rect x="3" y="11" width="2" height="2" />
        <rect x="11" y="11" width="2" height="2" />
      </g>
    </svg>
  );
}

export function PxBtn({
  variant = 'primary',
  href,
  children,
  label,
  target,
}: {
  variant?: 'primary' | 'secondary' | 'ghost';
  href: string;
  children: React.ReactNode;
  label: string;
  target?: string;
}) {
  return (
    <a
      className={`px-btn ${variant}`}
      href={href}
      aria-label={label}
      target={target}
      rel={target === '_blank' ? 'noreferrer' : undefined}
    >
      {children}
    </a>
  );
}

export function PxTag({
  variant = '',
  children,
}: {
  variant?: '' | 'red' | 'amber';
  children: React.ReactNode;
}) {
  return <span className={`px-tag ${variant}`}>{children}</span>;
}

/* ------------------------------------------------------------------ */
/* Pixel icons — hand-drawn 16x16 bitmaps rendered as crisp SVG rects. */
/* No vector glyphs, no font fallbacks: every pixel is explicit.       */
/* ------------------------------------------------------------------ */

const PIXEL_ICONS: Record<string, string[]> = {
  search: [
    '.....######.....',
    '...##########...',
    '..############..',
    '..###......###..',
    '.###........###.',
    '.##..........##.',
    '###..........###',
    '###..........###',
    '###..........###',
    '.##..........##.',
    '.###........###.',
    '..###......###..',
    '..############..',
    '...##########...',
    '.....######..##.',
    '.............###',
  ],
  question: [
    '....######......',
    '..##########....',
    '.####....####...',
    '.###......###...',
    '..........###...',
    '.........###....',
    '........###.....',
    '.......###......',
    '......###.......',
    '......###.......',
    '......###.......',
    '................',
    '......###.......',
    '......###.......',
    '................',
    '................',
  ],
  pencil: [
    '..............##',
    '.............###',
    '............####',
    '...........#####',
    '..........#####.',
    '.........#####..',
    '........#####...',
    '.......#####....',
    '......#####.....',
    '.....#####......',
    '....#####.......',
    '...#####........',
    '..#####.........',
    '.#####..........',
    '.####...........',
    '..##............',
  ],
  clipboard: [
    '.....######.....',
    '.....######.....',
    '...##########...',
    '..############..',
    '..############..',
    '..###......###..',
    '..###.####.###..',
    '..###.####.###..',
    '..###......###..',
    '..###.####.###..',
    '..###.####.###..',
    '..###......###..',
    '..############..',
    '..############..',
  ],
  hourglass: [
    '.##############.',
    '.##############.',
    '..############..',
    '...##########...',
    '....########....',
    '.....######.....',
    '.....######.....',
    '....########....',
    '...##########...',
    '..############..',
    '.##############.',
    '.##############.',
  ],
  envelope: [
    '################',
    '################',
    '.##..........##.',
    '.###........###.',
    '.####......####.',
    '.#####....#####.',
    '.######..######.',
    '.##############.',
    '.##############.',
    '.##############.',
    '.##############.',
    '.##############.',
  ],
  chat: [
    '..############..',
    '.##############.',
    '.##############.',
    '.###..####..###.',
    '.###..####..###.',
    '.##############.',
    '.##############.',
    '.##############.',
    '..############..',
    '..############..',
    '...####.........',
    '....###.........',
    '.....##.........',
  ],
  chart: [
    '................',
    '............##..',
    '............##..',
    '........##..##..',
    '........##..##..',
    '....##..##..##..',
    '....##..##..##..',
    '....##..##..##..',
    '##..##..##..##..',
    '##..##..##..##..',
    '##..##..##..##..',
    '################',
    '################',
  ],
  x: [
    '###..........###',
    '####........####',
    '#####......#####',
    '.#####....#####.',
    '..#####..#####..',
    '...##########...',
    '....########....',
    '.....######.....',
    '.....######.....',
    '....########....',
    '...##########...',
    '..#####..#####..',
    '.#####....#####.',
    '#####......#####',
    '####........####',
    '###..........###',
  ],
  shield: [
    '....########....',
    '..############..',
    '.##############.',
    '.##############.',
    '.###........###.',
    '.###.....##.###.',
    '.###....##..###.',
    '.###...##...###.',
    '..###..##..###..',
    '...#####..###...',
    '...####...###...',
    '....###..###....',
    '....#######.....',
    '.....#####......',
    '......###.......',
    '.......#........',
  ],
  gauge: [
    '................',
    '....########....',
    '..############..',
    '.####......####.',
    '.##..........##.',
    '.#......#.....#.',
    '##.....##.....##',
    '##....##......##',
    '##....#.......##',
    '##............##',
    '##............##',
    '##.....##.....##',
    '..############..',
    '................',
  ],
  ledger: [
    '...##########...',
    '..############..',
    '..############..',
    '..###......###..',
    '..###.####.###..',
    '..###.####.###..',
    '..###......###..',
    '..###.####.###..',
    '..###.####.###..',
    '..###......###..',
    '..###.####.###..',
    '..####..####....',
    '...##....##.....',
    '................',
  ],
  doc: [
    '....########....',
    '..############..',
    '..############..',
    '..###......###..',
    '..###.####.###..',
    '..###.####.###..',
    '..###......###..',
    '..###.####.###..',
    '..###.####.###..',
    '..###......###..',
    '..###......###..',
    '..############..',
    '..############..',
  ],
  list: [
    '.##############.',
    '.##############.',
    '................',
    '.##############.',
    '.##############.',
    '................',
    '.##############.',
    '.##############.',
    '................',
    '.##########.....',
    '.##########.....',
  ],
  check: [
    '................',
    '..............#.',
    '.............##.',
    '............##..',
    '#..........##...',
    '##........##....',
    '###......##.....',
    '####....##......',
    '.####..##.......',
    '..######........',
    '...####.........',
    '....##..........',
  ],
  warn: [
    '.##############.',
    '.##..........##.',
    '.##....##....##.',
    '.##....##....##.',
    '.##....##....##.',
    '.##....##....##.',
    '.##....##....##.',
    '.##....##....##.',
    '.##..........##.',
    '.##....##....##.',
    '.##....##....##.',
    '.##..........##.',
    '.##############.',
  ],
  lock: [
    '....########....',
    '...###....###...',
    '...##......##...',
    '...##......##...',
    '...##......##...',
    '..############..',
    '..############..',
    '..####.##.####..',
    '..####.##.####..',
    '..####.##.####..',
    '..####....####..',
    '..############..',
    '..############..',
  ],
  bolt: [
    '..........####..',
    '.........####...',
    '........####....',
    '.......####.....',
    '......####......',
    '.....########...',
    '....#########...',
    '.....######.....',
    '......####......',
    '.....####.......',
    '....####........',
    '...####.........',
    '..####..........',
    '.####...........',
    '.###............',
  ],
  star: [
    '......#.........',
    '......#.........',
    '.....###........',
    '.....###........',
    '.###########....',
    '#############...',
    '..#########.....',
    '...#######......',
    '...#####........',
    '..####.####.....',
    '..###...###.....',
    '.###.....###....',
    '.##.......##....',
  ],
  globe: [
    '....########....',
    '..############..',
    '.####..##..####.',
    '.##....##....##.',
    '##.....##.....##',
    '#......##......#',
    '#......##......#',
    '#......##......#',
    '#......##......#',
    '#......##......#',
    '##.....##.....##',
    '.##....##....##.',
    '.####..##..####.',
    '..############..',
    '....########....',
  ],
};

function iconPath(rows: string[]): string {
  let d = '';
  rows.forEach((row, y) => {
    for (let x = 0; x < row.length; x++) {
      if (row[x] === '#') d += `M${x} ${y}h1v1h-1z`;
    }
  });
  return d;
}

export function PixelIcon({ name, size = 30 }: { name: string; size?: number }) {
  const rows = PIXEL_ICONS[name] ?? PIXEL_ICONS.list;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="currentColor"
      shapeRendering="crispEdges"
      aria-hidden="true"
      focusable="false"
    >
      <path d={iconPath(rows)} />
    </svg>
  );
}

/* Maps legacy unicode-glyph icon values (home + drill-down specs) to
   pixel icon names. Pass-through for values that are already names. */
const GLYPH_TO_ICON: Record<string, string> = {
  '▦': 'search', // U+25A6
  '?': 'question',
  '✎': 'pencil', // U+270E
  '✉': 'envelope', // U+2709
  '◈': 'chat', // U+25C8
  '◉': 'star', // U+25C9
  '⛨': 'x', // U+26E8
  '⊘': 'shield', // U+2298
  '◐': 'gauge', // U+25D0
  '≣': 'chart', // U+2263
  '▣': 'clipboard', // U+25A3
  '☰': 'list', // U+2630
  '≡': 'list', // U+2261
  '✚': 'check', // U+271A
  '✔': 'check', // U+2714
  '✓': 'check', // U+2713
  '✕': 'x', // U+2715
  '⌁': 'globe', // U+2301
  '⊟': 'doc', // U+25A4
  '◔': 'hourglass', // U+25D4
};

export function resolveIcon(glyph: string): string {
  if (PIXEL_ICONS[glyph]) return glyph;
  return GLYPH_TO_ICON[glyph] ?? 'list';
}

/* ------------------------------------------------------------------ *//* Worker bots — built from real DOM/CSS, not sprite bitmaps.              */
/* Each bot is a blocky little machine: antenna, head, glowing eyes,    */
/* torso with a pulsing core, articulated arms, legs, and a work prop.  */
/* The miner swings a pick into a rock (sparks on impact); the builder  */
/* pounds a hammer onto stacked blocks. Tap/click to mutate + split.    */
/* ------------------------------------------------------------------ */

export type BotVariant = 'miner' | 'builder';

/* Hand-designed pixel-art worker bot. The sprite strip (3 frames of 52x38)
 * is drawn as one SVG path per color; CSS steps the strip for the work
 * cycle. Crisp at integer scales only. */
export function PixelBot({
  variant,
  label,
}: {
  variant: BotVariant;
  label?: string;
}) {
  const strip = variant === 'miner' ? MINER_STRIP : BUILDER_STRIP;
  return (
    <svg
      className={`pxbot pxbot-${variant}`}
      viewBox={`0 0 ${BOT_FW} ${BOT_FH}`}
      shapeRendering="crispEdges"
      role="img"
      aria-label={label ?? `${variant} bot`}
    >
      <g className="pxbot-strip">
        {strip.map(([color, d]) => (
          <path key={color} d={d} fill={color} />
        ))}
      </g>
    </svg>
  );
}

type BotUnit = { id: number; variant: BotVariant; born: boolean };

/* A tappable crew: click a bot, it mutates, then splits into two. */
export function BotCrew({ max = 6 }: { max?: number }) {
  const [bots, setBots] = useState<BotUnit[]>([
    { id: 0, variant: 'miner', born: false },
    { id: 1, variant: 'builder', born: false },
  ]);
  const [mutatingId, setMutatingId] = useState<number | null>(null);
  const [deniedId, setDeniedId] = useState<number | null>(null);
  const nextId = useRef(2);

  const replicate = useCallback(
    (id: number) => {
      if (mutatingId !== null) return;
      setBots((prev) => {
        const bot = prev.find((b) => b.id === id);
        if (!bot) return prev;
        if (prev.length >= max) {
          setDeniedId(id);
          window.setTimeout(() => setDeniedId(null), 350);
          return prev;
        }
        setMutatingId(id);
        window.setTimeout(() => {
          const nid = nextId.current++;
          setBots((p2) => {
            const i = p2.findIndex((b) => b.id === id);
            if (i < 0) return p2;
            const copy = [...p2];
            copy.splice(i + 1, 0, { id: nid, variant: bot.variant, born: true });
            return copy;
          });
          setMutatingId(null);
        }, 720);
        return prev;
      });
    },
    [mutatingId, max],
  );

  return (
    <div className="bot-crew-wrap">
      <div className="bot-crew" role="group" aria-label="Veto worker bots">
        {bots.map((b) => {
          const cls =
            'bot-unit' +
            (b.id === mutatingId ? ' is-mutating' : '') +
            (b.id === deniedId ? ' is-denied' : '') +
            (b.born ? ' is-born' : '');
          return (
            <span
              key={b.id}
              className={cls}
              role="button"
              tabIndex={0}
              title="Tap to replicate"
              aria-label={`${b.variant} bot — activate to replicate`}
              onClick={() => replicate(b.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  replicate(b.id);
                }
              }}
            >
              <span className="pxbot-stage">
                <PixelBot variant={b.variant} />
              </span>
            </span>
          );
        })}
      </div>
      <p className="bot-crew-caption" aria-live="polite">
        {'>'} veto crew · tap a bot to replicate · {bots.length}/{max}
        {bots.length >= max ? ' · crew at capacity' : ''}
      </p>
    </div>
  );
}
