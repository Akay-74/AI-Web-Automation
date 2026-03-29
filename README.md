<div align="center">

# 🤖 AI Web Automation Agent

**Give it a goal. Watch it browse.**

A production-grade platform where users type a natural-language goal and an autonomous AI agent controls a real browser to complete it — extracting, validating, and returning structured results in real time.

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium-2EAD33?style=flat-square&logo=playwright&logoColor=white)](https://playwright.dev)
[![OpenAI](https://img.shields.io/badge/LLM-OpenRouter%2FOpenAI-412991?style=flat-square&logo=openai&logoColor=white)](https://openrouter.ai)
[![SQLite](https://img.shields.io/badge/DB-SQLite%20%7C%20PostgreSQL-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

## 🎯 What It Does

Type a goal like **"Find the cheapest RTX 4060 laptop on Amazon"** and the agent:

1. 🧠 **Plans** a step-by-step browser action sequence using GPT-4o-mini
2. 🌐 **Controls** a headless Chromium browser using Playwright
3. 🖱️ **Navigates**, types, clicks, scrolls, and extracts data from live websites
4. ✅ **Validates** results against your constraints (GPU model, price cap, brand)
5. 🔄 **Replans** automatically if constraints aren't satisfied
6. 📡 **Streams** live status updates to your browser via WebSocket

---

## 🖥️ How It Works — Live Demo Flow

### Step 1: Submit a Goal
User types a natural language goal in the **New Task** form.

```
Goal: "Find the cheapest RTX 4060 laptop on Amazon under $1000, preferably ASUS"
```

### Step 2: Agent Plans & Executes
The AI Planner decomposes the goal into an action plan (single LLM call), then the Agent Loop executes each step:

```
[Step 1] navigate → https://amazon.com
[Step 2] type     → searchbox: "RTX 4060 laptop"
[Step 3] click    → search button
[Step 4] scroll   → loading more results
[Step 5] extract  → 12 product listings found
[Step 6] validate → 8 match RTX 4060, 4 filtered out (wrong GPU)
[Step 7] evaluate → goal met: cheapest valid result = $899.99
```

### Step 3: Structured Results Returned
```json
{
  "type": "product_comparison",
  "summary": "Found 8 RTX 4060 laptops. Cheapest valid: ASUS TUF A15 at $899.99",
  "items": [
    {
      "name": "ASUS TUF Gaming A15 RTX 4060",
      "price": 899.99,
      "currency": "USD",
      "rating": 4.5,
      "is_valid": true,
      "validation_reason": "GPU matches RTX 4060, brand matches ASUS, price under $1000",
      "specs": { "ram": "16GB", "storage": "512GB SSD", "display": "15.6\" 144Hz" }
    },
    {
      "name": "MSI Thin 15 RTX 4060",
      "price": 949.00,
      "is_valid": true,
      "validation_reason": "GPU matches RTX 4060, price under $1000"
    }
  ]
}
```

### Step 4: Live WebSocket Feed (what the frontend displays)
```
🟡 [10:00:01] Task started
📋 [10:00:02] Plan created: 7 steps
🌐 [10:00:03] Navigating to amazon.com
⌨️  [10:00:05] Typing search query...
🖱️  [10:00:06] Clicking search button
📜 [10:00:09] Scrolling for more results
🔍 [10:00:12] Extracting 12 product listings
✅ [10:00:14] Validation: 8/12 items pass constraints
🏁 [10:00:15] Task completed — 8 valid results found
```

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 14)                        │
│  ┌───────────┐  ┌──────────────────┐  ┌──────────┐  ┌───────────┐  │
│  │ Task Form │  │ Agent Monitor    │  │ Results  │  │  History  │  │
│  │ (goal in) │  │ (WebSocket live) │  │Dashboard │  │           │  │
│  └─────┬─────┘  └────────┬─────────┘  └────┬─────┘  └───────────┘  │
└────────┼────────────────┼───────────────────┼─────────────────────-─┘
         │                │                   │
         ▼                ▼                   ▼ REST / WebSocket
┌────────────────────────────────────────────────────────────────────┐
│                       BACKEND (FastAPI)                             │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ REST API │  │ WebSocket Hub│  │Task Manager │  │  Auth Layer │ │
│  └────┬─────┘  └──────┬───────┘  └──────┬──────┘  └─────────────┘ │
└───────┼───────────────┼─────────────────┼──────────────────────────┘
        │               │                 │
        ▼               ▼                 ▼
  ┌───────────┐  ┌────────────┐  ┌────────────────────────────────┐
  │ SQLite /  │  │ Redis      │  │       AGENT WORKER             │
  │ PostgreSQL│  │ PubSub +   │  │  ┌──────────┐  ┌───────────┐  │
  └───────────┘  │ Task Queue │  │  │ AI       │→ │ Browser   │  │
                 └────────────┘  │  │ Planner  │  │Controller │  │
                                 │  └──────────┘  │(Playwright)│  │
  ┌────────────┐                 │                └─────┬───────┘  │
  │   FAISS    │◄────────────────│       ┌──────────────▼───────┐  │
  │  Vector    │                 │       │ Page Analyzer +      │  │
  │  Memory    │                 │       │ Data Extractor       │  │
  └────────────┘                 │       └──────────────┬───────┘  │
                                 │  ┌───────────────────▼────────┐ │
                                 │  │ Result Evaluator           │ │
                                 │  │ + Constraint Validator     │ │
                                 │  └────────────────────────────┘ │
                                 └────────────────────────────────--┘
```

### Dual Execution Mode (Auto-Detected)
```
POST /api/tasks/{id}/start
    ↓
Is Redis reachable?
    YES → rpush("task_queue", task_id)     ← distributed worker picks it up
    NO  → asyncio.create_task(run_agent()) ← runs in-process (local dev)

GET /ws/tasks/{id}
    ↓
Is Redis reachable?
    YES → subscribe to "task_updates:{id}" PubSub channel
    NO  → poll DB every 500ms for new TaskLog rows
```
No configuration needed — the system adapts automatically.

---

## 🧩 Core Components

| Component | File | Description |
|---|---|---|
| **AI Planner** | `agent/planner.py` | Converts natural language goal → JSON action plan (1 LLM call; uses deterministic templates first) |
| **Agent Loop** | `agent/loop.py` | Orchestrates plan execution, handles replanning, broadcasts status |
| **Browser Controller** | `browser/controller.py` | Playwright wrapper: navigate, click, type, scroll, screenshot, extract |
| **Page Analyzer** | `browser/analyzer.py` | Converts raw HTML → compressed inner text for reliable LLM parsing |
| **Data Extractor** | `browser/extractor.py` | CSS heuristic extraction → LLM fallback; outputs structured JSON |
| **Result Validator** | `agent/validator.py` | Enforces GPU model, price cap, brand constraints with regex |
| **Result Evaluator** | `agent/evaluator.py` | Deterministic completion check → LLM verification if inconclusive |
| **Vector Memory** | `memory/vector.py` | FAISS + `text-embedding-3-small`; optional, gracefully disabled |
| **WebSocket Hub** | `api/routes/websocket.py` | Redis PubSub or DB polling fallback for live updates |

---

## 🔍 Validation Engine — Proof of Work

The `ResultValidator` parses constraints directly from the goal text:

```python
# Goal: "Find cheapest RTX 4060 laptop under $1000, ASUS brand"
#
# Validator extracts:
#   gpu_required  = "RTX 4060"
#   price_cap     = 1000.0
#   brand_filter  = "asus"
#
# Each result gets:
{
  "name": "ASUS TUF A15 RTX 4060",
  "price": 899.99,
  "is_valid": True,
  "validation_reason": "GPU matches RTX 4060 ✓, price $899.99 < $1000 ✓, brand ASUS ✓"
}
{
  "name": "Lenovo IdeaPad RTX 4050",
  "price": 799.99,
  "is_valid": False,
  "validation_reason": "GPU mismatch: found RTX 4050, requires RTX 4060 ✗"
}
```

If 0 valid items are found after extraction, the agent **automatically replans** and tries again.

---

## 🚀 Quickstart: Local Mode (No Docker Required)

### Prerequisites
- Python 3.11+
- Node.js 18+
- An [OpenRouter](https://openrouter.ai) API key (free tier available)

### 1. Backend Setup
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
EOF

uvicorn app.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

**Open [http://localhost:3000](http://localhost:3000)** — the app is ready.

> **Note:** The backend uses SQLite locally — no Postgres or Redis needed.

---

## 🐳 Production: Docker Compose (Full Stack)

Runs Postgres + Redis + distributed workers:

```bash
# Set your API key first
echo "OPENAI_API_KEY=sk-or-v1-your-key" >> backend/.env
echo "OPENAI_BASE_URL=https://openrouter.ai/api/v1" >> backend/.env

docker compose up --build
```

Services launched: `postgres`, `redis`, `backend` (FastAPI), `worker` (task processor), `frontend` (Next.js).

---

## 🧪 Running Tests

```bash
cd backend
source venv/bin/activate

# Unit tests — validation logic (no network, runs in < 1s)
pytest tests/test_validation_gpu.py -v

# Expected output:
# PASSED tests/test_validation_gpu.py::test_rtx4060_valid
# PASSED tests/test_validation_gpu.py::test_rtx4050_invalid
# PASSED tests/test_validation_gpu.py::test_price_cap
# PASSED tests/test_validation_gpu.py::test_brand_filter
# 4 passed in 0.12s

# Integration test (requires OPENAI_API_KEY + Playwright)
pytest tests/test_task_execution_local.py -v
```

---

## 📁 Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, DB init
│   │   ├── config.py            # Pydantic Settings (loads .env by absolute path)
│   │   ├── api/routes/
│   │   │   ├── tasks.py         # Task CRUD + /start + /cancel + /logs
│   │   │   ├── results.py       # Results endpoints
│   │   │   └── websocket.py     # WS: Redis PubSub or DB polling fallback
│   │   ├── models/              # SQLAlchemy ORM (sqlalchemy.Uuid — SQLite safe)
│   │   ├── schemas/             # Pydantic v2 request/response schemas
│   │   ├── services/
│   │   │   ├── agent/           # loop.py, planner.py, evaluator.py, validator.py
│   │   │   ├── browser/         # controller.py, extractor.py, analyzer.py
│   │   │   └── memory/          # vector.py (FAISS, optional)
│   │   └── workers/
│   │       └── task_worker.py   # Redis queue consumer (production)
│   └── tests/
│       ├── test_validation_gpu.py        # 4 unit tests, no deps
│       └── test_task_execution_local.py  # Integration test
├── frontend/
│   └── src/
│       ├── app/                 # Next.js App Router pages
│       ├── components/          # ActionTimeline, AgentChatPanel, LiveBrowserPanel
│       ├── hooks/               # useTaskWebSocket.ts
│       └── lib/                 # api.ts (typed API client)
├── docker-compose.yml
└── DEVELOPER_ONBOARDING.md      # Full architecture & bug history
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/tasks` | Create a new task |
| `GET` | `/api/tasks/{id}` | Get task details & status |
| `POST` | `/api/tasks/{id}/start` | Start agent execution |
| `POST` | `/api/tasks/{id}/cancel` | Cancel running task |
| `GET` | `/api/tasks/{id}/logs` | Execution step-by-step logs |
| `GET` | `/api/tasks/{id}/results` | Extracted & validated results |
| `WS` | `/ws/tasks/{id}` | Real-time streaming updates |

**Create Task Example:**
```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"goal": "Find the cheapest RTX 4060 laptop on Amazon", "priority": 1}'

# Response:
# {"id": "a1b2c3d4-...", "status": "pending", "created_at": "2026-03-29T..."}
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14, React, Tailwind CSS, ShadCN |
| **Backend** | Python 3.13, FastAPI, SQLAlchemy (async), Pydantic v2 |
| **Browser** | Playwright (async headless Chromium) |
| **LLM** | OpenRouter (GPT-4o-mini via OpenAI-compatible API) |
| **Memory** | FAISS + `text-embedding-3-small` (optional, graceful fallback) |
| **Database** | SQLite (local dev) / PostgreSQL (production) |
| **Task Queue** | Redis + custom worker (auto-bypassed locally) |
| **Comms** | WebSocket (Redis PubSub or DB polling fallback) |
| **Containers** | Docker + Docker Compose |

---

## 🐛 Known Issues & Fixes Applied

24 bugs were found and resolved during development. Key fixes:

| # | Issue | Fix Applied |
|---|---|---|
| Database | `postgresql.UUID` type crashes SQLite | Switched to `sqlalchemy.Uuid` universally |
| Agent | HTML extraction overflowed LLM context | Switched to `innerText` for reliable parsing |
| Agent | Replanning executed old plan, not new one | Fixed agent loop to restart with new plan |
| WebSocket | `EventSource` caused reconnection loops & quota exhaustion | Replaced with `fetch` + `ReadableStream` |
| Config | `.env` loaded relative to CWD (picked up wrong file) | Now loads by `Path(__file__).parent.parent / ".env"` |
| Routing | Docker frontend got 404 on task creation | Fixed `NEXT_PUBLIC_API_URL` proxy routing |

See [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) for the complete bug history and architectural decisions.

---

## 📄 License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built with ❤️ by <a href="https://github.com/Akay-74">Akay-74</a></sub>
</div>
