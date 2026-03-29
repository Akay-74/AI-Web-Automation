# AI Web Automation Agent

A full-stack web platform where users provide a goal in natural language (e.g., "Find the cheapest RTX 4060 laptop on Amazon"), and an AI agent autonomously controls a headless browser to complete the task, extract data, validate results against constraints, and return structured UI outputs.

## Features

- **Autonomous Browsing:** Uses Playwright to navigate, type, click, scroll, and wait.
- **Natural Language Parsing:** LLMs evaluate what step to take next.
- **Exact Match Validation:** Enforces requirements (e.g., "Must be an RTX 4060", "Must be Asus brand").
- **Dynamic Replanning:** Senses if constraints aren't met and tries again automatically.
- **Data Extraction:** Intelligently parses inner text from websites to maintain robust LLM context limits.
- **Live Browser View:** See exactly what the agent sees through a WebSocket snapshot stream.
- **Real-time Status Updates:** Watch the AI narrate its progress in real-time seamlessly.

---

## 🛠 Recent Stabilization & Updates

We recently overhauled the project to ensure maximum stability and reliability across both local and production environments:

- **Local SQLite Mode:** Fully decoupled from Docker/PostgreSQL/Redis dependencies for seamless local development.
- **Database UUID Fixes:** Resolved serialization (`PendingRollbackError`) issues between SQLite and PostgreSQL Uuid types.
- **Agent Logic Enhancements:** Switched HTML parsing to inner text to optimize LLM context usage, and fixed execution flow to ensure the agent correctly follows new schedules after replanning.
- **Frontend Networking:** Resolved WebSocket reconnection loops (switched to `fetch`/`ReadableStream`) and correctly configured Docker API proxy routing to fix `404` errors.
- **Task Broadcasting:** Fixed state broadcasting so the frontend accurately reflects task completion events in real-time.

---

## 🚀 Quickstart: Local Mode (SQLite / No Docker)

The easiest way to run the application for development.

### 1. Backend

Open a terminal session:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate

# Install all backend requirements
pip install -r requirements.txt
pip install pytest pytest-asyncio

# Required for the agent to navigate
playwright install chromium

# Create a local .env file
echo 'OPENAI_API_KEY=sk-your-key-here' > .env
echo 'DATABASE_URL=sqlite:///./agent.db' >> .env

# Run the API Server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

Open a new terminal session:
```bash
cd frontend
npm install
npm run dev
```

Visit **http://localhost:3000** to use the application.

---

## 🐳 Production: Docker Compose (Postgres + Redis)

To run the full stack with dedicated task queues and distributed workers:

1. Add your `OPENAI_API_KEY` to `backend/.env`.
2. Run `docker compose up --build`.

The system automatically switches seamlessly between the local FastAPI background runner and the Redis task queue worker depending on service availability.
