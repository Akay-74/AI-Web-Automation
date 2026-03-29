# Developer Onboarding & Context Document

Welcome to the **AI Web Automation Agent Platform**. This document is the single source of truth for understanding the project, its architecture, all known bugs and fixes applied, and how to run everything locally.

---

## 1. Project Overview

A full-stack web platform where users type a natural language goal (e.g., *"Find the cheapest RTX 4060 laptop on Amazon"*) and an AI agent autonomously:
1. Creates a browser action plan (via OpenAI/OpenRouter LLM)
2. Controls a headless Chromium browser with Playwright
3. Extracts, validates, and ranks results against user constraints
4. Streams live status updates to the frontend via WebSocket

**Goal of the project:** Production-grade AI engineering demo. LLM cost is minimized — deterministic templates and rules are used first; LLM is only called when needed.

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Next.js 14, React, Tailwind CSS, ShadCN components |
| **Backend** | Python 3.13, FastAPI, SQLAlchemy (async), Pydantic v2 |
| **Browser Automation** | Playwright (async, headless Chromium) |
| **LLM** | OpenRouter API (OpenAI-compatible, key prefix `sk-or-v1-`) |
| **Embeddings / Memory** | FAISS + OpenAI `text-embedding-3-small` (optional, falls back gracefully) |
| **Database** | SQLite in local dev (via `aiosqlite`), PostgreSQL in production (via `asyncpg`) |
| **Task Queue** | Redis + `task_worker.py` in production; auto-bypassed locally |

---

## 3. Local Setup (The Only Mode You Need)

No Docker, no Postgres, no Redis required.

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# backend/.env (already configured):
# OPENAI_API_KEY=sk-or-v1-...
# OPENAI_BASE_URL=https://openrouter.ai/api/v1
# DATABASE_URL=sqlite:///./agent.db

uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev           # NO sudo — avoid it or .next gets root-owned
```
Frontend at **http://localhost:3000**, backend at **http://localhost:8000**.

> **If `npm run dev` fails with EACCES:** run `sudo rm -rf frontend/.next` then `npm run dev` again (without sudo).

---

## 4. File Structure

```
backend/
  app/
    main.py                  # FastAPI app, CORS, lifespan (DB init)
    config.py                # Pydantic Settings — loads backend/.env by absolute path
    api/routes/
      tasks.py               # CRUD + /start + /cancel + /logs endpoints
      results.py             # Read-only results endpoints
      websocket.py           # WS endpoint — Redis PubSub or DB polling fallback
    models/
      database.py            # SQLAlchemy engine — auto-detects SQLite vs Postgres
      task.py                # Task + TaskLog ORM models
      result.py              # Result ORM model
      user.py                # User ORM model
    schemas/
      task.py                # Pydantic request/response schemas
      result.py              # Result schemas
    services/
      agent/
        loop.py              # AgentLoop — main orchestrator
        planner.py           # AIPlanner — LLM plan + replan
        evaluator.py         # ResultEvaluator — deterministic + LLM eval
        validator.py         # ResultValidator — GPU/price/brand constraint checking
      browser/
        controller.py        # BrowserController — Playwright wrapper + retries
        extractor.py         # DataExtractor — CSS heuristic + LLM extraction
        analyzer.py          # PageAnalyzer — HTML → compressed text for memory
      memory/
        vector.py            # VectorMemory — FAISS embeddings (optional)
    workers/
      task_worker.py         # Redis queue worker (production only)
  tests/
    test_validation_gpu.py   # Unit tests for validator (4 tests, no deps)
    test_task_execution_local.py  # Integration test for background runner
frontend/
  src/                       # Next.js pages and components
  .env.local                 # NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

---

## 5. Dual Execution Mode (Critical)

The system auto-detects its environment and adapts:

```
POST /api/tasks/{id}/start
    ↓
Is Redis reachable?
    YES → rpush("task_queue", task_id)   ← worker picks it up
    NO  → asyncio.create_task(_run_agent_background())  ← runs in-process
```

The WebSocket endpoint also adapts:
```
GET /ws/tasks/{id}
    ↓
Is Redis reachable?
    YES → subscribe to "task_updates:{id}" PubSub channel
    NO  → poll DB every 500ms for new TaskLog rows + task status
```

---

## 6. Database Model — UUID Handling (Bug History)

**Critical**: All ORM models MUST use `sqlalchemy.Uuid` (not `sqlalchemy.dialects.postgresql.UUID`). The PostgreSQL dialect UUID type crashes on SQLite.

Everywhere a `task_id` string comes from a URL path or is passed around as `str`, it must be coerced before DB queries:
```python
import uuid
task_uuid = uuid.UUID(task_id) if isinstance(task_id, str) else task_id
# Then: select(Task).where(Task.id == task_uuid)
```

FastAPI path parameters with `task_id: uuid.UUID` handle this automatically.

---

## 7. Agent Loop — How It Works

```
AgentLoop.run()
  1. AIPlanner.create_plan(goal)
       → matches deterministic template first (amazon/google)
       → falls back to LLM (gpt-4o-mini via OpenRouter)
  2. BrowserController.launch()  [headless=True]
  3. For each plan step:
       a. BrowserController.execute(step)  [navigate/click/type/scroll/extract/wait]
       b. Screenshot → Redis publish (silently skipped if Redis unavailable)
       c. If navigate/click/scroll: PageAnalyzer → VectorMemory.store()
       d. If extract: DataExtractor.extract() → ResultValidator.validate_all()
            → If 0 valid items + replan budget: AIPlanner.replan() and restart loop
       e. If evaluate: ResultEvaluator.evaluate()
            → deterministic check first (3+ results = done)
            → LLM check only if inconclusive
  4. Browser closed
  5. Return final {results, valid_results, summary, status}
```

