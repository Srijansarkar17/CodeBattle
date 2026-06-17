# CodeBattle — Detailed Project Walkthrough

## What Is CodeBattle?

**CodeBattle** is a real-time 1v1 coding battle platform — think chess.com, but for competitive programming. Two players are matched by rating, given the same DSA problem, and the **first one to solve it wins** and earns rating points.

> [!NOTE]
> The project is currently at **Phase 1 (MVP)** — auth, matchmaking, leaderboard, and WebSocket infrastructure are complete. Phase 2 (code editor, judge system, ELO calculation) is next.

---

## 1. High-Level Architecture

```
[Browser]
   │  HTTP / WebSocket
   ▼
[Next.js :3000]          ← Frontend (UI + routing + state)
   │  REST API calls
   ▼
[FastAPI :8000]          ← Backend (business logic, auth, matchmaking)
   │              │
   ▼              ▼
[PostgreSQL :5432]   [Redis :6379]
  (persistent DB)     (real-time queue + online users)
```

All four services run in Docker containers on a shared `codebattle_network` bridge. The containers communicate by **service name**, not `localhost`.

---

## 2. Technology Stack

| Layer | Technology | Reason |
|---|---|---|
| Frontend | **Next.js 15** (App Router) | TypeScript, SSR, file-system routing |
| Styling | **TailwindCSS + Custom CSS** | Utility classes + design token system |
| Backend | **FastAPI** | Async Python, auto Swagger docs |
| ORM | **SQLAlchemy 2 (async)** | Python-native DB abstraction |
| Database | **PostgreSQL 16** | Relational data: users, matches, problems |
| Cache/Queue | **Redis 7** | Matchmaking sorted set + online user tracking |
| Real-time | **WebSockets** (native FastAPI) | Push match notifications without polling |
| Auth | **JWT** (HS256) + **bcrypt** | Stateless tokens, secure password hashing |
| Validation | **Pydantic v2** | Request/response schema validation |
| Config | **pydantic-settings** | Env-var driven configuration |
| Container | **Docker + Docker Compose** | Reproducible multi-service orchestration |

---

## 3. Repository Layout

```
CodeBattle/
├── backend/                  ← Python/FastAPI application
│   ├── app/
│   │   ├── main.py           ← App factory + startup/shutdown lifecycle
│   │   ├── core/             ← Shared infrastructure modules
│   │   │   ├── config.py     ← Pydantic Settings (all env vars)
│   │   │   ├── database.py   ← Async SQLAlchemy engine + session
│   │   │   ├── redis.py      ← Redis manager (online users + queue)
│   │   │   └── security.py   ← bcrypt + JWT + FastAPI auth dependency
│   │   ├── models/           ← SQLAlchemy ORM table definitions
│   │   │   ├── user.py       ← users table
│   │   │   ├── match.py      ← matches table (1v1 battles)
│   │   │   ├── problem.py    ← problems table (DSA questions)
│   │   │   ├── submission.py ← submissions table (code attempts)
│   │   │   ├── rating.py     ← rating history table (ELO changes)
│   │   │   └── contest.py    ← contests table (future tournaments)
│   │   ├── schemas/          ← Pydantic I/O contracts
│   │   │   ├── auth.py       ← RegisterRequest, LoginRequest, TokenResponse
│   │   │   └── user.py       ← UserPublicProfile, UserPrivateProfile
│   │   ├── api/v1/           ← HTTP REST route handlers
│   │   │   ├── __init__.py   ← Root v1 router aggregating all sub-routers
│   │   │   ├── health.py     ← /health, /health/full
│   │   │   ├── auth.py       ← /auth/register, /auth/login, /auth/refresh
│   │   │   ├── users.py      ← /users/me, /users/{username}, /users/leaderboard
│   │   │   └── matchmaking.py← /matchmaking/join, /matchmaking/leave, /matchmaking/status
│   │   ├── services/
│   │   │   └── matchmaking.py← Rating-based pairing business logic
│   │   └── websockets/
│   │       ├── manager.py    ← In-memory WS connection registry
│   │       └── endpoint.py   ← WS handler at /api/v1/ws/battle?token=...
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env / .env.example
│
├── frontend/                 ← Next.js 15 application
│   └── src/
│       ├── app/              ← App Router pages (file-system routing)
│       │   ├── layout.tsx    ← Root HTML shell (fonts, metadata, AuthProvider)
│       │   ├── page.tsx      ← Landing/marketing page (/)
│       │   ├── globals.css   ← Design system (CSS variables, animations)
│       │   ├── (auth)/       ← Route group: login + register pages
│       │   │   ├── layout.tsx
│       │   │   ├── login/page.tsx
│       │   │   └── register/page.tsx
│       │   ├── (dashboard)/  ← Protected pages (auth guard in layout)
│       │   │   ├── layout.tsx← Auth guard + Navbar injection
│       │   │   ├── dashboard/page.tsx
│       │   │   └── matchmaking/page.tsx
│       │   └── leaderboard/page.tsx ← Public leaderboard
│       ├── components/
│       │   └── Navbar.tsx    ← Responsive nav bar with auth-aware links
│       ├── context/
│       │   └── AuthContext.tsx← React Context for global auth state
│       └── lib/
│           ├── api.ts        ← Typed HTTP client (all backend calls)
│           └── websocket.ts  ← WS client with reconnect + heartbeat
│
├── docker/
│   └── postgres/
│       └── init.sql          ← DB initialization SQL (run on first boot)
│
├── docs/
│   └── README.md             ← Complete project documentation
│
├── scripts/
│   ├── setup.sh              ← One-time environment file setup
│   └── dev.sh                ← Development startup helper
│
└── docker-compose.yml        ← Orchestrates all 4 services
```

