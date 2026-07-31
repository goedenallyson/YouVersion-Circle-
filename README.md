# YouVersion Circle

A web demo for group scripture engagement powered by YouVersion and Gloo AI.

Users receive a daily passage, engage via a highlight and daily prompt, unlock their circle's pulse (group responses + AI synthesis), and see an adaptive recommendation for tomorrow's passage.

## Architecture

```
scripture-frontiers/
├── web-app/        # Vite + React frontend (dev server on port 5173)
├── shared/         # Shared TypeScript types, mock engine, engagement logic
├── backend/        # FastAPI backend (dev server on port 8099)
│   └── app/
│       ├── api/        # HTTP routes
│       ├── core/       # Config + dependency injection
│       ├── models/     # Pydantic schemas
│       ├── providers/  # YouVersion, Gloo AI, local bible
│       └── rag/        # Engine (verse selection, signals, recommendations)
└── data/           # Local scripture corpus + vector index (fallback)
```

## Prerequisites

- **Node.js** (v18+)
- **Python 3.10+** (only needed for live mode)

## Running the Demo (Mock Mode)

The web app includes a full in-browser mock engine with deterministic scripture passages, simulated peer responses, and AI synthesis. **No backend, API keys, or credentials are needed.** The app automatically uses mock mode when it cannot reach the backend.

> **Important:** Make sure nothing is already running on port 8099 before starting. If a stale backend process is running, the app will try to use it (and fail). Kill anything on that port first:
> ```bash
> lsof -ti:8099 | xargs kill -9  # macOS/Linux
> ```

```bash
cd web-app
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. You should see the full demo flow immediately.

You can also force mock mode regardless of backend availability:

```bash
VITE_START_MOCK=1 npm run dev
```

## Full Setup (Live Mode — Requires Your Own Credentials)

To pull real scripture content from YouVersion and generate live AI synthesis via Gloo, you need to run the backend with your own API credentials. The app does not ship with any keys.

**You will need:**

- **Gloo AI credentials** — register at Gloo AI Studio to get a client ID and secret
- **YouVersion API key** — apply for a YouVersion platform app key

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env` with your credentials:

```env
GLOO_CLIENT_ID=your-gloo-client-id
GLOO_CLIENT_SECRET=your-gloo-client-secret
BIBLE_PROVIDER=youversion
BIBLE_API_KEY=your-youversion-app-key
BIBLE_BASE_URL=https://api.youversion.com/v1
BIBLE_DEFAULT_TRANSLATION=3034
```

Start the backend:

```bash
source .venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8099
```

Verify it's running: `curl http://127.0.0.1:8099/api/v1/health` should return `{"status":"ok","gloo_configured":true,"bible_provider":"youversion",...}`

### 2. Web App

```bash
cd web-app
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. The app will detect the backend and switch to live mode automatically.

## How It Works

1. **Read + Engage** — A verse arrives (from YouVersion in live mode, or the local corpus in mock mode). The user highlights a phrase and completes a daily prompt (emotion tap, short reflection, or one word).
2. **Group Pulse** — Once engaged, the circle's responses are revealed with an AI synthesis of shared needs and ways to support each other (powered by Gloo AI in live mode, deterministic in mock mode).
3. **Tomorrow** — An adaptive passage recommendation based on the group's engagement signals, with transparent workflow/signals/safeguards.

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| "Could not load today's passage: HTTP 404" | A stale backend is running with old routes | Kill port 8099: `lsof -ti:8099 \| xargs kill -9` then reload |
| App shows "Mock mode" when you want live | Backend isn't running or isn't reachable on port 8099 | Start the backend (see Full Setup above) |
| "Could not load today's passage: Failed to fetch" | Nothing on port 8099, mock mode should kick in | Hard refresh the browser (Cmd+Shift+R) |
| Backend starts but `gloo_configured: false` | Missing or invalid Gloo credentials in `.env` | Double-check `GLOO_CLIENT_ID` and `GLOO_CLIENT_SECRET` |

## Key Configuration

| Variable | Description |
|----------|-------------|
| `GLOO_CLIENT_ID` | Gloo AI Studio OAuth client ID |
| `GLOO_CLIENT_SECRET` | Gloo AI Studio OAuth client secret |
| `BIBLE_PROVIDER` | `youversion` (live) or `local` (offline fallback) |
| `BIBLE_API_KEY` | YouVersion platform app key |
| `BIBLE_BASE_URL` | YouVersion API base URL |
| `BIBLE_DEFAULT_TRANSLATION` | Bible version ID (e.g., `3034` for BSB) |
| `VITE_START_MOCK` | Set to `1` to force mock mode in the frontend |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Backend health check |
| GET | `/api/v1/circle/verse-of-day` | Today's verse for the group |
| POST | `/api/v1/circle/signal` | Submit engagement (highlight, reaction, word, reflection) |
| GET | `/api/v1/circle/pulse` | Group pulse (locked until user engages) |
| GET | `/api/v1/circle/tomorrow` | Adaptive recommendation for tomorrow |
| GET | `/api/v1/circle/config` | Group config (name, approved emoji) |
| GET | `/api/v1/circle/members` | Demo member list |
| POST | `/api/v1/circle/synthesize` | Standalone Gloo AI synthesis |

## Development

```bash
# Type check the web app
cd web-app && npx tsc --noEmit

# Production build
cd web-app && npm run build

# Run tests
cd web-app && npm run test
```

## Security

- Never commit `.env` — it contains API secrets
- The frontend never holds API keys — all credentialed calls go through the backend
- Scripture text comes only from YouVersion/local corpus, never AI-generated
