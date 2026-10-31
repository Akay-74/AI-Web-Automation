"""Agent loop — the perceive → decide → act cycle.

Each iteration re-reads the page, asks the planner for one action against that
page, checks it against the safety gate, and runs it. Nothing is planned
against a page the agent has not looked at, which is what makes element
targeting hold up on real sites.

Every event it emits goes through ``_emit`` and out to exactly one sink, so the
UI, the stored task log, and the agent all agree on what happened.
"""

from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

import structlog

from app.config import get_settings
from app.services.agent.control import ControlState, ControlStateMachine
from app.services.agent.planner import AIPlanner
from app.services.agent.registry import register_agent, unregister_agent
from app.services.browser.controller import BrowserController, detect_captcha
from app.services.browser.extractor import DataExtractor
from app.services.browser.state import BrowserState
from app.services.perception.page_observer import detect_auto_pause_triggers
from app.services.safety.permissions import SafetyValidator

logger = structlog.get_logger()

_ACTION_LABELS = {
    "navigate": "Opening",
    "click": "Clicking",
    "type": "Typing into",
    "hover": "Hovering over",
    "select": "Selecting in",
    "keypress": "Pressing key",
    "scroll": "Scrolling",
    "back": "Going back",
    "extract": "Extracting data from",
    "wait": "Waiting",
    "new_tab": "Opening a new tab",
    "switch_tab": "Switching tab",
    "close_tab": "Closing tab",
    "get_tabs": "Listing tabs",
    "finish": "Finishing",
}

_RESULT_ACTIONS = {"extracted", "task_completed"}
_ERROR_ACTIONS = {"task_failed", "action_failed", "approval_denied"}
_BROWSER_ACTIONS = {"navigate", "click", "type", "scroll", "select", "hover", "keypress", "back"}