---

## 4. Backend — Deep Dive

### 4.1 Application Entry Point — [main.py](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/main.py)

Uses the **app factory pattern** via `create_application()`:

- Creates a `FastAPI` instance with Swagger at `/api/docs` and ReDoc at `/api/redoc`
- Registers `CORSMiddleware` to allow the Next.js frontend to call the API
- Mounts the entire v1 router at `/api/v1`
- Uses a `@asynccontextmanager` **lifespan** to:
  - **On startup**: run `init_db()` (creates all tables), connect Redis
  - **On shutdown**: cleanly close Redis connections

```python
# Startup sequence
await init_db()            # SQLAlchemy creates all tables
await redis_manager.connect()  # Redis connection pool opens
```

---

### 4.2 Configuration — [core/config.py](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/core/config.py)

A single `Settings` class using `pydantic-settings` reads all config from environment variables (or `.env` file):

| Setting | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | (change me!) | JWT signing secret |
| `ALGORITHM` | HS256 | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Short-lived JWT lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Long-lived refresh token |
| `DATABASE_URL` | postgres+asyncpg://... | PostgreSQL async connection string |
| `REDIS_URL` | redis://localhost:6379/0 | Redis connection |
| `MATCHMAKING_RATING_RANGE` | 100 | Opponent search range (±100) |
| `MATCHMAKING_TIMEOUT_SECONDS` | 60 | Queue timeout |

A singleton `settings = Settings()` is imported everywhere — single source of truth.

---

### 4.3 Database Layer — [core/database.py](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/core/database.py)

Uses **SQLAlchemy 2 async** with the `asyncpg` driver:

```python
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,       # logs SQL in dev
    pool_size=10,
    pool_pre_ping=True,        # validates connections before use
)

AsyncSessionLocal = async_sessionmaker(...)
```

Key pieces:
- `Base` — `DeclarativeBase` that all ORM models inherit from
- `init_db()` — called at startup; imports all models and runs `Base.metadata.create_all`
- `get_db()` — FastAPI dependency that yields an `AsyncSession`, auto-commits on success, auto-rolls back on exception

---

### 4.4 Redis Layer — [core/redis.py](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/core/redis.py)

A `RedisManager` singleton handles two major responsibilities:

**Online User Tracking** (Redis Set: `online_users`):
```
SADD  online_users  "user_id"   # user connects
SREM  online_users  "user_id"   # user disconnects
SCARD online_users              # total online count
```

**Matchmaking Queue** (Redis Sorted Set: `matchmaking_queue`):
```
# Score = player rating → allows ZRANGEBYSCORE range queries
ZADD  matchmaking_queue  {rating}  '{"user_id":"5", "rating":1250}'
ZRANGEBYSCORE  matchmaking_queue  1150  1350  # find ±100 opponents
ZREM  matchmaking_queue  member              # remove when matched
```

