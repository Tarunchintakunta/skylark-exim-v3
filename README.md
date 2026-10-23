# skylark-exim-v3

Cinematic story-scroll website for **Skylark Exim**, seafood exporter in Visakhapatnam, India.

The full spec lives in [`docs/`](docs/): start with `docs/PRD.md`, `docs/TRD.md`, `docs/STORY.md` and `docs/CONTENT.md`.
Workflow rules: `docs/GIT_WORKFLOW.md` (issues → branches → small PRs; only Tarun merges `main`).

## Develop
```bash
npm ci
npm run dev          # http://localhost:5173
npm run build && npm run preview   # production build on http://localhost:4173
npm run typecheck
npm test             # Playwright smoke tests (runs against vite preview)
npm run test:scroll  # scroll perf, writes perf-report.json (GPU=1 to use the real GPU locally)
npm run test:weight  # transferred MB, initial and full scroll, per path
npm run lh           # Lighthouse CI, mobile
```

## Environment variables (all optional)
The site builds and deploys with **no secrets**. The quote form posts to `api/rfq.ts`; without an email key it answers
`{ fallback: 'mailto' }` and the visitor's email app opens with the request pre-filled to info@skylarkexim.com.

| Variable | Purpose |
|---|---|
| `RESEND_API_KEY` | Send quote requests by email through Resend |
| `RFQ_FROM` | Sender address on a domain verified in Resend, e.g. `quotes@skylarkexim.com` |
| `RFQ_TO` | Recipient, default `info@skylarkexim.com` |

Copy `.env.example` to `.env.local` for local use (git-ignored). On Vercel: Project → Settings → Environment Variables.