---

## 8. Validation Layer

`ResultValidator` (in `validator.py`) parses constraints from the goal text:
- **GPU**: regex matches `RTX 4060`, `GTX 1660`, etc.
- **Price cap**: matches `under $1000`
- **Brand**: keyword list (asus, msi, gigabyte, etc.)

Each extracted item gets a `validation_reason` string and `is_valid` flag.

`GPU_REJECT_TOKENS` list — these GPUs will mark an item as invalid when searching for a different GPU:
```python
"RTX 3050", "RTX 3060", ..., "RTX 4050", "RTX 4070", ..., "Intel UHD", ...
```

---

## 9. LLM API Configuration

**Important**: The project uses **OpenRouter** (not OpenAI directly). The key starts with `sk-or-v1-`.

`backend/.env` must contain:
```
OPENAI_API_KEY=sk-or-v1-...      # OpenRouter key
OPENAI_BASE_URL=https://openrouter.ai/api/v1
```

The `OPENAI_BASE_URL` in `config.py` defaults to `https://api.openai.com/v1` — it is **overridden by `backend/.env`**.

---

## 10. All Bugs Fixed (Session History)

| # | File | Bug | Fix |
|---|------|-----|-----|
| 1–3 | `models/{task,result,user}.py` | `postgresql.UUID` crashes SQLite on startup | Switched to `sqlalchemy.Uuid` |
| 4 | `browser/controller.py` | `headless=False` opens visible browser | Changed to `headless=True` |
| 5 | `config.py` | `openai_model = "openai/gpt-4o-mini"` (bad prefix) | Fixed to `"gpt-4o-mini"` |
| 6 | `agent/loop.py` | `settings.__dict__.get("default_replan_attempts")` | Direct attribute access |
| 7 | `agent/evaluator.py` | Hardcoded `model="gpt-4o-mini"` (ignores settings) | Uses `self.model` from settings |
| 8 | `agent/validator.py` | Missing `"RTX 4050"` in GPU_REJECT_TOKENS | Added |
| 9 | `api/routes/tasks.py` | No `db.commit()` after `create_task` | Added explicit commit |
| 10 | `api/routes/tasks.py` | All route `task_id: str` → SQLAlchemy `Uuid` crash | Changed to `task_id: uuid.UUID` |
| 11 | `api/routes/tasks.py` | `_run_agent_background` uses `task_id` str in DB queries | Added `uuid.UUID(task_id)` coercion |
| 12 | `api/routes/tasks.py` | `TaskLog(task_id=task_id)` str in ORM constructor | Changed to `task_uuid` |
| 13 | `api/routes/tasks.py` | `Result(task_id=task_id)` str in ORM constructor | Changed to `task_uuid` |
| 14 | `api/routes/websocket.py` | Redis-only WebSocket (hangs in local mode) | Dual-mode: Redis or DB polling |
| 15 | `api/routes/websocket.py` | Polling uses `task_id` str in DB queries | Added `uuid.UUID(task_id)` coercion |
| 16 | `agent/loop.py` | Screenshot logs noisy Redis errors in local mode | Silenced connection errors at debug level |
| 17 | `config.py` | Loaded `.env` relative to cwd (could pick up root .env with PostgreSQL URL) | Now loads by absolute path (`Path(__file__).parent.parent / ".env"`) |
| 18 | `backend/.env` | Missing `OPENAI_BASE_URL` — OpenRouter key rejected by OpenAI endpoint | Added `OPENAI_BASE_URL=https://openrouter.ai/api/v1` |
| 19 | `tests/test_task_execution_local.py` | `Task.id == task_id` str type mismatch | Changed to `Task.id == t.id` UUID |
| 20 | `browser/extractor.py` | LLM context limit exceeded from raw HTML extraction | Switched to inner text extraction for reliable LLM parsing |
| 21 | `agent/loop.py` | Agent fails to execute new plan after replanning | Fixed loop logic to correctly restart execution with the new plan |
| 22 | `api/routes/websocket.py` & Frontend | Reconnection loop causing API quota exhaustion | Replaced frontend `EventSource` with `fetch` / `ReadableStream` |
| 23 | `agent/loop.py` | Task completion events missing on frontend | Fixed task status broadcasting on task finish to emit final State |
| 24 | `docker-compose.yml` / `.env` | 404 error creating tasks via Docker UI | Fixed API URL routing proxy settings for frontend-to-backend communication |

---

## 11. Running Tests

```bash
cd backend
source venv/bin/activate

# Validation unit tests (no network, fast)
pytest tests/test_validation_gpu.py -v
# Expected: 4 passed

# Integration test (needs valid OPENAI_API_KEY + Playwright)
pytest tests/test_task_execution_local.py -v
```

---

## 12. Production (Docker) Mode

Only use when you need the full distributed stack. Keep Docker files for this.

```bash
# Ensure backend/.env has OPENAI_API_KEY
docker compose up --build
```

Services launched: `postgres`, `redis`, `backend` (API), `worker` (task_worker.py), `frontend`.

The code auto-switches between local and production mode — no manual flag needed.