The sorted set is the key insight: `ZRANGEBYSCORE` runs in **O(log N + M)** — extremely fast for finding opponents in a rating range, even with thousands of queued players.

Also provides generic `set/get/delete` helpers with TTL for caching.

---

### 4.5 Security — [core/security.py](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/core/security.py)

**Password Hashing:**
```python
pwd_context = CryptContext(schemes=["bcrypt"])

hash_password("mypassword")     # → "$2b$12$..."
verify_password("mypassword", hash)  # → True/False
```

**JWT Tokens (python-jose):**
- `create_access_token(data)` — Signs payload with `SECRET_KEY`, adds `exp` (30 min), `type: access`
- `create_refresh_token(data)` — Same but `exp` is 7 days, `type: refresh`
- `decode_token(token)` — Decodes and validates; raises HTTP 401 on failure

**FastAPI Auth Dependencies:**
- `get_current_user` — Extracts Bearer token, decodes it, loads User from DB
- `get_current_active_user` — Chains on top; additionally checks `user.is_active`

Usage in any route:
```python
async def my_route(user: User = Depends(get_current_active_user)):
    ...
```

---

### 4.6 Database Models

All models inherit from `Base` (SQLAlchemy `DeclarativeBase`).

#### [User](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/models/user.py)
The core entity — a registered player.

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | Auto-increment |
| `username` | String(50) | Unique, indexed |
| `email` | String(255) | Unique, indexed |
| `hashed_password` | String(255) | bcrypt hash |
| `rating` | Integer | Starts at 1200 (ELO) |
| `is_active` | Boolean | False = banned |
| `created_at` / `updated_at` | DateTime(tz) | Timestamps |

Relationships: `matches_as_player1`, `matches_as_player2`, `rating_record`, `submissions`

#### [Match](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/models/match.py)
A 1v1 coding battle session.

| Column | Notes |
|---|---|
| `player1_id`, `player2_id` | FK → users |
| `problem_id` | FK → problems |
| `winner_id` | FK → users (null until ended) |
| `status` | `pending → active → completed / cancelled` |
| `started_at`, `ended_at` | Nullable timestamps |

#### [Problem](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/models/problem.py)
A DSA coding question.

| Column | Notes |
|---|---|
| `slug` | URL-friendly unique identifier |
| `difficulty` | `easy / medium / hard` (Enum) |
| `tags` | JSON array e.g. `["array", "hash-map"]` |
| `examples` | JSON array of input/output pairs |
| `starter_code` | JSON map `{language → template}` |
| `constraints` | Text field |

#### [Submission](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/models/submission.py)
Every code submission during a match.

Status enum: `pending → running → accepted / wrong_answer / time_limit / memory_limit / runtime_error / compile_error`

Tracks `language`, `code` (full source), `runtime_ms`, and `memory_kb`.

#### [Rating](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/models/rating.py)
ELO change history — one row per match per player.

Stores `old_rating`, `new_rating`, `delta` (e.g., `+25`, `-15`). This gives players a full progression history.

#### [Contest](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/models/contest.py)
Tournament events (Phase 2 feature, model defined now).

Fields: `title`, `status` (`upcoming/active/finished/cancelled`), `max_participants`, `start_time`, `end_time`, `problem_ids` (JSON list).

---

### 4.7 API Endpoints

#### Health — [api/v1/health.py](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/api/v1/health.py)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/health/` | Liveness: returns `{status: "ok"}` if process is up |
| GET | `/api/v1/health/full` | Readiness: checks PostgreSQL (`SELECT 1`) + Redis (`PING`) |

Used by Docker's `healthcheck` config and monitoring tools.

#### Authentication — [api/v1/auth.py](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/api/v1/auth.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | No | Create account, return JWT pair |
| POST | `/api/v1/auth/login` | No | Verify credentials, return JWT pair |
| POST | `/api/v1/auth/refresh` | No | Exchange refresh token for new access token |

**Register flow:**
1. Check username uniqueness → HTTP 409 if taken
2. Check email uniqueness → HTTP 409 if taken
3. Hash password with bcrypt
4. Insert User with `rating=1200`
5. Return `{access_token, refresh_token, token_type: "bearer"}`

