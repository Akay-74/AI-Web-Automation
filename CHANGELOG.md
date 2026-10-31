# Changelog

All notable changes to the AI Web Automation Agent project will be documented in this file.

## [Unreleased]

### Added
- **Optional API key**: set `API_KEY` in `backend/.env` to require `X-API-Key` on `/api/*` and `?api_key=` on the task WebSocket (`backend/app/api/auth.py`). Off by default for local development; the frontend sends `NEXT_PUBLIC_API_KEY`.
- **CI**: GitHub Actions runs the backend pytest suite and a frontend typecheck plus production build on every push and pull request.

### Removed
- **Third-party CAPTCHA solving**: the 2Captcha integration and `CAPTCHA_API_KEY` are gone. A detected CAPTCHA now always hands the live browser to the human.

### Fixed
- `next build` failed to prerender `/tasks/new` because `useSearchParams()` had no Suspense boundary.

- **Validation Layer**: Introduced `backend/app/services/agent/validator.py` to parse constraints (GPU model, brand, price limit) from user goals and deterministically validate extracted items, appending a `validation_reason` string.
- **Backend Task Execution Fallback**: Added `_run_agent_background` in `backend/app/api/routes/tasks.py` that bypasses Redis and runs the `AgentLoop` as a FastAPI background task if Redis is unreachable (ideal for local SQLite dev).
- **Frontend UI Redesign**: 
  - `AgentChatPanel.tsx` created to format `ui_event` broadcasts into a chat-like messaging interface.
  - `ActionTimeline.tsx` created to show standard `raw_event` steps.
  - `LiveBrowserPanel.tsx` isolated for displaying real-time Chromium screenshots.
  - `ProductCard.tsx` designed to beautifully render extracted item specs (GPU, RAM, etc.) and validation reasons.
- **Replan Logic**: `AgentLoop` in `backend/app/services/agent/loop.py` automatically replans up to `default_replan_attempts` (2) if zero items match the strict validation criteria.
- **Testing**: Added Pytest config and two integration test scripts for the GPU validation logic and the local fallback route.

### Changed
- **WebSockets / Logging**: The `AgentLoop` method `_broadcast` now sends two simultaneous events per action: `raw_event` (original JSON payload) and `ui_event` (human-readable mapped string).
- **Playwright Stability**: In `backend/app/services/browser/controller.py`, `headless` changed to `False` for visible tracking, `timeout` increased to 30,000ms, wait strategies updated to `networkidle`, and an exponential-backoff retry helper added for all critical DOM interactions.
- **Extraction schemas**: Updated `backend/app/services/browser/extractor.py` to explicitly request specific hardware elements like `gpu`, `cpu`, `ram`, `storage`, and `validation_reason` from the LLM.

### Fixed
- Fixed an issue where tasks would report "Waiting for agent to start..." on single-machine environments without Redis.
- Fixed a bug in `_generate_summary` crashing on string-to-float price comparisons.
