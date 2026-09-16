"""Action planner — decides the agent's next browser action.

The agent does not plan the whole task up front. Guessing CSS selectors for a
page you have not loaded yet does not survive contact with a real website, so
instead the planner is called once per step with the *current* page state and
returns a single next action. Elements are addressed by the ``element_id``
assigned by the perception layer, never by a selector the model invented.
"""

import json
from typing import Optional

import structlog
from openai import AsyncOpenAI

from app.config import get_settings

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are the decision engine of a web automation agent. You see the current
browser page and choose the ONE next action that best advances the user's goal.

Available actions:
- navigate: load a URL. params: {"url": "https://..."}
- click: click an element. params: {"element_id": N}
- type: type into a field. params: {"element_id": N, "text": "...", "submit": true|false}
- select: choose a dropdown option. params: {"element_id": N, "value": "..."}
- hover: hover an element. params: {"element_id": N}
- keypress: press a key. params: {"key": "Enter"|"Escape"|"Tab"|...}
- scroll: scroll the page. params: {"direction": "down"|"up", "amount": 600}
- back: go back one page. params: {}
- wait: wait for the page to settle. params: {"seconds": 2}
- extract: pull structured data off the current page. params: {"schema": "product"|"job"|"article"|"generic"}
- new_tab / switch_tab / close_tab / get_tabs: multi-tab control. params: {"tab_id": N} where relevant
- finish: stop. params: {"result": "short summary of the outcome", "success": true|false}
    Set "success": true if the goal was achieved, false if it cannot be (blocked, not available, dead end).

Rules:
- Only use an element_id listed under "Interactive elements" for the CURRENT page. Never invent one.
- Use "type" with "submit": true to type and press Enter in one step (search boxes).
- Start with "navigate" when the page is blank (about:blank).
- Call "extract" once the page actually shows the data the goal asks for.
- Call "finish" as soon as the goal is satisfied, or if you are stuck and further actions will not help.
  Be honest with "success": a task you could not complete must report false.
- Prefer the shortest route. Do not repeat an action that just failed — try a different element or approach.

Respond with ONLY a JSON object:
{"action": "...", "params": {...}, "description": "what this does, in plain words", "reasoning": "why, in one sentence"}
"""


class AIPlanner:
    """Chooses the next browser action from the live page state."""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self.model = settings.chat_model

    async def decide_next_action(
        self,
        goal: str,
        page_state: str,
        history: list[dict],
        steps_left: int,
        extracted_count: int = 0,
    ) -> dict:
        """Return the next action to execute.

        Args:
            goal: The user's goal, verbatim.
            page_state: Compact page summary from ``BrowserState.summary_for_llm()``.
            history: Prior ``{action, description, ok, error}`` records.
            steps_left: Remaining step budget, so the model can wrap up in time.
            extracted_count: How many data items have been collected so far.
        """
        settings = get_settings()

        user_prompt = "\n".join([
            f"# Goal\n{goal}",
            f"\n# Current page\n{page_state}",
            f"\n# Actions so far\n{_format_history(history)}",
            f"\n# Budget\nSteps remaining: {steps_left}. Data items collected: {extracted_count}.",
            "\nChoose the next action.",
        ])

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=settings.max_tokens_decision,
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        decision = _parse_decision(response.choices[0].message.content)
        logger.info(
            "Action decided",
            action=decision["action"],
            params=decision.get("params"),
            tokens=getattr(response.usage, "total_tokens", 0),
        )
        return decision


def _format_history(history: list[dict], limit: int = 12) -> str:
    if not history:
        return "(none yet — this is the first step)"

    lines = []
    for i, h in enumerate(history[-limit:], start=1):
        if h.get("ok"):
            outcome = "ok"
            if h.get("note"):
                outcome += f" ({h['note']})"
        else:
            outcome = f"FAILED: {str(h.get('error', ''))[:120]}"
        lines.append(f"{i}. {h.get('action')} — {h.get('description', '')} → {outcome}")
    return "\n".join(lines)


def _parse_decision(content: Optional[str]) -> dict:
    """Coerce the model's JSON into a well-formed action dict."""
    try:
        raw = json.loads(content or "{}")
    except json.JSONDecodeError:
        logger.warning("Decision was not valid JSON", content=(content or "")[:200])
        return _finish_decision("Planner returned malformed JSON")

    # Tolerate a model that wraps the action, e.g. {"steps": [ ... ]}.
    if "action" not in raw:
        for key in ("step", "next_action", "decision"):
            if isinstance(raw.get(key), dict):
                raw = raw[key]
                break
        else:
            steps = raw.get("steps")
            if isinstance(steps, list) and steps and isinstance(steps[0], dict):
                raw = steps[0]

    action = raw.get("action")
    if not isinstance(action, str) or not action:
        return _finish_decision("Planner did not name an action")

    params = raw.get("params")
    if not isinstance(params, dict):
        params = {}

    return {
        "action": action.strip().lower(),
        "params": params,
        "description": str(raw.get("description") or action),
        "reasoning": str(raw.get("reasoning") or ""),
    }


def _finish_decision(reason: str) -> dict:
    return {
        "action": "finish",
        "params": {"result": reason},
        "description": reason,
        "reasoning": reason,
    }
