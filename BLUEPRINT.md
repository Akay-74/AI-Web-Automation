# AI Web Automation Agent Platform — Engineering Blueprint

> A production-grade full-stack platform where users give a goal in natural language and an AI agent autonomously operates a browser to complete the task.

---

## 1. PROJECT OVERVIEW

This platform demonstrates mastery of **AI engineering, agent architecture, browser automation, full-stack web development, scalable backend systems, and distributed workers**.

Users submit natural-language goals like *"Find the cheapest RTX 4060 laptop on Amazon"*. An AI agent then:

1. **Interprets** the goal via GPT-4o-mini
2. **Plans** a step-by-step action sequence
3. **Controls** a headless Chromium browser via Playwright
4. **Navigates** websites, clicks, types, scrolls
5. **Extracts** structured data from pages
6. **Evaluates** results against the original goal
7. **Returns** a final answer to the user dashboard in real-time

### Why This Project Is Impressive

| Skill Area | Demonstrated By |
|---|---|
| AI Engineering | Agent loop, prompt design, cost optimization |
| System Design | Distributed workers, queue system, memory layer |
| Full-Stack Dev | Next.js frontend + FastAPI backend + WebSockets |
| Browser Automation | Playwright controller with error recovery |
| Data Engineering | Structured extraction pipelines |
| DevOps | Docker, CI/CD, observability |

---

## 2. SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js)                          │
│  ┌──────────┐ ┌───────────────┐ ┌──────────┐ ┌───────────────────┐│
│  │Task Form │ │Agent Monitor  │ │Results   │ │ Task History      ││
│  │          │ │(WebSocket)    │ │Dashboard │ │                   ││
│  └────┬─────┘ └───────┬───────┘ └────┬─────┘ └───────────────────┘│
└───────┼───────────────┼──────────────┼────────────────────────────┘
        │               │              │
        ▼               ▼              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                              │
│  ┌──────────┐ ┌───────────────┐ ┌──────────────┐ ┌──────────────┐ │
│  │REST API  │ │WebSocket Hub  │ │Task Manager  │ │Auth Module   │ │
│  └────┬─────┘ └───────┬───────┘ └──────┬───────┘ └──────────────┘ │
└───────┼───────────────┼────────────────┼──────────────────────────┘
        │               │                │
        ▼               ▼                ▼
┌───────────────┐ ┌──────────────┐ ┌──────────────────────────────────┐
│  PostgreSQL   │ │    Redis     │ │        WORKER SYSTEM             │
│  ┌──────────┐ │ │  ┌────────┐  │ │  ┌──────────────────────────┐   │
│  │users     │ │ │  │task    │  │ │  │     AGENT LOOP           │   │
│  │tasks     │ │ │  │queue   │  │ │  │  ┌────────┐ ┌─────────┐ │   │
│  │task_logs │ │ │  │pubsub  │  │ │  │  │Planner │→│Executor │ │   │
│  │results   │ │ │  └────────┘  │ │  │  └────────┘ └────┬────┘ │   │
│  │workflows │ │ │              │ │  │                   │      │   │
│  └──────────┘ │ │              │ │  │  ┌────────────────▼────┐ │   │
└───────────────┘ └──────────────┘ │  │  │Browser Controller   │ │   │
                                   │  │  │(Playwright)         │ │   │
┌───────────────┐                  │  │  └─────────┬───────────┘ │   │
│ Vector Memory │                  │  │            │             │   │
│ (FAISS)       │◄─────────────────│  │  ┌─────────▼───────────┐ │   │
│ ┌───────────┐ │                  │  │  │Page Analyzer +      │ │   │
│ │page embeds│ │                  │  │  │Data Extractor       │ │   │
│ │task ctx   │ │                  │  │  └─────────┬───────────┘ │   │
│ └───────────┘ │                  │  │            │             │   │
└───────────────┘                  │  │  ┌─────────▼───────────┐ │   │
                                   │  │  │Result Evaluator     │ │   │
                                   │  │  └─────────────────────┘ │   │
                                   │  └──────────────────────────┘   │
                                   └──────────────────────────────────┘