class AgentLoop:
    """Runs one browser automation task end to end."""

    def __init__(
        self,
        task_id: str,
        goal: str,
        on_event: Optional[Callable[[dict], Awaitable[None]]] = None,
    ):
        self.task_id = task_id
        self.goal = goal
        self.on_event = on_event
        self.settings = get_settings()

        self.planner = AIPlanner()
        self.extractor = DataExtractor()
        self.safety = SafetyValidator()
        self.control = ControlStateMachine(on_state_change=self._on_control_change)
        self.browser = BrowserController(
            user_data_dir=self.settings.browser_user_data_dir,
            headless=self.settings.browser_headless,
        )

        self.history: list[dict] = []
        self.results: list[dict] = []

        self._cancelled = False
        # A trigger fires once per URL; re-firing on the page the human just
        # handed back would pause the agent again immediately.
        self._paused_for: set[str] = set()
        self._captcha_handled_for: set[str] = set()

    def cancel(self) -> None:
        """Ask the loop to stop after the current action."""
        self._cancelled = True
        self.browser.resume_after_captcha()  # unblock a CAPTCHA wait
        self.control.release()  # unblock a pause or a pending approval

    # ------------------------------------------------------------------
    # Event emission
    # ------------------------------------------------------------------

    async def _emit(self, step: int, action: str, event: dict, ui_message: Optional[str] = None) -> None:
        """Send one event to the sink the runner supplied."""
        if not self.on_event:
            return

        message = {
            "task_id": self.task_id,
            "step": step,
            "action": action,
            "raw_event": event,
            "timestamp": _now(),
        }
        if ui_message is not None:
            message["ui_event"] = {
                "type": _ui_type(action, event),
                "message": ui_message,
                "step": step,
                "timestamp": message["timestamp"],
            }
        await self.on_event(message)

    async def _emit_frame(self, frame_b64: str) -> None:
        """Forward a screencast frame. Never logged, never given a UI line."""
        if not self.on_event:
            return
        try:
            await self.on_event({
                "task_id": self.task_id,
                "step": 0,
                "action": "screencast_frame",
                "raw_event": {"image": frame_b64, "format": "jpeg"},
                "timestamp": _now(),
            })
        except Exception as e:
            logger.debug("Frame forward failed", error=str(e)[:200])

    async def _on_control_change(self, old_state: ControlState, new_state: ControlState) -> None:
        await self._emit(
            0,
            "control_state_changed",
            {"previous_state": old_state.value, "current_state": new_state.value},
            ui_message=f"Control: {new_state.value.replace('_', ' ').lower()}",
        )

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(self) -> dict:
        """Execute the task. Always returns a result dict, never raises."""
        logger.info("Agent loop started", task_id=self.task_id, goal=self.goal[:80])

        try:
            await self.browser.launch()
            register_agent(self.task_id, self, self.browser)
            await self.browser.start_screencast(self._emit_frame)
            await self._emit(
                0,
                "browser_launched",
                {"viewport": self.browser.viewport_size},
                ui_message="Browser ready",
            )

            outcome = await self._step_until_done()

        except Exception as e:
            logger.error("Agent loop crashed", task_id=self.task_id, error=str(e))
            await self.control.mark_failed()
            return self._result("failed", f"Failed: {str(e)[:200]}", error=str(e))

        finally:
            unregister_agent(self.task_id)
            await self.browser.close()

        return outcome

    async def _step_until_done(self) -> dict:
        """The cycle itself."""
        max_steps = self.settings.max_steps_per_task
        consecutive_failures = 0
        last_signature: Optional[str] = None
        repeat_count = 0
        step = 0

        while step < max_steps:
            if self._cancelled:
                return self._result("cancelled", f"Cancelled before step {step + 1}")

            # 1. Respect whoever is driving.
            if not self.control.can_act():
                resumed = await self.control.wait_until_active(
                    self.settings.human_pause_timeout_seconds
                )
                if not resumed:
                    return self._result(
                        "failed",
                        "Stopped waiting for a human after "
                        f"{self.settings.human_pause_timeout_seconds}s "
                        f"(state: {self.control.state.value})",
                    )
                if self._cancelled:
                    return self._result("cancelled", "Cancelled while paused")

            step += 1

            # 2. Observe.
            state = await self.browser.get_browser_state()
            interrupted = await self._handle_interruptions(step, state)
            if self._cancelled:
                return self._result("cancelled", "Cancelled during observation")
            if interrupted or not self.control.can_act():
                # Whatever happened — a CAPTCHA cleared, the human clicked
                # around — the page has moved on, so this observation cannot be
                # used to decide anything. Spend the step and look again.
                continue

            # 3. Decide.
            try:
                decision = await self.planner.decide_next_action(
                    goal=self.goal,
                    page_state=state.summary_for_llm(self.settings.max_elements_in_context),
                    history=self.history,
                    steps_left=max_steps - step,
                    extracted_count=len(self.results),
                )
            except Exception as e:
                logger.error("Planner failed", error=str(e)[:300])
                return self._result("failed", f"Planner failed: {str(e)[:160]}", error=str(e))

            action = decision["action"]
            params = decision["params"]
            description = decision["description"]

            await self._emit(
                step,
                action,
                {
                    "description": description,
                    "reasoning": decision["reasoning"],
                    "params": params,
                    "status": "executing",
                    "url": state.current_url,
                },
                ui_message=_ui_label(action, params, description),
            )

            if action == "finish":
                summary = str(params.get("result") or description)
                # The planner reports whether it actually got there; a run that
                # hit a dead end is a failure even though it ended tidily.
                succeeded = params.get("success", True) is not False
                if succeeded:
                    await self.control.mark_completed()
                else:
                    await self.control.mark_failed()
                return self._result("completed" if succeeded else "failed", summary)

            # Re-sending the same action against the same page is not progress.
            signature = _signature(action, params, state.current_url)
            repeat_count = repeat_count + 1 if signature == last_signature else 1
            last_signature = signature
            if action != "scroll" and repeat_count >= self.settings.max_repeated_actions:
                await self.control.mark_failed()
                return self._result(
                    "failed",
                    f"Stuck repeating '{action}' on {state.current_url[:80]} "
                    f"{repeat_count} times with no effect.",
                )

            # 4. Check the action against the page and the safety gate.
            element = self.browser.resolve_element(params)
            if params.get("element_id") is not None and element is None:
                consecutive_failures += 1
                await self._record_failure(
                    step, action, description,
                    f"element_id {params.get('element_id')} is not on this page",
                )
                if consecutive_failures >= self.settings.max_consecutive_failures:
                    return self._result("failed", "Too many invalid element references in a row")
                continue

            risk = self.safety.classify(action, params, element, state.current_url)
            if risk.requires_approval:
                if not await self._get_approval(step, action, description, risk):
                    consecutive_failures += 1
                    if consecutive_failures >= self.settings.max_consecutive_failures:
                        return self._result("failed", "Too many actions were not approved")
                    continue

            # 5. Act.
            result = await self.browser.execute(action, params)

            if not result.get("success"):
                consecutive_failures += 1
                await self._record_failure(step, action, description, result.get("error", "unknown error"))
                if consecutive_failures >= self.settings.max_consecutive_failures:
                    return self._result(
                        "failed",
                        f"{consecutive_failures} actions failed in a row; last error: "
                        f"{str(result.get('error'))[:120]}",
                    )
                continue

            if action == "extract":
                rows = await self._handle_extraction(step, result.get("content", ""), params)
                if not rows:
                    # A successful call that found nothing has not advanced the
                    # goal; the planner must be told so it tries elsewhere.
                    consecutive_failures += 1
                    self.history.append({
                        "action": action,
                        "description": description,
                        "ok": False,
                        "error": "extract found 0 items on this page — try a different page or schema",
                    })
                    if consecutive_failures >= self.settings.max_consecutive_failures:
                        return self._result(
                            "failed",
                            f"Nothing extractable found after {consecutive_failures} attempts.",
                        )
                    continue

                consecutive_failures = 0
                self.history.append({
                    "action": action,
                    "description": description,
                    "ok": True,
                    "note": f"{len(rows)} item(s) extracted",
                })
            else:
                consecutive_failures = 0
                self.history.append({
                    "action": action,
                    "description": description,
                    "ok": True,
                    "note": f"now at {result.get('url')}" if result.get("url") else None,
                })

            await self._emit(
                step,
                action,
                {"description": description, "status": "completed"},
                ui_message=None,
            )

        # Budget exhausted.
        summary = (
            f"Reached the {max_steps}-step limit with {len(self.results)} item(s) collected."
        )
        status = "completed" if self.results else "failed"
        await (self.control.mark_completed() if self.results else self.control.mark_failed())
        return self._result(status, summary)

    # ------------------------------------------------------------------
    # Step helpers
    # ------------------------------------------------------------------

    async def _handle_interruptions(self, step: int, state: BrowserState) -> bool:
        """Deal with a CAPTCHA or a credential prompt before deciding anything.

        Returns True if it intervened, meaning the caller's view of the page is
        no longer current. Each trigger fires once per URL; re-firing on the
        page the human just handed back would pause the agent again at once.
        """
        url = state.current_url

        captcha_type = await detect_captcha(self.browser.page)
        if captcha_type and url not in self._captcha_handled_for:
            self._captcha_handled_for.add(url)
            await self._hand_over_captcha(step, captcha_type)
            return True

        if url in self._paused_for:
            return False

        trigger = await detect_auto_pause_triggers(self.browser.page)
        if trigger.should_pause:
            self._paused_for.add(url)
            await self.control.pause_for_human()
            await self._emit(
                step,
                "auto_pause_triggered",
                {
                    "trigger_type": trigger.trigger_type,
                    "reason": trigger.reason,
                    "url": url,
                },
                ui_message=f"Paused: {trigger.reason}. Take over in the browser panel, then resume.",
            )
            return True

        return False

    async def _hand_over_captcha(self, step: int, captcha_type: str) -> None:
        """Pause and let the human clear the challenge; the agent never solves it."""
        await self._emit(
            step,
            "captcha_detected",
            {"captcha_type": captcha_type},
            ui_message=f"{captcha_type} challenge detected",
        )

        await self.control.take_control()
        solved = await self.browser.pause_for_human_captcha(
            self.settings.human_pause_timeout_seconds
        )
        await self.control.give_control_back()
        await self._emit(
            step,
            "captcha_solved" if solved else "captcha_timeout",
            {"method": "human", "solved": solved},
            ui_message="CAPTCHA cleared by you" if solved else "Nobody solved the CAPTCHA in time",
        )

    async def _get_approval(self, step: int, action: str, description: str, risk) -> bool:
        """Ask the human before an irreversible action. False = do not run it."""
        await self._emit(
            step,
            "approval_requested",
            {
                "action": action,
                "description": description,
                **risk.to_dict(),
                "timeout_seconds": self.settings.approval_timeout_seconds,
            },
            ui_message=f"Approval needed: {risk.reason}",
        )

        approved, timed_out = await self.control.request_approval(
            {"action": action, "description": description, "reason": risk.reason},
            timeout=self.settings.approval_timeout_seconds,
        )

        if approved:
            await self._emit(
                step, "approval_granted", {"action": action},
                ui_message="You approved it — continuing",
            )
            return True

        reason = "nobody answered in time" if timed_out else "you declined"
        await self._record_failure(step, action, description, f"Not approved ({reason})")
        await self._emit(
            step, "approval_denied", {"action": action, "timed_out": timed_out},
            ui_message=f"Skipped — {reason}",
        )
        return False

    async def _handle_extraction(self, step: int, content: str, params: dict) -> list[dict]:
        """Run the extractor over the page text and keep the rows."""
        schema = str(params.get("schema", "generic"))
        try:
            rows = await self.extractor.extract(content, schema, goal=self.goal)
        except Exception as e:
            logger.warning("Extraction failed", error=str(e)[:200])
            await self._record_failure(step, "extract", "Extract data", str(e)[:160])
            return []

        self.results.extend(rows)
        await self._emit(
            step,
            "extracted",
            {"items_count": len(rows), "total_results": len(self.results), "schema": schema},
            ui_message=(
                f"Extracted {len(rows)} item(s) — {len(self.results)} total"
                if rows
                else "Nothing extractable on this page"
            ),
        )
        return rows

    async def _record_failure(self, step: int, action: str, description: str, error: str) -> None:
        """Log a failed action into history so the planner can route around it."""
        self.history.append({
            "action": action,
            "description": description,
            "ok": False,
            "error": error,
        })
        await self._emit(
            step,
            "action_failed",
            {"description": description, "status": "failed", "error": error, "of_action": action},
            ui_message=f"{action} failed: {error[:100]}",
        )

    def _result(self, status: str, summary: str, error: Optional[str] = None) -> dict:
        result = {
            "task_id": self.task_id,
            "goal": self.goal,
            "status": status,
            "results": self.results,
            "summary": summary,
            "steps_executed": len(self.history),
        }
        if error:
            result["error"] = error
        logger.info("Agent loop finished", task_id=self.task_id, status=status, items=len(self.results))
        return result


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _signature(action: str, params: dict, url: str) -> str:
    """Identity of an attempt, for spotting a loop that is going nowhere."""
    key_params = sorted(
        (k, str(v)) for k, v in params.items() if k in ("element_id", "url", "text", "key", "tab_id", "schema")
    )
    return f"{url}|{action}|{key_params}"


def _ui_type(action: str, event: dict) -> str:
    if action in _ERROR_ACTIONS or event.get("status") == "failed":
        return "error"
    if action in _RESULT_ACTIONS:
        return "result"
    if action in _BROWSER_ACTIONS:
        return "action"
    return "info"


def _ui_label(action: str, params: dict, description: str) -> str:
    """One readable line for the execution feed."""
    label = _ACTION_LABELS.get(action, action.replace("_", " ").title())

    if action == "navigate" and params.get("url"):
        return f"{label} {str(params['url'])[:70]}"
    if action == "type" and params.get("text"):
        suffix = " and submitting" if params.get("submit") else ""
        return f'{label} a field: "{str(params["text"])[:50]}"{suffix}'
    if description:
        return f"{label}: {description}"
    return label
