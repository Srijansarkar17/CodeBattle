# CodeBattle — Complete Project Documentation

## What Is CodeBattle?

CodeBattle is a **real-time 1v1 coding battle platform** where developers compete against each other by solving Data Structures & Algorithms (DSA) problems. Think of it as a chess.com, but for coding! Two players are matched based on their rating, given the same problem, and the first one to solve it wins the round and gains rating points.

---

## Project Architecture Overview

```
codebattle/
├── frontend/               ← Next.js 15 app (what users see in their browser)
├── backend/                ← FastAPI Python server (the brain of the app)
├── docker/                 ← Database configuration files
├── docs/                   ← You are here 📖
├── scripts/                ← Helper scripts (setup, dev start)
└── docker-compose.yml      ← Orchestrates all services together
```

Think of the architecture as **4 services talking to each other**:

```
[Browser] ←→ [Next.js :3000] ←→ [FastAPI :8000] ←→ [PostgreSQL :5432]
                                        ↕
                                  [Redis :6379]
```

---

## Technology Choices — Why We Picked Each Tool

| Tool | Purpose | Why |
|------|---------|-----|
| **Next.js 15** | Frontend framework | App Router, TypeScript, fast rendering |
| **TailwindCSS** | Styling | Utility-first, fast to prototype |
| **FastAPI** | Backend API | Fast, Python, automatic docs at `/api/docs` |
| **PostgreSQL** | Database | Relational DB for users, matches, history |
| **Redis** | Cache + Queue | Lightning-fast in-memory store for real-time features |
| **WebSockets** | Real-time | Push instant match notifications without polling |
| **Docker** | Containerization | "Works on my machine" problem = solved |
| **JWT** | Authentication | Stateless auth tokens, industry standard |
| **SQLAlchemy** | ORM | Write Python objects, not raw SQL |
| **Pydantic** | Validation | Auto-validates all API input/output shapes |
| **bcrypt** | Password hashing | Industry standard — passwords are NEVER stored plain |

---

## Backend — Deep Dive

### Folder Structure

```
backend/
├── app/
│   ├── main.py              ← App entry point, startup/shutdown hooks
│   ├── core/
│   │   ├── config.py        ← All env variables in one place (Pydantic Settings)
│   │   ├── database.py      ← PostgreSQL async connection + session
│   │   ├── redis.py         ← Redis connection + online users + matchmaking queue
│   │   └── security.py      ← bcrypt hashing + JWT create/verify + auth dependency
│   ├── models/              ← SQLAlchemy ORM table definitions
│   │   ├── user.py          ← users table
│   │   ├── match.py         ← matches table (1v1 battles)
│   │   ├── problem.py       ← problems table (DSA questions)
│   │   ├── submission.py    ← submissions table (code attempts)
│   │   ├── rating.py        ← ratings history table
│   │   └── contest.py       ← contests table (tournaments)
│   ├── schemas/             ← Pydantic request/response validation
│   │   ├── auth.py          ← RegisterRequest, LoginRequest, TokenResponse
│   │   └── user.py          ← UserPublicProfile, UserPrivateProfile
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py  ← Aggregates all routers
│   │       ├── health.py    ← GET /health, GET /health/full
│   │       ├── auth.py      ← POST /auth/register, /auth/login, /auth/refresh
│   │       ├── users.py     ← GET /users/me, /users/{username}, /users/leaderboard
│   │       └── matchmaking.py ← POST /matchmaking/join, /matchmaking/leave
│   ├── services/
│   │   └── matchmaking.py   ← Matchmaking business logic (rating-based pairing)
│   └── websockets/
│       ├── manager.py       ← Tracks all active WS connections
│       └── endpoint.py      ← WS handler at /api/v1/ws/battle?token=...
├── requirements.txt
├── Dockerfile
└── .env.example
```

### How Authentication Works

1. User sends `POST /api/v1/auth/register` with `{username, email, password}`
2. Backend hashes the password with **bcrypt** (irreversible)
3. Creates the user in PostgreSQL with rating=1200
4. Returns two JWT tokens:
   - **Access Token** (expires in 30 min) — used for every API request
   - **Refresh Token** (expires in 7 days) — used to get a new Access Token
5. Frontend stores both in `localStorage`
6. Every subsequent request includes `Authorization: Bearer <access_token>`

> **Why two tokens?** Access tokens are short-lived for security. If stolen, they expire in 30 minutes. Refresh tokens allow seamless re-authentication without re-entering password.

### Database Models Explained

**User** — The most important model:
```python
id | username | email | hashed_password | rating | is_active | created_at | updated_at
```

**Match** — A 1v1 battle record:
```
id | player1_id | player2_id | problem_id | winner_id | status | started_at | ended_at
```
Status goes: `pending → active → completed` (or `cancelled`)

**Problem** — A DSA question:
```
id | title | slug | description | difficulty | tags | examples | starter_code
```

**Submission** — Every time a player submits code:
```
id | user_id | match_id | language | code | status | runtime_ms | memory_kb
```
Status: `pending → running → accepted / wrong_answer / time_limit / etc.`

