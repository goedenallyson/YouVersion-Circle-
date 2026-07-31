# YouVersion Circle — web app (React + Vite + TypeScript)

The production frontend for the **YouVersion Circle** group Scripture experience.
Talks only to the FastAPI backend; no API keys live in the client.

When the backend is not reachable, the app falls back to an in-browser **mock
engine** with deterministic passages and simulated peers — no credentials needed.

## Stack

- React 18 + TypeScript, built with Vite.
- Vitest + Testing Library for unit/interaction tests.
- No global state library needed; component state + a small API service layer.

## Project structure

```
web-app/
├─ index.html                     # Vite entry
├─ src/
│  ├─ main.tsx                     # React bootstrap
│  ├─ App.tsx                      # screen flow + engagement/live/mock/demo state
│  ├─ styles.css                   # design system (calm, Scripture-first)
│  ├─ api/
│  │  ├─ types.ts                  # shared response/request types (mirror backend)
│  │  ├─ live.ts                   # live service: calls our backend only
│  │  ├─ mock.ts                   # in-browser engine parity (offline)
│  │  └─ mock.test.ts              # API-parity tests (acceptance behaviors)
│  └─ components/
│     ├─ PassageHighlighter.tsx    # tap + drag highlight, keyboard/ARIA
│     ├─ PassageHighlighter.test.tsx
│     ├─ EmojiSelector.tsx         # curated approved emoji from /api/v1/circle/config
│     ├─ GroupPulseView.tsx        # named (non-anonymous) pulse + synthesis
│     └─ RecommendationPlanView.tsx# Demo-mode signal weighting + safeguards
└─ .env.example                    # frontend env (no secrets)
```

## Running (mock mode — no backend needed)

```bash
npm install
npm run dev
```

Open `http://localhost:5173`. If nothing is running on port 8099, the app detects
that the backend is unreachable and uses the mock engine automatically.

> **Gotcha:** If something is already listening on port 8099 (e.g. a stale backend
> process from a previous session), the app will try to use it as a live backend.
> If that process has outdated routes you'll get 404 errors. Fix by killing port
> 8099 first: `lsof -ti:8099 | xargs kill -9`

To **force** mock mode regardless of backend availability:

```bash
VITE_START_MOCK=1 npm run dev
```

## Running (live mode — backend required)

```bash
# 1) Start the backend (from repo root)
cd ../backend
source .venv/bin/activate
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8099

# 2) Start the frontend (this folder)
npm install
npm run dev    # http://localhost:5173
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8099` (see
`vite.config.ts`), so the browser only ever calls its own origin.

## Build / preview / deploy

```bash
npm run build      # tsc -b && vite build  ->  dist/
npm run preview    # serve the production build locally
```

`dist/` is a static bundle deployable to any static host (Netlify, Vercel,
GitHub Pages, S3/CloudFront, nginx). Because the client must not hold secrets,
deploy the FastAPI backend separately and route `/api` to it (reverse proxy or
`VITE_API_BASE=https://your-backend/api/v1` at build time).

## Tests

```bash
npm run test       # vitest: mock API parity + highlighter interactions
```

## Modes

- **Live vs Mock**: On startup the app health-checks the backend. If reachable,
  it uses live mode; otherwise mock mode. Users can also toggle manually in the
  UI via "Use live backend" / "Use mock" buttons.
- **Demo vs Product**: Demo shows AI reasoning, the recommendation plan (signal
  weighting + workflow + safeguards), and API callouts. Product hides internal
  reasoning — the intended end-user experience.

## Notes

- Scripture text is always retrieved from the backend (YouVersion/local corpus),
  never generated in the client.
- Group Pulse is **named**, not anonymous: it shows the group name and each mock
  member's response.