```

### Data Flow

1. User submits task via **REST API**
2. Backend enqueues task in **Redis**
3. **Worker** picks up task, starts **Agent Loop**
4. Agent calls **GPT-4o-mini** for planning (1 call)
5. Agent executes steps via **Playwright Browser Controller**
6. **Page Analyzer** extracts content; embeddings stored in **FAISS**
7. Each step logged to **PostgreSQL** and broadcast via **WebSocket**
8. **Result Evaluator** checks completion; returns structured result

---

## 3. CORE COMPONENTS

### 3.1 Task Manager
Owns the task lifecycle: `PENDING → RUNNING → COMPLETED / FAILED`. Persists state to PostgreSQL, publishes state changes to Redis PubSub for WebSocket broadcast.

### 3.2 AI Planner
Makes a **single** GPT-4o-mini call to decompose the user goal into a JSON action plan. Uses deterministic templates for common tasks (search, extract, compare) to minimize token usage.

### 3.3 Agent Loop
The core orchestrator. Iterates through the plan, dispatching actions to the Browser Controller, checking results via the Evaluator, and only calling the LLM again if the plan needs revision.

### 3.4 Browser Controller
Wraps Playwright to provide high-level actions: `navigate(url)`, `click(selector)`, `type(selector, text)`, `scroll()`, `screenshot()`, `extract_content()`. Handles retries, timeouts, and anti-bot mitigations.

### 3.5 Page Analyzer
Converts raw HTML into a simplified DOM representation. Strips scripts/styles, extracts visible text, identifies interactive elements, and creates a compressed page summary for the LLM.

### 3.6 Data Extractor
Converts page content into structured JSON using extraction schemas (product, job, article). Uses CSS selectors first (deterministic), falls back to LLM extraction only when needed.

### 3.7 Vector Memory (FAISS)
Stores embeddings of visited pages and extracted data. Enables the agent to recall previously visited content without re-browsing, reducing both time and API costs.

### 3.8 Result Evaluator
Checks whether the extracted data satisfies the original goal. Uses deterministic checks first (e.g., "do we have ≥5 results with price fields?"), then a lightweight LLM verification if needed.

---

## 4. AGENT WORKFLOW

```
User Goal
    │
    ▼
┌──────────────┐
│  AI Planner  │──── GPT-4o-mini: decompose goal → action plan (1 API call)
└──────┬───────┘
       │ action_plan = [{action, params}, ...]
       ▼
┌──────────────────────────────────────────┐
│            AGENT LOOP                     │
│                                          │
│  for step in action_plan:                │
│    ┌─────────────────────────────┐       │
│    │ Browser Controller          │       │
│    │  execute(step.action,       │       │
│    │         step.params)        │       │
│    └────────────┬────────────────┘       │
│                 │                        │
│    ┌────────────▼────────────────┐       │
│    │ Page Analyzer               │       │
│    │  content = analyze(page)    │       │
│    └────────────┬────────────────┘       │
│                 │                        │
│    ┌────────────▼────────────────┐       │
│    │ Data Extractor              │       │
│    │  data = extract(content)    │       │
│    └────────────┬────────────────┘       │
│                 │                        │
│    ┌────────────▼────────────────┐       │
│    │ Memory: store embedding     │       │
│    └────────────┬────────────────┘       │
│                 │                        │
│    ┌────────────▼────────────────┐       │
│    │ Result Evaluator            │       │
│    │  if goal_met: break         │       │
│    │  if stuck: replan (LLM)     │       │
│    └─────────────────────────────┘       │
│                                          │
└──────────────────────────────────────────┘
       │
       ▼
  Final Structured Result → DB + WebSocket → Dashboard