**Login flow:**
1. Find user by email
2. `verify_password(plain, hash)` — same error for "not found" and "wrong password" to prevent user enumeration attacks
3. Check `user.is_active`
4. Return JWT pair

#### Users — [api/v1/users.py](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/api/v1/users.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/users/me` | ✅ | Full private profile |
| PATCH | `/api/v1/users/me` | ✅ | Update username/email |
| GET | `/api/v1/users/leaderboard?limit=50` | No | Top players by rating |
| GET | `/api/v1/users/{username}` | No | Public profile |

#### Matchmaking — [api/v1/matchmaking.py](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/api/v1/matchmaking.py)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/matchmaking/join` | ✅ | Join queue / instant-match if opponent found |
| POST | `/api/v1/matchmaking/leave` | ✅ | Leave the queue |
| GET | `/api/v1/matchmaking/queue-size` | No | Public queue size |
| GET | `/api/v1/matchmaking/status` | ✅ | Check if you're in queue |

---

### 4.8 Matchmaking Service — [services/matchmaking.py](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/services/matchmaking.py)

Business logic separated from the API layer so it can be called from both HTTP endpoints and the WebSocket handler.

**`join_queue(user)` flow:**
```
1. Check Redis sorted set for opponent within ±100 rating BEFORE adding self
   → This avoids matching with yourself
2. If opponent found:
   a. Remove opponent from queue
   b. Generate pseudo match_id (Phase 2 will create a DB record)
   c. Send WebSocket `match_found` event to BOTH players
   d. Return {match_found: true, match_id: ...}
3. If no opponent:
   a. Add self to queue with rating as score
   b. Return {match_found: false, message: "X in queue"}
```

---

### 4.9 WebSocket System

#### [websockets/manager.py](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/websockets/manager.py) — Connection Registry

`ConnectionManager` is an **in-memory dict** mapping `user_id → WebSocket`:

- `connect(ws, user_id)` — Accepts WS, closes old connection if user reconnects from another tab
- `disconnect(user_id)` — Removes from registry
- `send_to_user(user_id, data)` — Sends JSON to one user; returns `False` if not connected
- `broadcast(data, exclude_user_id)` — Sends to all; auto-cleans dead connections

A singleton `ws_manager` is imported by both the endpoint and the matchmaking service.

#### [websockets/endpoint.py](file:///Users/srijansarkar/Documents/CodeBattle/backend/app/websockets/endpoint.py) — WS Handler

**Connection URL:** `ws://localhost:8000/api/v1/ws/battle?token=<JWT>`

**Lifecycle:**
```
Client connects with ?token=JWT
  → Validate JWT, load User from DB
  → If invalid: close(4001, "Invalid token")
  → ws_manager.connect(ws, user_id)
  → redis_manager.add_online_user(user_id)
  → Send "connected" event to client

Message loop:
  - "ping"             → reply "pong"
  - "matchmaking_join" → call MatchmakingService.join_queue()
  - "matchmaking_leave"→ remove from Redis queue
  - "chat"             → broadcast to all connected users (max 500 chars)
  - unknown event      → reply "error"

On disconnect (WebSocketDisconnect or error):
  → ws_manager.disconnect(user_id)
  → redis_manager.remove_online_user(user_id)
  → redis_manager.remove_from_matchmaking_queue(user_id)
```

**WebSocket Event Protocol (JSON):**

| Direction | Event | Payload |
|---|---|---|
| Server → Client | `connected` | `{user_id, username, rating, online_count}` |
| Server → Client | `match_found` | `{match_id, opponent_id, opponent_rating}` |
| Server → Client | `pong` | `{}` |
| Server → Client | `error` | `{detail: "..."}` |
| Client → Server | `ping` | `{}` |
| Client → Server | `matchmaking_join` | `{}` |
| Client → Server | `matchmaking_leave` | `{}` |
| Client → Server | `chat` | `{message: "..."}` |

---

## 5. Frontend — Deep Dive

### 5.1 Design System — [globals.css](file:///Users/srijansarkar/Documents/CodeBattle/frontend/src/app/globals.css)

The entire visual language is defined as **CSS custom properties** in `:root`:

