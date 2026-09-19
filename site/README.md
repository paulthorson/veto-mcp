# Veto marketing site

Sources for **https://www.vetomcp.com/** — the public marketing and docs
surface for Veto MCP. Root directory of this repository is the MCP server;
this folder is the static site deployed from `site/`.

## Build

Design-system CSS is vendored at `src/vendor/tokens.css` and
`src/vendor/veto-web.css` (see `src/vendor/README`) and imported from
`src/main.tsx`. The site builds from a plain clone:

```bash
npm install
npm run build   # tsc -b && vite build → dist/
```

- `npm run dev` — local dev server with hot reload
- `npm run preview` — preview the production build in `dist/`
- `npm run lint` — oxlint

## Measured live surface

As of the go-live scrub:

| Check | Expected |
|---|---|
| `https://www.vetomcp.com/` | HTTP 200 |
| `https://vetomcp.com/` | HTTP 308 → `https://www.vetomcp.com/` |
| Canonical / OG URL | `https://www.vetomcp.com/` |
| Contact (privacy / disclaimer) | `hello@vetomcp.com` |
| Boards named on the homepage | Greenhouse, Lever, Ashby, Adzuna |

Do not reintroduce removed scrapers (LinkedIn, Indeed, ZipRecruiter) or
legacy preview hostnames in visitor-facing copy.