```

### Agent Loop Pseudocode

```python
async def run_agent(task: Task):
    # Phase 1: Plan (single LLM call)
    plan = await planner.create_plan(task.goal)
    log_step(task.id, "plan_created", plan)

    browser = await BrowserController.launch()
    memory = VectorMemory(task.id)

    for i, step in enumerate(plan.steps):
        try:
            # Phase 2: Execute browser action
            page_state = await browser.execute(step)

            # Phase 3: Analyze page
            content = await page_analyzer.analyze(page_state)
            memory.store(content)

            # Phase 4: Extract data if needed
            if step.expects_data:
                data = await extractor.extract(content, step.schema)
                task.add_results(data)

            # Phase 5: Evaluate progress
            evaluation = evaluator.check(task.goal, task.results)
            log_step(task.id, f"step_{i}", evaluation)
            broadcast_update(task.id, evaluation)

            if evaluation.goal_met:
                break
            if evaluation.needs_replan:
                plan = await planner.replan(task.goal, memory.context())

        except BrowserError as e:
            await handle_error(browser, e)

    await browser.close()
    task.complete(task.results)
```

---

## 5. BROWSER AUTOMATION DESIGN

### Playwright Architecture

```python
class BrowserController:
    """High-level browser control wrapping Playwright."""

    async def launch(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 ..."
        )
        self.page = await self.context.new_page()

    async def navigate(self, url: str):
        await self.page.goto(url, wait_until="domcontentloaded", timeout=30000)

    async def click(self, selector: str):
        await self.page.wait_for_selector(selector, timeout=10000)
        await self.page.click(selector)

    async def type_text(self, selector: str, text: str):
        await self.page.fill(selector, text)

    async def scroll_down(self):
        await self.page.evaluate("window.scrollBy(0, window.innerHeight)")

    async def extract_content(self) -> str:
        return await self.page.evaluate("document.body.innerText")

    async def screenshot(self) -> bytes:
        return await self.page.screenshot()

    async def get_interactive_elements(self) -> list:
        """Extract clickable/typable elements for the agent."""
        return await self.page.evaluate("""() => {
            const elements = document.querySelectorAll('a, button, input, select, textarea');
            return Array.from(elements).map((el, i) => ({
                index: i,
                tag: el.tagName,
                text: el.innerText?.slice(0, 100),
                placeholder: el.placeholder,
                selector: el.id ? '#' + el.id : null
            }));
        }""")
```

### Handling Challenges

| Challenge | Strategy |
|---|---|
| Dynamic content | `wait_for_selector()` + retry with exponential backoff |
| Pagination | Detect "next" buttons, loop with max page limit |
| CAPTCHAs | Detect CAPTCHA elements, pause task, notify user |
| Anti-bot | Rotate user agents, add random delays, stealth mode |
| Infinite scroll | Scroll + wait + detect no-new-content condition |
| Login walls | Detect login forms, use stored credentials or skip |

---

## 6. DATA EXTRACTION SYSTEM

### Extraction Pipeline

```
Raw HTML → Clean HTML → Simplified DOM → Schema Matching → Structured JSON
```

### Extraction Schemas

```python
PRODUCT_SCHEMA = {
    "name": "string",
    "price": "float",
    "currency": "string",
    "rating": "float",
    "url": "string",
    "image_url": "string",
    "specs": "dict"
}

JOB_SCHEMA = {
    "title": "string",
    "company": "string",
    "location": "string",
    "salary_range": "string",
    "url": "string",
    "posted_date": "string"
}

ARTICLE_SCHEMA = {
    "title": "string",
    "source": "string",
    "summary": "string",
    "url": "string",
    "published_date": "string"
}
```

### Example Output

```json
{
  "type": "product_comparison",
  "items": [
    {
      "name": "ASUS TUF Gaming A15 RTX 4060",
      "price": 899.99,
      "currency": "USD",
      "rating": 4.5,
      "url": "https://amazon.com/dp/...",
      "specs": {"ram": "16GB", "storage": "512GB SSD", "display": "15.6\" 144Hz"}
    }
  ],
  "summary": "Found 8 RTX 4060 laptops. Cheapest: ASUS TUF at $899.99"
}
```

---

## 7. VECTOR MEMORY SYSTEM

### Architecture

```
Page Content → text-embedding-3-small → FAISS Index
                                            │
                    Query ─────────────────►│
                                            │
                              Top-K Results ◄┘