```css
/* Color Palette */
--color-bg-primary:     #0a0a0f   /* deep dark base */
--color-brand-primary:  #6c63ff   /* purple accent */
--color-brand-secondary:#4facfe   /* blue accent */
--color-success:        #00e676   /* match found green */
--color-text-primary:   #f0f0ff   /* near-white text */

/* Brand Gradient */
--gradient-brand: linear-gradient(135deg, #6c63ff → #4facfe → #00f2fe)
```

**Reusable CSS classes:**
- `.glass-card` — Glassmorphism card (`backdrop-filter: blur(20px)` + subtle border)
- `.glass-card-hover` — Adds lift + glow on hover
- `.btn-primary` — Gradient button with shimmer sweep on hover
- `.btn-secondary` — Transparent bordered button
- `.btn-danger` — Red gradient (cancel search)
- `.form-input` — Dark-themed input with purple focus ring
- `.rating-badge` — Pill showing ELO number (e.g., `⚡ 1342`)
- `.status-online` / `.status-searching` — Pulsing dot indicators
- `.skeleton` — Shimmer loading placeholder

**Animations:** `fadeInUp`, `pulse-glow`, `float`, `shimmer`, `spin-slow`

**Typography:** Inter (UI text) + JetBrains Mono (code display), both from Google Fonts.

---

### 5.2 Authentication Context — [context/AuthContext.tsx](file:///Users/srijansarkar/Documents/CodeBattle/frontend/src/context/AuthContext.tsx)

Global auth state via React Context. Wraps the entire app so every component can access the current user.

**State shape:**
```ts
{
  user: User | null,
  accessToken: string | null,
  isLoading: boolean,       // true while checking localStorage on mount
  isAuthenticated: boolean,
}
```

**Actions:**
- `login(email, password)` — Calls API, stores tokens in localStorage, fetches `/users/me`
- `register(username, email, password)` — Same flow after registration
- `logout()` — Clears localStorage, resets state
- `refreshUser()` — Re-fetches current user from `/users/me` with existing token

**Session persistence:** On mount, checks `localStorage` for `codebattle_access_token`. If found, fetches the user profile to re-hydrate state after page refresh.

**Token storage keys:**
- `codebattle_access_token`
- `codebattle_refresh_token`

---

### 5.3 API Client — [lib/api.ts](file:///Users/srijansarkar/Documents/CodeBattle/frontend/src/lib/api.ts)

A typed service class wrapping `fetch`. All API calls go through the central `request<T>()` helper which:
1. Adds `Content-Type: application/json`
2. Adds `Authorization: Bearer <token>` if provided
3. Parses error bodies and throws `APIError(status, detail)`
4. Handles 204 No Content (returns `{}`)

**Methods:**
```ts
apiService.register({ username, email, password }) → TokenResponse
apiService.login({ email, password })              → TokenResponse
apiService.refreshToken(refreshToken)              → TokenResponse
apiService.getMe(token)                            → UserProfile
apiService.getUserProfile(username)                → PublicUserProfile
apiService.getLeaderboard(limit?)                  → PublicUserProfile[]
apiService.joinQueue(token)                        → MatchmakingStatus
apiService.leaveQueue(token)                       → { message }
apiService.getQueueSize()                          → { queue_size }
apiService.getHealth()                             → HealthStatus
```

Base URL: `process.env.NEXT_PUBLIC_API_URL` (default: `http://localhost:8000`)

---

### 5.4 WebSocket Client — [lib/websocket.ts](file:///Users/srijansarkar/Documents/CodeBattle/frontend/src/lib/websocket.ts)

`WsService` class providing:
- **Connection:** `ws.connect()` — builds URL `{WS_BASE}/api/v1/ws/battle?token=<JWT>` and opens socket
- **Disconnect:** `ws.disconnect()` — closes cleanly (code 1000), stops reconnect loop
- **Event subscription:** `ws.on("match_found", handler)` / `ws.off("match_found", handler)`
- **Sending:** `ws.send("matchmaking_join", {})` — JSON-serializes and sends
- **Heartbeat:** Sends `ping` every **25 seconds** to keep the connection alive
- **Auto-reconnect:** On unexpected close (non-1000), retries after **3 seconds**

