                <div align="center">

# 🤖 AI Web Automation Agent

**Give it a goal. Watch it browse.**

Type a natural-language goal and an autonomous agent drives a real browser to carry it out — looking at each page, deciding the next action, and returning structured results while you watch it live.

[![CI](https://github.com/Akay-74/AI-Web-Automation/actions/workflows/ci.yml/badge.svg)](https://github.com/Akay-74/AI-Web-Automation/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium-2EAD33?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev)
[![OpenAI](https://img.shields.io/badge/LLM-OpenRouter%2FOpenAI-412991?style=flat-square&logo=openai&logoColor=white)](https://openrouter.ai)
[![SQLite](https://img.shields.io/badge/DB-SQLite%20%7C%20PostgreSQL-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## 🎯 What It Does

Type a goal like **"Search Wikipedia for web scraping and extract the article summary"** and the agent:

1. 👁️ **Looks** at the current page — every interactive element, the headings, the visible text
2. 🧠 **Decides** the single next action against *that* page, referring to elements by id
3. 🖱️ **Acts** — navigates, types, clicks, scrolls, switches tabs
4. 🔁 **Repeats**, so a page that loaded differently than expected changes the next decision
5. 📦 **Extracts** structured rows once the data it needs is on screen
6. 🛡️ **Asks first** before anything irreversible (placing an order, deleting an account, entering a password)
7. 🤝 **Hands over** to you on a login or CAPTCHA wall — and takes the wheel back when you are done
8. 📡 **Streams** a live CDP screencast you can click straight into

### Why observe-then-decide

Planning a whole run up front means inventing CSS selectors for pages you have not loaded. Those selectors miss, and the run dies on step two. Here the perception layer assigns an `element_id` to every interactive element on the page it just rendered, and the planner may only choose from that list — so it cannot invent a target that isn't there.

---

## 🖥️ How It Works — Live Flow

### Step 1: Submit a goal

```
Goal: "Search Wikipedia for 'Playwright software' and extract the title and summary"
```

### Step 2: The agent cycles, one page at a time

```
[observe] about:blank              → 0 elements
[decide ] navigate                 → https://www.wikipedia.org/
[observe] wikipedia.org            → 44 elements  ([31] input "Search Wikipedia", ...)
[decide ] type  element_id=31      → "Playwright software", submit
[observe] search results page      → 78 elements  ([10] a "Playwright (software)", ...)
[decide ] click element_id=10
[observe] en.wikipedia.org/wiki/…  → 312 elements
[decide ] extract schema=article   → 1 item
[decide ] finish                   → "Extracted the title and summary"
```

Real output from that run:

```json
{
  "items": [
    {
      "title": "Playwright (software)",
      "source": "Wikipedia",
      "summary": "Playwright is an open-source automation library for browser testing and web scraping developed by Microsoft and launched on 31 January 2020, which has since become popular among programmers and web developers.",
      "url": "https://en.wikipedia.org/wiki/Playwright_(software)",
      "published_date": "January 31, 2020"
    }
  ]
}
```

### Step 3: Live feed in the UI

```
ℹ️  Task started
ℹ️  Browser ready
🌐 Opening https://www.wikipedia.org/
⌨️  Typing a field: "Playwright software" and submitting
🖱️  Clicking: the Playwright (software) article link
🔍 Extracted 1 item(s) — 1 total
🏁 Finishing: Extracted the title and summary
```

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 14)                        │
│  ┌───────────┐  ┌──────────────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Task Form │  │ Live Browser     │  │ Results  │  │  History  │  │
│  │ (goal in) │  │ Panel + Feed     │  │  Cards   │  │           │  │
│  └─────┬─────┘  └────────┬─────────┘  └────┬─────┘  └───────────┘  │
└────────┼────────────────┼───────────────────┼──────────────────────┘
         │ REST            │ WebSocket (both ways)
         ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI)                           │
│  ┌──────────┐   ┌──────────────────┐   ┌────────────────────────┐  │
│  │ REST API │   │ ConnectionManager│◄──│ Task Runner            │  │
│  └────┬─────┘   │ (single event    │   │ (background coroutine) │  │
│       │         │  sink)           │   └───────────┬────────────┘  │
│       ▼         └──────────────────┘               │               │
│  ┌──────────────┐                      ┌───────────▼────────────┐  │
│  │ SQLite /     │                      │      AGENT LOOP        │  │
│  │ PostgreSQL   │                      │                        │  │
│  └──────────────┘                      │  ┌──────────────────┐  │  │
│                                        │  │ 1. observe       │  │  │
│  ┌───────────────────────────────┐     │  │    ElementMapper │  │  │
│  │ Agent Registry                │◄────│  │    PageObserver  │  │  │
│  │ task_id → AgentLoop + Browser │     │  └────────┬─────────┘  │  │
│  │ (routes your clicks into the  │     │  ┌────────▼─────────┐  │  │
│  │  browser the agent is using)  │     │  │ 2. decide        │  │  │
│  └───────────────────────────────┘     │  │    AIPlanner     │  │  │
│                                        │  └────────┬─────────┘  │  │
│                                        │  ┌────────▼─────────┐  │  │
│                                        │  │ 3. gate          │  │  │
│                                        │  │  SafetyValidator │  │  │
│                                        │  │  ControlStateM.  │  │  │
│                                        │  └────────┬─────────┘  │  │
│                                        │  ┌────────▼─────────┐  │  │
│                                        │  │ 4. act           │  │  │
│                                        │  │ BrowserController│  │  │
│                                        │  │   (Playwright)   │  │  │
│                                        │  └──────────────────┘  │  │
│                                        └────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### One execution path, on purpose

The agent runs as a background coroutine **inside the API process**. That is not a shortcut — the live browser panel forwards your clicks and keystrokes into the same `BrowserController` object the agent is driving, looked up through a process-local registry. Move execution to a separate worker process and that handover cannot work at all.

For the same reason there is one event sink. The loop hands every event to `ConnectionManager`, which writes it to the task log and pushes it to every open socket. No broker, no database polling.

---

## 🧩 Core Components

| Component | File | Description |
|---|---|---|
| **Agent Loop** | `agent/loop.py` | The observe → decide → gate → act cycle, plus every bounded wait |
| **AI Planner** | `agent/planner.py` | One LLM call per step: current page + history → the next action |
| **Element Mapper** | `perception/element_mapper.py` | Assigns `element_id` to each interactive element; resolves ids back to selectors |
| **Page Observer** | `perception/page_observer.py` | Headings and visible text; detects login / 2FA walls that need a human |
| **Browser State** | `browser/state.py` | Normalized page description, and the summary the planner actually reads |
| **Browser Controller** | `browser/controller.py` | Playwright wrapper: actions, CDP screencast, tabs, CAPTCHA, input forwarding |
| **Data Extractor** | `browser/extractor.py` | Page text → structured rows against a schema (product / job / article / generic) |
| **Safety Validator** | `safety/permissions.py` | Flags only irreversible actions, judged on the resolved element |
| **Control State Machine** | `agent/control.py` | AI ↔ human handover and approval, with a timeout on every wait |
| **Task Runner** | `agent/runner.py` | Runs one loop, persists events and results, updates task status |
| **Agent Registry** | `agent/registry.py` | `task_id` → live loop and browser, so the UI can reach them |
| **WebSocket Hub** | `api/routes/websocket.py` | Streams events out, accepts clicks and control commands in |

---

## 🛡️ Safety Gate — Narrow On Purpose

An over-eager gate is not a safe gate. If "Submit search" needs approval then every task stops dead waiting for a human, and the agent is useless. So the gate asks only about things you cannot undo:

```python
# Allowed without asking — ordinary browsing
"Submit search"     "Sign in"      "Add to cart"     "Save changes"
"Next page"         "Reply"        "Order history"   "Account settings"

# Requires your approval — irreversible
"Place your order"  "Buy now"      "Confirm payment"    "Proceed to checkout"
"Subscribe"         "Transfer funds"  "Delete my account"
# ...plus typing into any real password field, and any click on paypal/stripe/a bank
```

It classifies the **resolved element** — the accessible name and input type read off the live page — not the model's prose description of what it thinks it is doing.

### Nothing waits forever

| Wait | Bound | On timeout |
|---|---|---|
| Human approval of a risky action | `APPROVAL_TIMEOUT_SECONDS` (180s) | Treated as declined; the agent moves on |
| Paused for a human (login, 2FA, CAPTCHA) | `HUMAN_PAUSE_TIMEOUT_SECONDS` (300s) | Task fails with a plain reason |
| Same action repeated with no effect | `MAX_REPEATED_ACTIONS` (3) | Task stops — the page is not responding to it |
| Actions failing back to back | `MAX_CONSECUTIVE_FAILURES` (4) | Task stops with the last error |
| Total steps | `MAX_STEPS_PER_TASK` (25) | Returns whatever was collected |

---

## 🚀 Quickstart: Local Mode (No Docker Required)

### Prerequisites
- Python 3.11+
- Node.js 18+
- An [OpenRouter](https://openrouter.ai) or OpenAI API key

### 1. Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium

# Create backend/.env
cat > .env << EOF
OPENAI_API_KEY=sk-or-v1-your-openrouter-key-here
OPENAI_BASE_URL=https://openrouter.ai/api/v1
DATABASE_URL=sqlite:///./agent.db
# Optional: require a shared secret on every API/WebSocket call
# API_KEY=pick-a-long-random-string
EOF

uvicorn app.main:app --reload --port 8000
```

Model ids are namespaced automatically: with an OpenRouter base URL, `gpt-4o-mini` is sent as `openai/gpt-4o-mini`. Set `OPENAI_MODEL` to use anything else.

### 2. Frontend

```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

**Open [http://localhost:3000](http://localhost:3000)** — the app is ready. SQLite is created on first run; nothing else to stand up.

### Useful settings

All optional, all via `backend/.env`:

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_MODEL` | `gpt-4o-mini` | Any OpenAI-compatible chat model |
| `BROWSER_HEADLESS` | `true` | `false` to watch the real window |
| `BROWSER_USER_DATA_DIR` | — | Point at a Chrome profile to reuse existing logins |
| `VIEWPORT_WIDTH` / `VIEWPORT_HEIGHT` | `1440` / `900` | Browser size; the screencast matches it 1:1 |
| `SCREENCAST_FPS` / `SCREENCAST_QUALITY` | `8` / `55` | Raise for a smoother stream, at more bandwidth |
| `MAX_STEPS_PER_TASK` | `25` | Step budget per task |
| `API_KEY` | — | Require `X-API-Key` on `/api/*` and `?api_key=` on the WebSocket. Set the same value as `NEXT_PUBLIC_API_KEY` in `frontend/.env.local` |

---

## 🐳 Docker Compose

```bash
echo "OPENAI_API_KEY=sk-or-v1-your-key" >> backend/.env
echo "OPENAI_BASE_URL=https://openrouter.ai/api/v1" >> backend/.env

docker compose up --build
```

Services: `postgres`, `backend` (FastAPI + the agent), `frontend` (Next.js).

---

## 🧪 Running Tests

```bash
cd backend
source venv/bin/activate
pytest
```

102 tests, no network and no browser, a couple of seconds. The same suite runs in GitHub Actions on every push, alongside a frontend typecheck and production build:

```
tests/test_agent_loop.py       # the cycle: re-observation, stall + failure guards, approval, cancel
tests/test_auth.py             # optional API key on HTTP routes and the WebSocket
tests/test_browser_state.py    # the page summary the planner reads; config/model-id handling
tests/test_control.py          # AI ↔ human handover; every wait is bounded
tests/test_planner.py          # surviving malformed or oddly-shaped model JSON
tests/test_safety.py           # ordinary clicks pass, irreversible ones are gated
```

---

## 📁 Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, DB init
│   │   ├── config.py               # Pydantic Settings (loads .env by absolute path)
│   │   ├── api/auth.py             # Optional shared-secret API key
│   │   ├── api/routes/
│   │   │   ├── tasks.py            # Task CRUD + /start + /cancel + /logs
│   │   │   ├── results.py          # Results endpoints
│   │   │   └── websocket.py        # WS: events out, user input in
│   │   ├── models/                 # SQLAlchemy ORM (sqlalchemy.Uuid — SQLite safe)
│   │   ├── schemas/                # Pydantic v2 request/response schemas
│   │   └── services/
│   │       ├── agent/              # loop.py, planner.py, control.py, runner.py, registry.py
│   │       ├── browser/            # controller.py, state.py, extractor.py
│   │       ├── perception/         # element_mapper.py, page_observer.py
│   │       └── safety/             # permissions.py
│   └── tests/                      # 102 offline unit tests
├── frontend/
│   └── src/
│       ├── app/                    # Next.js App Router pages
│       ├── components/             # LiveBrowserPanel, ExecutionFeed, ResultCard, Sidebar
│       ├── hooks/                  # useTaskWebSocket.ts
│       └── lib/                    # api.ts (typed API client)
├── .github/workflows/ci.yml        # pytest + frontend typecheck/build
├── docker-compose.yml
└── DEVELOPER_ONBOARDING.md
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/tasks` | Create a new task |
| `GET` | `/api/tasks` | List tasks (filter by `status`, paginate) |
| `GET` | `/api/tasks/{id}` | Task details & status |
| `POST` | `/api/tasks/{id}/start` | Start agent execution |
| `POST` | `/api/tasks/{id}/cancel` | Cancel a task, stopping a running agent |
| `GET` | `/api/tasks/{id}/logs` | Step-by-step event log |
| `GET` | `/api/tasks/{id}/results` | Extracted rows |
| `DELETE` | `/api/tasks/{id}` | Delete a task with its logs and results |
| `WS` | `/ws/tasks/{id}` | Live events out; clicks and control commands in |
| `GET` | `/health` | Liveness, whether an LLM key is configured, and whether auth is on |

**Auth:** off by default. With `API_KEY` set, every `/api/*` call needs an `X-API-Key` header and the WebSocket needs `?api_key=…` (browsers cannot set headers on a socket handshake); otherwise HTTP returns `401` and the socket closes with `1008`. `/health` stays public.

**Create and run a task:**

```bash
TASK=$(curl -s -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"goal": "Search Wikipedia for web scraping and extract the article summary"}')

ID=$(echo "$TASK" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
curl -s -X POST "http://localhost:8000/api/tasks/$ID/start"
curl -s "http://localhost:8000/api/tasks/$ID/results"
```

**WebSocket messages** all share one envelope:

```jsonc
{ "task_id": "…", "step": 3, "action": "click",
  "raw_event": { "description": "…", "params": { "element_id": 10 } },
  "ui_event":  { "type": "action", "message": "Clicking: …" },
  "timestamp": "…" }
```

Inbound, from the live panel: `{"user_action": "click", "x": 720, "y": 430}`, plus
`take_control`, `give_control_back`, `pause`, `resume`, `approve_action`,
`reject_action`, `captcha_resume`, `cancel`, `type`, `keypress`, `scroll`.

---

## ⚠️ Known Limitations

Honest scope notes — this is a single-user tool, not a hosted service.

- **Auth is a shared secret, not user accounts.** `NEXT_PUBLIC_API_KEY` ships in the frontend bundle, so it keeps strangers off a personal deployment; it does not separate users. Real multi-tenant use would need per-user auth and per-user task ownership.
- **CAPTCHAs go to a human.** The agent detects a challenge and hands the live browser to you; it never tries to solve or bypass one.
- **One process runs the agents.** Tasks run in the API process, so concurrent tasks share its CPU and memory; there is no job queue or horizontal scaling yet.
- **The safety gate is pattern-based.** It matches the resolved element's accessible name against known high-risk phrases. It is deliberately narrow, so an unusually worded "buy" button can slip past it — keep `BROWSER_USER_DATA_DIR` away from profiles logged in to anything you can't afford to lose.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14, React, Tailwind CSS |
| **Backend** | Python 3.13, FastAPI, SQLAlchemy (async), Pydantic v2 |
| **Browser** | Playwright (async Chromium) + Chrome DevTools Protocol screencast |
| **LLM** | Any OpenAI-compatible endpoint (OpenRouter, OpenAI) |
| **Database** | SQLite (local) / PostgreSQL (production) |
| **Comms** | One WebSocket per task, bidirectional |
| **Containers** | Docker + Docker Compose |

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built with ❤️ by <a href="https://github.com/Akay-74">Akay-74</a></sub>
</div>
