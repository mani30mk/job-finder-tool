# Job Hunter — Integration Guide

## What was changed

### Frontend (`lib/api.ts`) — fully rewritten
- **Response transformer**: backend returns `snake_case` (job_id, apply_url, match_score…),
  frontend types expect `camelCase` (id, link, matchScore…). `transformJob()` handles all of this.
- **`/recommendations/default`**: new no-auth endpoint — no user_id, no resume upload needed.
- **API URL override**: Settings screen saves URL to `localStorage`; `api.ts` picks it up at runtime
  so you can change the server without rebuilding.
- **Graceful fallback**: if `/api/v1/stats` fails, stats are derived from recommendations + new jobs.
- **Mock data fallback**: if `NEXT_PUBLIC_API_URL` is not set, mock data is used automatically.

### Frontend (`ProfileScreen.tsx`) — updated
- Your actual name, skills, university pre-filled as defaults.
- **Test Connection** button pings the server and shows latency.
- API URL field saves to `localStorage` immediately — api.ts reads it on next call.

### Backend (`api/main.py`) — two endpoints added at the bottom
- `GET /api/v1/recommendations/default` — uses hardcoded profile, no session needed.
- `GET /api/v1/jobs/new` — returns jobs scraped in last N hours.

---

## Setup

### 1. Update your backend

Replace `api/main.py` with the provided file (or just append the new endpoints to yours).

### 2. Configure the frontend

Create `.env.local` in the frontend root:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

When accessing from your phone on the same WiFi:
```
NEXT_PUBLIC_API_URL=http://192.168.1.x:8000
```
(Replace with your PC's local IP — run `ipconfig` on Windows or `ip addr` on Linux)

### 3. Start everything

**Backend (terminal 1):**
```bash
cd job-hunter
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

`--host 0.0.0.0` is required so your phone can reach it on the local network.

**Frontend (terminal 2):**
```bash
cd frontend-integrated
pnpm install
pnpm dev
```

Open `http://localhost:3000` in browser, or `http://192.168.1.x:3000` on your phone.

---

## Verify it works

1. Open Settings → enter your API URL → tap **Test** → should show ✅ Connected
2. Open Jobs Feed → jobs should load (not mock data)
3. Open Dashboard → stats should reflect your actual DB counts

## Data flow reminder

```
Phone browser
  → GET /api/v1/recommendations/default   (no login, no upload)
  → FastAPI reads DEFAULT_PROFILE from memory
  → RecommendationEngine queries SQLite WHERE is_active = 1
  → returns ranked jobs
  → api.ts transforms snake_case → camelCase
  → JobCard renders
```