Usage pattern in the matchmaking page:
```ts
const ws = new WsService(accessToken);
ws.on("match_found", (data) => router.push(`/battle/${data.match_id}`));
ws.connect();
// On cancel:
ws.disconnect();
```

---

### 5.5 Pages

#### Landing Page — [app/page.tsx](file:///Users/srijansarkar/Documents/CodeBattle/frontend/src/app/page.tsx) (`/`)

Public marketing page. **Sections:**
1. **Fixed Navbar** — glassmorphism bar with "Log in" and "Start Battling →" CTAs
2. **Hero** — "Code. Battle. Dominate." headline with floating orbs background, animated code snippet showing a Python `two_sum` solution with syntax highlighting
3. **Stats** — 4-column grid (10K+ Players, 500+ Problems, 1M+ Battles, 99.9% Uptime)
4. **Features** — 6-card grid: Real-Time 1v1, DSA Problems, ELO Rating, Instant Matchmaking, Global Leaderboard, Live Code Viewing
5. **CTA** — "Ready to battle?" section with purple radial glow
6. **Footer**

This page is a **Server Component** (no `"use client"`) with `export const metadata` for SEO.

#### Login — [app/(auth)/login/page.tsx](file:///Users/srijansarkar/Documents/CodeBattle/frontend/src/app/(auth)/login/page.tsx) (`/login`)

Client component with controlled form:
- Email + password inputs with `form-input` class
- Calls `useAuth().login()` on submit
- Shows `APIError.detail` in an error banner
- Loading spinner during submission
- Redirects to `/dashboard` on success
- Links to `/register` for new users

#### Register — [app/(auth)/register/page.tsx](file:///Users/srijansarkar/Documents/CodeBattle/frontend/src/app/(auth)/register/page.tsx) (`/register`)

Similar form with username + email + password fields. Calls `useAuth().register()` then redirects to `/dashboard`.

#### Dashboard — [app/(dashboard)/dashboard/page.tsx](file:///Users/srijansarkar/Documents/CodeBattle/frontend/src/app/(dashboard)/dashboard/page.tsx) (`/dashboard`)

Protected page showing:
- User profile card (username, rating badge, account creation date)
- Quick stats (matches played, win rate, rank)
- "Find Match" CTA linking to `/matchmaking`
- Recent activity / match history section

#### Matchmaking — [app/(dashboard)/matchmaking/page.tsx](file:///Users/srijansarkar/Documents/CodeBattle/frontend/src/app/(dashboard)/matchmaking/page.tsx) (`/matchmaking`)

The battle lobby — three states: `idle | searching | found`

**State machine:**
```
[idle]
  → Click "⚡ Find Opponent"
  → Open WebSocket (listen for match_found)
  → POST /matchmaking/join

[searching]
  → Search timer counts up (MM:SS)
  → Player card pulses with brand gradient animation
  → Queue size polls every 5 seconds
  → Click "Cancel Search" → POST /matchmaking/leave → [idle]
  → WebSocket fires "match_found" → [found]

[found]
  → "✅ Opponent Found!" displayed in green
  → Auto-redirect to /battle/{match_id} after 2 seconds
```

**Implementation details:**
- Dual approach: REST API join + WebSocket listener (covers both immediate match and delayed match via push)
- `useRef` for the `WsService` instance (persists across renders without causing re-render)
- Timer implemented with `setInterval` in a `useEffect`
- Queue size polls independently via a separate `setInterval`
- WebSocket cleaned up on component unmount via cleanup function in `useEffect`

#### Leaderboard — [app/leaderboard/page.tsx](file:///Users/srijansarkar/Documents/CodeBattle/frontend/src/app/leaderboard/page.tsx) (`/leaderboard`)

Public page showing top-rated players. Fetches `/users/leaderboard?limit=50`, renders a ranked table with rating badges.

---

### 5.6 Layout Hierarchy

```
app/layout.tsx                        ← Root: <html>, <body>, AuthProvider
  ├── app/page.tsx                    ← Landing page (no layout wrapper)
  ├── app/(auth)/layout.tsx           ← Auth pages (just AuthProvider, no navbar)
  │   ├── app/(auth)/login/page.tsx
  │   └── app/(auth)/register/page.tsx
  ├── app/(dashboard)/layout.tsx      ← Auth guard + Navbar injection
  │   ├── app/(dashboard)/dashboard/page.tsx
  │   └── app/(dashboard)/matchmaking/page.tsx
  └── app/leaderboard/page.tsx
```