**Rating** — History of ELO changes:
```
id | user_id | match_id | old_rating | new_rating | delta
```

**Contest** — Tournaments (Phase 2):
```
id | title | status | start_time | end_time | problem_ids
```

### How the Matchmaking Queue Works

The matchmaking queue uses a **Redis Sorted Set** — a clever data structure:

```
Key: "matchmaking_queue"
Members: JSON string with {user_id, rating}
Score: The player's rating (number)
```

Why a sorted set? Because Redis can instantly find all players with a rating **between X and Y** using `ZRANGEBYSCORE`. This makes finding opponents within ±100 rating O(log N) — extremely fast!

**Flow when a player clicks "Find Match":**
1. Call `POST /api/v1/matchmaking/join`
2. Service checks if anyone in the queue has a rating between `my_rating - 100` and `my_rating + 100`
3. **If found:** Remove them from queue, create a match, notify both via WebSocket
4. **If not found:** Add yourself to the queue, return "searching"
5. Client waits for WebSocket `match_found` event

---

## Frontend — Deep Dive

### Folder Structure

```
frontend/
└── src/
    ├── app/                        ← Next.js App Router pages
    │   ├── layout.tsx              ← Root HTML wrapper (SEO metadata, fonts)
    │   ├── page.tsx                ← Landing page (/)
    │   ├── globals.css             ← Design system (CSS variables, animations)
    │   ├── (auth)/                 ← Route group: login + register (no shared layout conflict)
    │   │   ├── layout.tsx          ← Wraps auth pages with AuthProvider
    │   │   ├── login/page.tsx      ← Login form (/login)
    │   │   └── register/page.tsx   ← Register form (/register)
    │   ├── (dashboard)/            ← Protected pages (require login)
    │   │   ├── layout.tsx          ← Auth guard + Navbar
    │   │   ├── dashboard/page.tsx  ← User dashboard (/dashboard)
    │   │   └── matchmaking/page.tsx ← Battle lobby (/matchmaking)
    │   └── leaderboard/page.tsx    ← Public leaderboard (/leaderboard)
    ├── components/
    │   └── Navbar.tsx              ← Responsive navigation bar
    ├── context/
    │   └── AuthContext.tsx         ← Global auth state (user, token, login, logout)
    └── lib/
        ├── api.ts                  ← All HTTP calls to the backend
        └── websocket.ts            ← WebSocket client with reconnection + heartbeat
```

### Route Groups Explained

Next.js **Route Groups** (folders in parentheses like `(auth)`) let you group pages without affecting the URL. For example:
- `(auth)/login/page.tsx` → URL is `/login` (not `/auth/login`)
- This lets `(auth)` and `(dashboard)` have different layouts without conflicting

### Authentication Flow (Frontend)

```
User visits /login
     ↓
Submits email + password
     ↓
AuthContext.login() calls apiService.login()
     ↓
Backend returns {access_token, refresh_token}
     ↓
Tokens stored in localStorage
     ↓
AuthContext fetches user profile from /users/me
     ↓
Router.push("/dashboard")
     ↓
Dashboard renders with user data
```

On **every page load**, the AuthContext checks localStorage for a token and re-fetches the user profile — this is how the session "survives" a page refresh.

### WebSocket Client

The `WsService` class (`src/lib/websocket.ts`) provides:
- **Auto-reconnect** — If connection drops, retries after 3 seconds
- **Heartbeat** — Sends a ping every 25 seconds so the server knows we're alive
- **Event system** — Subscribe to events like `match_found` with `ws.on("match_found", handler)`

Usage example:
```typescript
const ws = new WsService(accessToken);
ws.on("match_found", (data) => {
  console.log(`Battle starting! Match ID: ${data.match_id}`);
  router.push(`/battle/${data.match_id}`);
});
ws.connect();
```

---

## Docker — How All Services Connect

The `docker-compose.yml` starts 4 containers on a shared private network:

```
┌─────────────────────────────────────────────────────┐
│                 codebattle_network                   │
│                                                      │
│  [postgres:5432] ←→ [redis:6379]                    │
│         ↑                ↑                           │
│  [backend:8000]  ←←←←←←←┘                           │
│         ↑                                            │
│  [frontend:3000]                                     │
└─────────────────────────────────────────────────────┘
```

Inside Docker, services reach each other by **service name** (not localhost). That's why the backend's `DATABASE_URL` uses `@postgres:5432` and `REDIS_URL` uses `redis://redis:6379`.

**Health Checks** ensure services start in the right order:
- PostgreSQL must be healthy before backend starts
- Redis must be healthy before backend starts
- Backend must be up before frontend is considered ready

---

## API Endpoints Reference

### Health Check

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/health/` | No | Simple liveness check |
| GET | `/api/v1/health/full` | No | DB + Redis health check |

### Authentication

| Method | Path | Auth | Body | Description |
|--------|------|------|------|-------------|
| POST | `/api/v1/auth/register` | No | `{username, email, password}` | Create account |
| POST | `/api/v1/auth/login` | No | `{email, password}` | Get JWT tokens |
| POST | `/api/v1/auth/refresh` | No | `?refresh_token_str=...` | Refresh access token |

### Users

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/users/me` | ✅ | Get your private profile |
| PATCH | `/api/v1/users/me` | ✅ | Update username/email |
| GET | `/api/v1/users/leaderboard` | No | Top players by rating |
| GET | `/api/v1/users/{username}` | No | Get public profile |

