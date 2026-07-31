# YouVersion Circle — web app (React + Vite + TypeScript)

The runnable, editable production frontend for the **YouVersion Circle**
group Scripture experience. Talks only to the FastAPI backend; no API keys
live in the client. Runs fully offline in **mock mode** when no backend is
reachable, so demos/CI never break.

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

## Local development

```bash
# 1) Start the backend (repo root)
cd ../backend && python3 -m pip install -r requirements.txt
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8099

# 2) Start the frontend (this folder)
cp .env.example .env         # optional; defaults are fine
npm install
npm run dev                  # http://localhost:5173
```

The dev server proxies `/api` → `http://127.0.0.1:8099` (see `vite.config.ts`
and `VITE_PROXY_TARGET`), so the browser only ever calls the app's own origin.
If the backend is down, the app automatically falls back to mock mode.

Set `VITE_START_MOCK=1` to force offline mock mode.

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

- **Live vs Mock**: "Use live backend" health-checks the base URL and switches;
  "Use mock" returns to offline mode. Startup auto-detects.
- **Demo vs Product**: Demo shows AI reasoning, the recommendation plan (signal
  weighting + workflow + safeguards), and API callouts. Product hides internal
  reasoning and the tomorrow preview — the intended end-user experience.

## Notes

- Scripture text is always retrieved from the backend (YouVersion/local corpus),
  never generated in the client.
- Group Pulse is **named**, not anonymous: it shows the group name and each mock
  member's response.
- The legacy single-file demo at `../web/index.html` is kept as a zero-setup
  backup; this app is the canonical deliverable.
