# AI Web Automation Agent - Agent Guidelines

## Development Setup

### Backend (FastAPI)
- Use virtual environment: `cd backend && python3 -m venv venv && source venv/bin/activate`
- Install dependencies: `pip install -r requirements.txt`
- Install Playwright browsers: `playwright install chromium`
- Set environment variables: Create `backend/.env` with `OPENAI_API_KEY` and `OPENAI_BASE_URL` (loads from absolute path: `Path(__file__).parent.parent / ".env"`)
- Run locally: `uvicorn app.main:app --reload --port 8000`
- Backend uses SQLite locally (no Postgres/Redis needed for dev)

### Frontend (Next.js)
- Install dependencies: `cd frontend && npm install`
- Run development server: `npm run dev`
- Access at: http://localhost:3000
- Frontend uses Next.js 14 App Router
- If `npm run dev` fails with EACCES: run `sudo rm -rf frontend/.next` then `npm run dev` again (without sudo)

## Testing
- Backend unit tests: `cd backend && pytest tests/test_validation_gpu.py -v`
- Backend integration test: `cd backend && pytest tests/test_task_execution_local.py -v`
- Requires OPENAI_API_KEY and Playwright browsers installed
- Tests run with pytest; configuration in backend/pytest.ini

## Docker Production
- Set API key in backend/.env before building
- Start all services: `docker compose up --build`
- Services: postgres, redis, backend, worker, frontend
- System auto-detects Redis availability for distributed/local mode switching

## Important Notes
- LLM integration via OpenRouter API (OpenAI-compatible)
- The system has dual execution mode: when Redis is unreachable (local dev), it runs tasks in-process; when Redis is reachable (production), it uses distributed workers
- WebSocket connections use Redis PubSub when available, otherwise fall back to DB polling every 500ms
- Database uses sqlalchemy.Uuid type which works for both SQLite and PostgreSQL