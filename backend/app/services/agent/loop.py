"""Agent Loop — Central orchestrator for browser automation tasks.

Executes plan steps, captures screenshots, validates results, evaluates
completion, and broadcasts both raw events and human-friendly UI events.
"""

import base64
import json
import re
from datetime import datetime
from typing import Optional, Callable, Awaitable

import redis.asyncio as aioredis
import structlog

from app.config import get_settings
from app.services.agent.planner import AIPlanner
from app.services.agent.evaluator import ResultEvaluator
from app.services.agent.validator import ResultValidator
from app.services.browser.controller import BrowserController
from app.services.browser.analyzer import PageAnalyzer
from app.services.browser.extractor import DataExtractor
from app.services.memory.vector import VectorMemory

logger = structlog.get_logger()

# Human-readable action labels
_ACTION_LABELS = {
    "navigate": "Opening",
    "type": "Typing",
    "click": "Clicking",
    "scroll": "Scrolling the page",
    "extract": "Extracting data",
    "evaluate": "Evaluating results",
    "validate": "Validating results",
    "wait": "Waiting",
}


class AgentLoop:
    """Runs a complete browser automation task."""

    def __init__(
        self,
        task_id: str,
        goal: str,
        on_step: Optional[Callable[[dict], Awaitable[None]]] = None,
    ):
        self.task_id = task_id
        self.goal = goal
        self.on_step = on_step
        self.settings = get_settings()

        self.planner = AIPlanner()
        self.evaluator = ResultEvaluator()
        self.validator = ResultValidator(goal)
        self.browser = BrowserController()
        self.analyzer = PageAnalyzer()
        self.extractor = DataExtractor()
        self.memory = VectorMemory(task_id)

        self.results: list[dict] = []
        self.valid_results: list[dict] = []

    # ------ broadcasting ------

    async def _broadcast(self, step_num: int, action: str, details: dict):
        """Send structured update with both raw_event and ui_event."""
        description = details.get("description", "")
        status_text = details.get("status", "")

        # Build human-friendly message
        label = _ACTION_LABELS.get(action, action.replace("_", " ").title())
        if action == "navigate" and "url" in details:
            ui_message = f"{label} {details['url'][:60]}..."
        elif action == "type" and "text" in details.get("params", {}):
            ui_message = f'{label} "{details["params"]["text"][:40]}"'
        elif description:
            ui_message = f"{label}: {description}"
        else:
            ui_message = label

        # Map to event type
        if status_text == "failed" or action == "task_failed":
            evt_type = "error"
        elif action in ("extract", "extracted", "evaluated", "validated", "task_completed"):
            evt_type = "result"
        elif action in ("navigate", "click", "type", "scroll"):
            evt_type = "action"
        else:
            evt_type = "info"

        message = {
            "task_id": self.task_id,
            "step": step_num,
            "action": action,
            "raw_event": details,
            "ui_event": {
                "type": evt_type,
                "message": ui_message,
                "step": step_num,
                "timestamp": datetime.utcnow().isoformat(),
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        if self.on_step:
            await self.on_step(message)

    async def _broadcast_screenshot(self, step_num: int):
        """Capture screenshot and publish it via the on_step callback."""
        try:
            png_bytes = await self.browser.screenshot()
            b64 = base64.b64encode(png_bytes).decode("ascii")
            msg = {
                "task_id": self.task_id,
                "step": step_num,
                "action": "screenshot",
                "details": {"image": b64},
                "timestamp": datetime.utcnow().isoformat(),
            }
            if self.on_step:
                await self.on_step(msg)
        except Exception as e:
            logger.debug("Screenshot capture failed", error=str(e)[:200])

    # ------ main loop ------

    async def run(self) -> dict:
        """Execute the full agent workflow."""
        logger.info("Agent loop started", task_id=self.task_id, goal=self.goal[:80])

        try:
            # Phase 1: Create plan
            plan = await self.planner.create_plan(self.goal)
            plan_descriptions = [s.get("description", s.get("action")) for s in plan]
            await self._broadcast(0, "plan_created", {
                "steps": len(plan),
                "plan": plan_descriptions,
            })

            # Phase 2: Launch browser
            await self.browser.launch()
            await self._broadcast(0, "browser_launched", {})

            # Phase 3: Execute steps
            replan_count = 0
            max_replans = self.settings.default_replan_attempts

            step_idx = 0
            while step_idx < len(plan):
                if step_idx >= self.settings.max_steps_per_task:
                    logger.warning("Max steps reached", task_id=self.task_id)
                    break

                i = step_idx
                step = plan[step_idx]

                action = step.get("action", "unknown")
                description = step.get("description", action)

                await self._broadcast(i + 1, action, {
                    "description": description,
                    "status": "executing",
                })

                result = await self.browser.execute(step)

                # Screenshot after every browser action
                if action not in ("evaluate", "wait"):
                    await self._broadcast_screenshot(i + 1)

                if not result.get("success", False):
                    error = result.get("error", "Unknown error")
                    await self._broadcast(i + 1, action, {
                        "description": description,
                        "status": "failed",
                        "error": error,
                    })

                    if replan_count < max_replans:
                        context = self.memory.get_context_summary()
                        plan = await self.planner.replan(self.goal, context, error)
                        replan_count += 1
                        await self._broadcast(i + 1, "replanned", {
                            "reason": error,
                            "new_steps": len(plan),
                        })
                        step_idx = 0  # Restart the loop with new plan
                        continue
                    else:
                        step_idx += 1
                        continue

                # Analyze page after nav/click/scroll
                if action in ("navigate", "click", "scroll"):
                    try:
                        html = await self.browser.extract_html()
                        analysis = self.analyzer.analyze(html)
                        summary = self.analyzer.create_summary(analysis)
                        await self.memory.store(summary, {
                            "url": self.browser.page.url,
                            "step": i + 1,
                        })
                    except Exception as e:
                        logger.warning("Page analysis failed", error=str(e)[:200])

                # Extract
                if action == "extract":
                    schema = step.get("params", {}).get("schema", "generic")
                    content = result.get("content", "")
                    extracted = await self.extractor.extract(
                        content, schema, self.browser.page.url
                    )
                    self.results.extend(extracted)
                    await self._broadcast(i + 1, "extracted", {
                        "items_count": len(extracted),
                        "total_results": len(self.results),
                    })

                    # --- Validate extracted items ---
                    valid, all_validated = self.validator.validate_all(self.results)
                    self.valid_results = valid
                    self.results = all_validated  # keep validation reasons

                    await self._broadcast(i + 1, "validated", {
                        "total_items": len(all_validated),
                        "valid_items": len(valid),
                        "constraints": self.validator.constraints,
                    })

                    # If zero valid, attempt replan with stricter query
                    if len(valid) == 0 and replan_count < max_replans:
                        gpu = self.validator.constraints.get("gpu", "")
                        stricter_goal = f"{self.goal} - only show {gpu} products"
                        context = self.memory.get_context_summary()
                        plan = await self.planner.replan(stricter_goal, context,
                                                         f"0/{len(all_validated)} items matched constraints")
                        replan_count += 1
                        self.results.clear()
                        self.valid_results.clear()
                        await self._broadcast(i + 1, "replanned", {
                            "reason": f"No valid items found (0/{len(all_validated)} matched constraints)",
                            "new_steps": len(plan),
                        })
                        step_idx = 0  # Restart loop with new plan
                        continue

                # Evaluate
                if action == "evaluate":
                    items_for_eval = self.valid_results if self.valid_results else self.results
                    evaluation = await self.evaluator.evaluate(self.goal, items_for_eval)
                    await self._broadcast(i + 1, "evaluated", evaluation.to_dict())

                    if evaluation.goal_met:
                        logger.info("Goal met!", task_id=self.task_id,
                                    confidence=evaluation.confidence)
                        break

                await self._broadcast(i + 1, action, {
                    "description": description,
                    "status": "completed",
                })
                
                step_idx += 1

            # Phase 4: Final result
            final_items = self.valid_results if self.valid_results else self.results
            final_result = {
                "task_id": self.task_id,
                "goal": self.goal,
                "status": "completed" if final_items else "failed",
                "results": final_items,
                "all_results": self.results,
                "summary": self._generate_summary(),
                "steps_executed": min(
                    len(plan),
                    self.settings.max_steps_per_task,
                ),
            }
            return final_result

        except Exception as e:
            logger.error("Agent loop error", error=str(e), task_id=self.task_id)
            return {
                "task_id": self.task_id,
                "goal": self.goal,
                "status": "failed",
                "error": str(e),
                "results": self.results,
                "summary": f"Failed: {str(e)[:200]}",
                "steps_executed": 0,
            }
        finally:
            await self.browser.close()

    def _generate_summary(self) -> str:
        """Generate a human-readable summary."""
        items = self.valid_results if self.valid_results else self.results
        if not items:
            return "No results were extracted."

        count = len(items)
        total = len(self.results)

        # Price summary
        float_prices = []
        for r in items:
            try:
                cleaned = str(r.get("price", "")).replace("$", "").replace(",", "").strip()
                float_prices.append(float(cleaned))
            except (ValueError, TypeError):
                pass

        if float_prices:
            min_price = min(float_prices)
            cheapest = next(
                (r for r in items if _safe_price(r.get("price")) == min_price),
                None,
            )
            name = cheapest.get("name", "Unknown") if cheapest else "Unknown"
            label = f"Found {count} valid items (out of {total} total). Cheapest: {name} at ₹{min_price:,.2f}"
            return label

        return f"Found {count} valid results (out of {total} total)."


def _safe_price(price) -> Optional[float]:
    try:
        return float(str(price).replace("$", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return None
