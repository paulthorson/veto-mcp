/* Shared pixel-brand primitives for all site pages. */
import { useCallback, useRef, useState } from 'react';

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

/* ------------------------------------------------------------------ */
/* Pixel bots — hand-drawn animated worker sprites.                    */
/* Each bot is a 24x16 scene (bot + prop) with 3 work frames rendered  */
/* as one SVG strip; CSS steps() cycles the frames like a sprite.     */
/* Tap/click a bot and it mutates, then splits into two.              */
/* ------------------------------------------------------------------ */

export type BotVariant = 'miner' | 'builder';

const BOT_W = 24;
const BOT_H = 16;
const BOT_FRAMES = 3;

const BOT_PALETTE: Record<string, string> = {
  K: '#0d0d12',
  W: '#f4f4f5',
  R: '#ff4d5e',
  G: '#34d399',
  A: '#fbbf24',
  S: '#a1a1aa',
  B: '#c08a4d',
  D: '#3a3a44',
  L: '#71717a',
};

const BOT_BODY: string[] = [
  '........................',
  '.....RR.................',
  '.....DD.................',
  '...DDDDDD...............',
  '..DSSSSSSD..............',
  '..DSGGSSGD..............',
  '..DSGGSSGD..............',
  '..DSSSSSSD..............',
  '...DSSSSSD..............',
  '..DSSSSSSSDD............',
  '..DSSASSDSDD............',
  '..DSSSSSSSDD............',
  '...DSSSSSDD.............',
  '...DDS.DDSD.............',
  '...DDS.DDSD.............',
  '..DDSSD.DDSSD...........',
];

type Bpx = [number, number, string]; // x, y, palette key

function botPropRock(): Bpx[] {
  const px: Bpx[] = [];
  for (let x = 18; x < 22; x++) px.push([x, 11, 'L']);
  for (let y = 12; y < 16; y++)
    for (let x = 17; x < 23; x++) px.push([x, y, 'D']);
  px.push([19, 13, 'L'], [21, 14, 'L'], [18, 15, 'L'], [17, 12, 'S'], [22, 13, 'S']);
  return px;
}

function botPropBlocks(): Bpx[] {
  const px: Bpx[] = [];
  for (let x = 17; x < 23; x++) px.push([x, 13, 'D']);
  for (const y of [14, 15]) {
    px.push([17, y, 'D']);
    for (let x = 18; x < 22; x++) px.push([x, y, 'S']);
    px.push([22, y, 'D']);
  }
  for (let x = 18; x < 22; x++) px.push([x, 10, 'D']);
  for (const y of [11, 12]) {
    px.push([18, y, 'D']);
    for (let x = 19; x < 21; x++) px.push([x, y, 'S']);
    px.push([21, y, 'D']);
  }
  px.push([19, 14, 'W'], [20, 11, 'W']);
  return px;
}

/* Tool poses per frame: handle pixels + head pixels + strike sparks. */
const BOT_TOOLS: Record<BotVariant, { prop: () => Bpx[]; tools: Bpx[][] }> = {
  miner: {
    prop: botPropRock,
    tools: [
      [[10,9,'B'],[11,8,'B'],[12,7,'B'],[13,6,'B'],[14,5,'B'],[15,4,'B'],
       [13,2,'W'],[14,2,'W'],[15,2,'W'],[16,2,'W'],[16,3,'W'],[13,3,'W']],
      [[10,9,'B'],[11,9,'B'],[12,8,'B'],[13,8,'B'],[14,7,'B'],
       [13,6,'W'],[14,6,'W'],[15,6,'W'],[15,7,'W']],
      [[10,9,'B'],[12,9,'B'],[13,10,'B'],[14,10,'B'],
       [15,9,'W'],[16,9,'W'],[15,10,'W'],[16,10,'W'],
       [17,8,'W'],[18,9,'A'],[17,10,'W'],[19,8,'A']],
    ],
  },
  builder: {
    prop: botPropBlocks,
    tools: [
      [[10,9,'B'],[11,8,'B'],[12,7,'B'],[13,6,'B'],[14,5,'B'],[14,4,'B'],
       [12,3,'W'],[13,3,'W'],[14,3,'W'],[15,3,'W'],[15,4,'W'],[12,4,'W']],
      [[10,9,'B'],[11,9,'B'],[12,8,'B'],[13,8,'B'],
       [12,7,'W'],[13,7,'W'],[14,7,'W'],[14,8,'W']],
      [[10,9,'B'],[12,9,'B'],[14,10,'B'],[16,10,'B'],
       [16,9,'W'],[17,9,'W'],[16,10,'W'],[17,10,'W'],
       [18,8,'W'],[19,9,'A'],[18,9,'W']],
    ],
  },
};

function composeBotFrame(variant: BotVariant, frame: number): string[] {
  const g = BOT_BODY.map((r) => r.split(''));
  const spec = BOT_TOOLS[variant];
  for (const [x, y, c] of [...spec.prop(), ...spec.tools[frame]]) {
    if (y >= 0 && y < BOT_H && x >= 0 && x < BOT_W) g[y][x] = c;
  }
  return g.map((r) => r.join(''));
}

const BOT_FRAME_CACHE: Record<BotVariant, string[][]> = {
  miner: [0, 1, 2].map((f) => composeBotFrame('miner', f)),
  builder: [0, 1, 2].map((f) => composeBotFrame('builder', f)),
};

export function PixelBot({
  variant,
  px = 3,
  label,
}: {
  variant: BotVariant;
  px?: number;
  label?: string;
}) {
  const frames = BOT_FRAME_CACHE[variant];
  const rects: React.ReactNode[] = [];
  frames.forEach((rows, f) => {
    rows.forEach((row, y) => {
      for (let x = 0; x < row.length; x++) {
        const c = row[x];
        if (c === '.') continue;
        rects.push(
          <rect
            key={`${f}-${x}-${y}`}
            x={f * BOT_W + x}
            y={y}
            width={1.02}
            height={1.02}
            fill={BOT_PALETTE[c] ?? '#ffffff'}
          />,
        );
      }
    });
  });
  return (
    <svg
      className="bot-strip"
      width={BOT_W * BOT_FRAMES * px}
      height={BOT_H * px}
      viewBox={`0 0 ${BOT_W * BOT_FRAMES} ${BOT_H}`}
      shapeRendering="crispEdges"
      role="img"
      aria-label={label ?? `${variant} bot`}
      style={{ '--bot-fw': `${BOT_W * px}px` } as React.CSSProperties}
    >
      {rects}
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
              <span className="bot-scene" style={{ width: BOT_W * 3, height: BOT_H * 3 }}>
                <PixelBot variant={b.variant} px={3} />
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
