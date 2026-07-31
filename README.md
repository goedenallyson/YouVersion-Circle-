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

## Setup (Requires Your Own Credentials)

To connect to YouVersion and Gloo AI for real data, you must supply your own API credentials. The app does not ship with any keys — you need to obtain them yourself:

- **Gloo AI credentials** — register at Gloo AI Studio to get a client ID and secret
- **YouVersion API key** — apply for a YouVersion platform app key
- **Node.js** (v18+) — for the web frontend
- **Python 3.10+** — for the backend

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

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

Verify: `curl http://127.0.0.1:8099/api/v1/health` should return `{"status":"ok","gloo_configured":true,"bible_provider":"youversion",...}`

### 2. Web App

```bash
cd web-app
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

The Vite dev server proxies `/api` requests to the backend at `http://127.0.0.1:8099`. On startup, the app checks if the backend is reachable — if so, it uses the live API; otherwise it falls back to the mock engine.

## How It Works

1. **Read + Engage** — A verse arrives from YouVersion. The user highlights a phrase and completes a daily prompt (emotion tap, short reflection, or one word).
2. **Group Pulse** — Once engaged, the circle's responses are revealed with an AI synthesis of shared needs and ways to support each other (powered by Gloo AI).
3. **Tomorrow** — An adaptive passage recommendation based on the group's engagement signals, with transparent workflow/signals/safeguards.

## Key Configuration

| Variable | Description |
|----------|-------------|
| `GLOO_CLIENT_ID` | Gloo AI Studio OAuth client ID |
| `GLOO_CLIENT_SECRET` | Gloo AI Studio OAuth client secret |
| `BIBLE_PROVIDER` | `youversion` (live) or `local` (offline fallback) |
| `BIBLE_API_KEY` | YouVersion platform app key |
| `BIBLE_BASE_URL` | YouVersion API base URL |
| `BIBLE_DEFAULT_TRANSLATION` | Bible version ID (e.g., `3034` for BSB) |

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
```

## Security

- Never commit `.env` — it contains API secrets
- The frontend never holds API keys — all credentialed calls go through the backend
- Scripture text comes only from YouVersion/local corpus, never AI-generated