### Matchmaking

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/matchmaking/join` | ✅ | Join queue / find match |
| POST | `/api/v1/matchmaking/leave` | ✅ | Leave the queue |
| GET | `/api/v1/matchmaking/queue-size` | No | Players in queue |
| GET | `/api/v1/matchmaking/status` | ✅ | Are you in queue? |

### WebSocket

| Protocol | Path | Auth | Description |
|----------|------|------|-------------|
| WS | `/api/v1/ws/battle?token=<JWT>` | ✅ (query param) | Real-time battle connection |

**WebSocket Events (Server → Client):**
- `connected` — You successfully connected
- `match_found` — An opponent was found! Includes `match_id` and `opponent_id`
- `pong` — Response to your ping
- `error` — Something went wrong

**WebSocket Events (Client → Server):**
- `ping` — Heartbeat
- `matchmaking_join` — Join queue via WS
- `matchmaking_leave` — Leave queue via WS
- `chat` — Send a message (broadcast to all)

---

## Installation & Setup

### Prerequisites
- Node.js 20+
- Python 3.12+
- Docker Desktop
- Git

### Option A: Docker (Recommended)

```bash
# 1. Clone the project
git clone <your-repo-url>
cd CodeBattle

# 2. Setup environment files
./scripts/setup.sh

# 3. Edit backend secret key (IMPORTANT!)
nano backend/.env
# Change SECRET_KEY to a strong random string (32+ chars)

# 4. Start everything
docker compose up --build

# 5. Open your browser
open http://localhost:3000
```

### Option B: Local Development (No Docker)

You'll need PostgreSQL and Redis running locally first.

```bash
# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your local DB/Redis URLs
uvicorn app.main:app --reload

# Frontend (in a new terminal)
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

---

## Docker Commands Cheat Sheet

```bash
# Start all services
docker compose up

# Start in background
docker compose up -d

# Start fresh (rebuild images)
docker compose up --build

# Stop everything
docker compose down

# Stop and delete all data (⚠️ wipes database!)
docker compose down -v

# View logs
docker compose logs -f

# View just backend logs
docker compose logs -f backend

# Shell into backend container
docker compose exec backend bash

# Run a DB migration check
docker compose exec backend python -c "from app.core.database import engine; print('DB OK')"
```

---

## Environment Variables Reference

### Backend (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | ⚠️ Change me! | JWT signing key (32+ chars) |
| `DATABASE_URL` | postgres://... | PostgreSQL connection string |
| `REDIS_URL` | redis://... | Redis connection string |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | JWT access token lifetime |
| `MATCHMAKING_RATING_RANGE` | 100 | ±N rating for opponent search |
| `DEBUG` | False | Enable SQL logging |
| `CORS_ORIGINS` | localhost:3000 | Allowed frontend origins |

### Frontend (.env.local)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | http://localhost:8000 | Backend HTTP URL |
| `NEXT_PUBLIC_WS_URL` | ws://localhost:8000 | Backend WebSocket URL |

---

## Phase 1 vs Phase 2 Roadmap

### ✅ Phase 1 (This MVP — Completed)
- User registration & login (JWT)
- Dashboard with rating display
- Matchmaking queue (Redis sorted set)
- WebSocket real-time notifications
- Leaderboard
- Docker deployment
- All database models defined

### 🚀 Phase 2 (Next Steps)
- Code editor integration (Monaco Editor)
- Code execution engine (judge system)
- Live opponent code viewing
- Match history page
- ELO rating calculation after each match
- Contest/tournament system
- Profile pages
- Social features (friends, challenges)

---

## Common Issues & Fixes

**Backend can't connect to PostgreSQL:**
```bash
# Make sure postgres is healthy first
docker compose ps
# If postgres is not healthy, check its logs:
docker compose logs postgres
```

**JWT token expired:**
- Access tokens expire after 30 minutes
- Call `POST /api/v1/auth/refresh` with your refresh token
- Or simply log in again

**WebSocket connection fails:**
- Make sure you pass a valid `?token=` query parameter
- Token must be a valid, non-expired JWT
- Browser dev tools → Network → WS tab to debug

**Frontend can't reach backend:**
- Check `NEXT_PUBLIC_API_URL` in `frontend/.env.local`
- In Docker, the frontend should use `http://backend:8000` (service name)
- Outside Docker (local dev), use `http://localhost:8000`

---

## Auto-Generated API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/api/docs
  - Try every endpoint directly from your browser!
  - Authenticate with your JWT token using the 🔒 button
  
- **ReDoc**: http://localhost:8000/api/redoc
  - Clean, readable reference documentation

---

*Built with ❤️ for competitive coders. CodeBattle — where algorithms meet adrenaline.*