```

### Implementation

```python
class VectorMemory:
    def __init__(self, task_id: str):
        self.index = faiss.IndexFlatIP(1536)  # cosine similarity
        self.documents = []

    async def store(self, content: str, metadata: dict):
        embedding = await get_embedding(content[:8000])  # truncate for cost
        self.index.add(np.array([embedding], dtype="float32"))
        self.documents.append({"content": content, "metadata": metadata})

    async def retrieve(self, query: str, top_k: int = 3) -> list:
        query_emb = await get_embedding(query)
        scores, indices = self.index.search(
            np.array([query_emb], dtype="float32"), top_k
        )
        return [self.documents[i] for i in indices[0] if i < len(self.documents)]
```

### Cost Optimization
- Uses `text-embedding-3-small` ($0.02/1M tokens) — negligible cost
- Content truncated to 8000 chars before embedding
- Only stores unique page snapshots (dedup by URL + content hash)

---

## 8. DATABASE DESIGN

```sql
-- Users table
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Tasks table
CREATE TABLE tasks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    goal        TEXT NOT NULL,
    status      VARCHAR(20) DEFAULT 'pending',  -- pending/running/completed/failed
    priority    INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT NOW(),
    started_at  TIMESTAMP,
    completed_at TIMESTAMP
);

-- Task execution logs
CREATE TABLE task_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id     UUID REFERENCES tasks(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    action      VARCHAR(100),
    details     JSONB,
    screenshot  TEXT,              -- base64 or S3 URL
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Extracted results
CREATE TABLE results (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id     UUID REFERENCES tasks(id) ON DELETE CASCADE,
    data_type   VARCHAR(50),       -- product/job/article
    data        JSONB NOT NULL,
    summary     TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Reusable workflows
CREATE TABLE workflows (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id),
    name        VARCHAR(255),
    description TEXT,
    steps       JSONB NOT NULL,    -- template action plan
    created_at  TIMESTAMP DEFAULT NOW()
);
```

---

## 9. API DESIGN

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/tasks` | Create a new task |
| GET | `/api/tasks/{id}` | Get task details |
| GET | `/api/tasks` | List user tasks |
| POST | `/api/tasks/{id}/start` | Start agent execution |
| POST | `/api/tasks/{id}/cancel` | Cancel running task |
| GET | `/api/tasks/{id}/logs` | Get execution logs |
| GET | `/api/tasks/{id}/results` | Get extracted results |
| WS | `/ws/tasks/{id}` | Live execution updates |

### Example: Create Task

**Request:**
```json
POST /api/tasks
{
  "goal": "Find the cheapest RTX 4060 laptop on Amazon",
  "priority": 1
}
```

**Response:**
```json
{
  "id": "a1b2c3d4-...",
  "goal": "Find the cheapest RTX 4060 laptop on Amazon",
  "status": "pending",
  "created_at": "2026-03-11T12:00:00Z"
}
```

### Example: Task Logs

```json
GET /api/tasks/a1b2c3d4-.../logs
{
  "logs": [
    {"step": 1, "action": "navigate", "details": {"url": "https://amazon.com"}, "timestamp": "..."},
    {"step": 2, "action": "type", "details": {"selector": "#search", "text": "RTX 4060 laptop"}, "timestamp": "..."},
    {"step": 3, "action": "click", "details": {"selector": "#search-btn"}, "timestamp": "..."},
    {"step": 4, "action": "extract", "details": {"items_found": 12}, "timestamp": "..."}
  ]
}
```

---

## 10. FRONTEND ARCHITECTURE

### Pages

| Page | Route | Purpose |
|---|---|---|
| Dashboard | `/` | Overview, recent tasks |
| New Task | `/tasks/new` | Natural language input |
| Agent Monitor | `/tasks/[id]` | Live execution view |
| Results | `/tasks/[id]/results` | Structured data display |
| History | `/history` | All past tasks |

### Component Tree

```
App
├── Layout (Sidebar + Header)
├── TaskCreationForm
│   ├── GoalInput (textarea)
│   ├── PrioritySelector
│   └── SubmitButton
├── AgentMonitor
│   ├── StepTimeline (live via WebSocket)
│   ├── BrowserPreview (screenshots)
│   ├── LogStream
│   └── ProgressBar
├── ResultsView
│   ├── DataTable (products/jobs/articles)
│   ├── SummaryCard
│   └── ExportButton (CSV/JSON)
└── TaskHistory
    ├── TaskList
    ├── FilterBar
    └── TaskCard
```

### State Management
- **React Query** for server state (tasks, results, logs)
- **WebSocket context** for real-time updates
- **URL state** for filters and pagination

---

## 11. ERROR HANDLING

| Error | Detection | Recovery |
|---|---|---|
| Page load failure | Timeout after 30s | Retry 3x, then mark step failed |
| CAPTCHA | Detect CAPTCHA elements | Pause, notify user, skip site |
| Element not found | Selector timeout | Try alternative selectors, re-analyze page |
| Infinite loop | Step counter > max_steps | Force break, return partial results |
| Rate limiting | HTTP 429 response | Exponential backoff, rotate approach |
| Browser crash | Process exit signal | Restart browser, resume from last checkpoint |
| LLM API error | API exception | Retry with backoff, fallback to cached plan |

---

## 12. TESTING STRATEGY

### Test Pyramid

```
         ┌──────────┐
         │  E2E     │  — Full agent runs on test sites
         ├──────────┤
         │Integration│ — API + DB + Redis
         ├──────────┤
         │  Unit    │  — Individual components
         └──────────┘
```

### Example Test Cases

```python
# Unit: Planner
def test_planner_creates_valid_plan():
    plan = planner.create_plan("Find cheapest laptop on Amazon")
    assert plan.steps[0].action == "navigate"
    assert "amazon" in plan.steps[0].params["url"]

# Unit: Extractor
def test_extract_product_from_html():
    html = load_fixture("amazon_product_page.html")
    products = extractor.extract(html, PRODUCT_SCHEMA)
    assert len(products) > 0
    assert all(p["price"] > 0 for p in products)

# Integration: Agent loop with mock browser
async def test_agent_completes_search_task():
    task = Task(goal="Find RTX 4060 laptops")
    result = await run_agent(task, browser=MockBrowser())
    assert result.status == "completed"
    assert len(result.data) > 0

# E2E: Browser automation
async def test_browser_navigates_and_extracts():
    controller = BrowserController()
    await controller.launch()
    await controller.navigate("https://example.com")
    content = await controller.extract_content()
    assert "Example Domain" in content
```

---

## 13. DEVELOPMENT ROADMAP

| Phase | Duration | Deliverables |
|---|---|---|
| **1. Foundation** | Week 1-2 | FastAPI skeleton, DB models, Redis setup, Docker |
| **2. Agent Core** | Week 3-4 | Planner, agent loop, memory system |
| **3. Browser** | Week 5-6 | Playwright controller, page analyzer, extractors |
| **4. Frontend** | Week 7-8 | Next.js dashboard, WebSocket live updates |
| **5. Polish** | Week 9-10 | Testing, error handling, deployment, observability |

---

## 14. REPOSITORY STRUCTURE

```
ai-web-automation-agent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── tasks.py     # Task CRUD
│   │   │   │   ├── results.py   # Results endpoints
│   │   │   │   └── websocket.py # WS handler
│   │   ├── models/
│   │   │   ├── database.py      # DB connection
│   │   │   ├── task.py          # Task model
│   │   │   ├── result.py        # Result model
│   │   │   └── user.py          # User model
│   │   ├── schemas/
│   │   │   ├── task.py          # Pydantic schemas
│   │   │   └── result.py
│   │   ├── services/
│   │   │   ├── agent/
│   │   │   │   ├── loop.py      # Agent loop
│   │   │   │   ├── planner.py   # AI planner
│   │   │   │   └── evaluator.py # Result evaluator
│   │   │   ├── browser/
│   │   │   │   ├── controller.py # Playwright wrapper
│   │   │   │   ├── analyzer.py  # Page analyzer
│   │   │   │   └── extractor.py # Data extractor
│   │   │   └── memory/
│   │   │       └── vector.py    # FAISS memory
│   │   └── workers/
│   │       └── task_worker.py   # Redis worker
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic/                 # DB migrations
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js app router
│   │   ├── components/          # React components
│   │   ├── lib/                 # Utilities
│   │   └── hooks/               # Custom hooks
│   ├── package.json
│   ├── Dockerfile
│   └── tailwind.config.ts
├── docker-compose.yml
├── .env.example
├── README.md
└── BLUEPRINT.md
```

---

## 15. DEPLOYMENT STRATEGY

### Docker Compose (Development)
```yaml
services:
  backend:   # FastAPI + Uvicorn
  worker:    # Agent worker processes
  frontend:  # Next.js
  postgres:  # Database
  redis:     # Queue + PubSub
```

### Production Deployment
- **Backend**: AWS ECS / Railway / Fly.io
- **Frontend**: Vercel
- **Database**: AWS RDS / Supabase
- **Redis**: AWS ElastiCache / Upstash
- **CI/CD**: GitHub Actions → Docker build → deploy

---

## 16. SCALABILITY PLAN

| Component | Scaling Strategy |
|---|---|
| Backend API | Horizontal scaling behind load balancer |
| Workers | Scale worker count independently based on queue depth |
| Browser instances | One browser per worker, pool management |
| Database | Read replicas, connection pooling (pgbouncer) |
| Redis | Redis Cluster for high throughput |
| Memory (FAISS) | Per-task indices, archived to disk after completion |

---

## 17. SECURITY CONSIDERATIONS

- **Authentication**: JWT tokens with refresh rotation
- **Rate Limiting**: Per-user task limits (e.g., 50 tasks/day on free tier)
- **Input Sanitization**: Validate and sanitize all user goals
- **Browser Isolation**: Each task runs in isolated browser context
- **API Protection**: CORS, CSRF, request validation
- **Secrets Management**: Environment variables, never committed
- **Abuse Prevention**: Block malicious URLs, limit browsing domains optionally

---

## 18. OBSERVABILITY

| Layer | Tool | Purpose |
|---|---|---|
| Logging | Structlog | Structured JSON logs |
| Metrics | Prometheus | Task counts, durations, API latency |
| Monitoring | Grafana | Dashboards and alerts |
| Error Tracking | Sentry | Exception capture and alerting |
| Tracing | OpenTelemetry | Distributed trace across services |

---

## 19. ADVANCED FEATURES

1. **Scheduled Tasks** — Run tasks on a cron schedule (e.g., daily price monitoring)
2. **Workflow Templates** — Save and reuse action plans as templates
3. **Multi-Tab Browsing** — Open multiple tabs in parallel for comparison tasks
4. **Screenshot Timeline** — Visual replay of the agent's browsing session
5. **Collaborative Tasks** — Share task results with team members
6. **Natural Language Refinement** — User can guide the agent mid-execution
7. **Cost Dashboard** — Show per-task token usage and cost breakdown
8. **Browser Recording** — Record and replay browser sessions as video
9. **API Integration** — Expose agent as an API for programmatic access
10. **Plugin System** — Custom extractors for specific websites

---

## 20. RESUME VALUE

This project demonstrates:

- **AI Engineering**: Designing and implementing autonomous AI agents with LLM integration, prompt optimization, and cost-efficient architectures
- **Systems Design**: Building distributed systems with message queues, worker pools, and real-time communication
- **Full-Stack Development**: Production-grade frontend (Next.js/React) + backend (FastAPI) with WebSocket integration
- **Browser Automation**: Advanced Playwright usage with error recovery, anti-detection, and structured data extraction
- **Data Engineering**: Building extraction pipelines that convert unstructured web data into structured datasets
- **DevOps**: Docker containerization, CI/CD pipelines, observability stack
- **Cost Optimization**: Designing AI systems that minimize API costs while maintaining quality

> This is the kind of project that shows you can build **real AI products**, not just call APIs.