**`(dashboard)/layout.tsx`** is the auth guard: it checks `isAuthenticated` from `useAuth()`. If `false` and not loading, redirects to `/login`. This protects all dashboard routes without repetition.

---

### 5.7 Navbar — [components/Navbar.tsx](file:///Users/srijansarkar/Documents/CodeBattle/frontend/src/components/Navbar.tsx)

Fixed-position glassmorphism bar injected in the dashboard layout.

**Features:**
- Logo links to `/dashboard` (auth) or `/` (unauth)
- Nav links: Dashboard, Play (`/matchmaking`), Leaderboard
  - Auth-required links (`Dashboard`, `Play`) are hidden if not logged in
- Shows `rating-badge` (⚡ 1342) and username when authenticated
- "Logout" button calls `useAuth().logout()` + `router.push("/")`
- **Mobile menu** — hamburger button toggles a dropdown with all links
- Active link highlighted with brand color background

---

## 6. Infrastructure & Docker

### 6.1 [docker-compose.yml](file:///Users/srijansarkar/Documents/CodeBattle/docker-compose.yml)

Defines 4 services on `codebattle_network` (bridge):

| Service | Image/Build | Port | Depends On |
|---|---|---|---|
| `postgres` | `postgres:16-alpine` | 5432 | — |
| `redis` | `redis:7-alpine` | 6379 | — |
| `backend` | `./backend/Dockerfile` | 8000 | postgres ✅, redis ✅ |
| `frontend` | `./frontend/Dockerfile` | 3000 | backend |

**Health checks:**
- PostgreSQL: `pg_isready -U codebattle -d codebattle_db`
- Redis: `redis-cli ping`
- Backend: `curl -f http://localhost:8000/api/v1/health/`

**Volume mounts (dev mode):**
- `./backend:/app` — hot reload Python code
- `./frontend:/app` — hot reload Next.js code
- `/app/node_modules` — anonymous volume prevents host overwrite

**Backend startup command:** `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

**Redis configuration:** `--maxmemory 256mb --maxmemory-policy allkeys-lru` (LRU eviction when full)

### 6.2 [docker/postgres/init.sql](file:///Users/srijansarkar/Documents/CodeBattle/docker/postgres/init.sql)

Runs on first PostgreSQL boot. Sets up extensions/schema needed before SQLAlchemy's `create_all`.

### 6.3 Scripts

- [scripts/setup.sh](file:///Users/srijansarkar/Documents/CodeBattle/scripts/setup.sh) — Copies `.env.example` to `.env` for all services
- [scripts/dev.sh](file:///Users/srijansarkar/Documents/CodeBattle/scripts/dev.sh) — Starts all Docker services with logs

---

## 7. Key Data Flows

### 7.1 Registration → Login → Dashboard

```
1. User fills register form (/register)
2. POST /api/v1/auth/register {username, email, password}
   Backend:
   a. Check username/email uniqueness (HTTP 409 if conflict)
   b. hash_password(password) with bcrypt
   c. INSERT INTO users (rating=1200)
   d. Return {access_token, refresh_token}
3. AuthContext stores tokens in localStorage
4. GET /api/v1/users/me (with Bearer token)
5. AuthContext stores User object in state
6. router.push("/dashboard")
```

### 7.2 Find a Match (Matchmaking Flow)

```
User on /matchmaking clicks "⚡ Find Opponent"
   │
   ├── New WsService(accessToken).connect()
   │   WebSocket: ws://localhost:8000/api/v1/ws/battle?token=JWT
   │   Server: validates JWT, registers connection, adds to online_users set
   │   Client: listens for "match_found" event
   │
   └── POST /api/v1/matchmaking/join
       MatchmakingService.join_queue(user):
         → ZRANGEBYSCORE matchmaking_queue [rating-100, rating+100]
         
         Case A: Opponent found
           → ZREM opponent from queue
           → ws_manager.send_to_user(user_id, "match_found" + match details)
           → ws_manager.send_to_user(opponent_id, "match_found" + match details)
           → Both clients receive WebSocket event
           → Both redirect to /battle/{match_id}
         
         Case B: No opponent
           → ZADD matchmaking_queue (self, with rating as score)
           → Return {match_found: false}
           → Client shows searching state, waits for WS event
           
On disconnect/cancel:
  → ws_manager.disconnect(user_id)
  → redis_manager.remove_online_user(user_id)
  → redis_manager.remove_from_matchmaking_queue(user_id)
```

### 7.3 JWT Auth on Every Request

```
Frontend: localStorage.getItem("codebattle_access_token")
  ↓
request<T>() adds:  Authorization: Bearer eyJ...
  ↓
Backend: oauth2_scheme extracts token
  ↓
get_current_user():
  decode_token(token) → TokenData(user_id="5")
  SELECT * FROM users WHERE id = 5
  return User object
  ↓
Route handler receives: current_user: User
```

---

## 8. API Quick Reference

### Authentication
```
POST /api/v1/auth/register       body: {username, email, password}
POST /api/v1/auth/login          body: {email, password}
POST /api/v1/auth/refresh        query: ?refresh_token_str=...
```

### Users
```
GET  /api/v1/users/me            auth required
PATCH /api/v1/users/me           auth required
GET  /api/v1/users/leaderboard   ?limit=50
GET  /api/v1/users/{username}
```

### Matchmaking
```
POST /api/v1/matchmaking/join    auth required
POST /api/v1/matchmaking/leave   auth required
GET  /api/v1/matchmaking/status  auth required
GET  /api/v1/matchmaking/queue-size
```

### Health
```
GET /api/v1/health/
GET /api/v1/health/full
```

### WebSocket
```
WS  /api/v1/ws/battle?token=<JWT>
```

**Auto-generated docs:** http://localhost:8000/api/docs (Swagger UI)

---

## 9. Environment Variables

### Backend (`backend/.env`)
```
SECRET_KEY=<32+ chars random string>
DATABASE_URL=postgresql+asyncpg://codebattle:codebattle_password@localhost:5432/codebattle_db
REDIS_URL=redis://localhost:6379/0
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
MATCHMAKING_RATING_RANGE=100
DEBUG=False
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend (`frontend/.env.local`)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

## 10. Getting Started

### Docker (Recommended)
```bash
cd CodeBattle
./scripts/setup.sh          # Copy .env files
nano backend/.env           # Set SECRET_KEY
docker compose up --build   # Start all 4 services
open http://localhost:3000
```

### Local Development (No Docker)
```bash
# Terminal 1 — Backend
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload

# Terminal 2 — Frontend
cd frontend && npm install
cp .env.example .env.local
npm run dev
```

---

## 11. Phase 1 vs Phase 2 Roadmap

### ✅ Phase 1 (Complete — Current State)
- User registration & login (JWT + bcrypt)
- ELO-style rating starting at 1200
- Redis matchmaking queue (sorted set by rating)
- WebSocket real-time match notifications
- Dashboard, matchmaking lobby, leaderboard pages
- All 6 database models defined
- Docker orchestration
- Health check endpoints
- Auto-generated Swagger/ReDoc docs

### 🚀 Phase 2 (Next Steps)
- **Monaco Editor** integration in the battle room
- **Code execution engine** / judge system (run submitted code against test cases)
- Real DB `Match` record created when match is found
- **ELO calculation** after each match (`old_rating ± delta` stored in `ratings` table)
- Live opponent code viewing (stream keystrokes via WebSocket)
- Match history page per user
- **Contest/tournament** system (using the `Contest` model)
- Profile pages with stats graphs
- Social features (friends list, direct challenges)
- Alembic migrations (replace `create_all` with versioned migrations)

---

## 12. Common Troubleshooting

| Issue | Fix |
|---|---|
| Backend can't connect to PostgreSQL | `docker compose ps` → check postgres is healthy; `docker compose logs postgres` |
| JWT expired | Call `/api/v1/auth/refresh` with refresh token, or re-login |
| WebSocket fails to connect | Check `?token=` param is a valid, non-expired JWT; inspect Network → WS tab in DevTools |
| Frontend can't reach backend | Verify `NEXT_PUBLIC_API_URL` in `.env.local`; inside Docker use `http://backend:8000` |
| Rating mismatch | Rating updates in Phase 2; Phase 1 rating stays at default 1200 after matches |
