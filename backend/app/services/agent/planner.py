"""AI Planner — Uses GPT-4o-mini to decompose user goals into action plans.

Cost optimization: Single API call for initial planning. Re-planning only
when the agent gets stuck. Uses deterministic template matching for common
task patterns to avoid unnecessary LLM calls.
"""

import json
from typing import Optional
from openai import AsyncOpenAI
import structlog

from app.config import get_settings

logger = structlog.get_logger()

SYSTEM_PROMPT = """You are an AI web automation planner. Given a user's goal, create a step-by-step action plan.

Each step must be one of these actions:
- navigate: Go to a URL. Params: {"url": "..."}
- type: Type text into a field. Params: {"selector": "CSS selector", "text": "..."}
- click: Click an element. Params: {"selector": "CSS selector or description"}
- scroll: Scroll down the page. Params: {}
- extract: Extract structured data from the page. Params: {"schema": "product|job|article|generic"}
- wait: Wait for page to load. Params: {"seconds": N}
- evaluate: Check if goal is met. Params: {}

Respond ONLY with a valid JSON object containing a "steps" array. Example:
{
  "steps": [
    {"action": "navigate", "params": {"url": "https://amazon.com"}, "description": "Go to Amazon"},
    {"action": "type", "params": {"selector": "#twotabsearchtextbox", "text": "RTX 4060 laptop"}, "description": "Search for product"},
    {"action": "click", "params": {"selector": "#nav-search-submit-button"}, "description": "Submit search"},
    {"action": "extract", "params": {"schema": "product"}, "description": "Extract product listings"},
    {"action": "evaluate", "params": {}, "description": "Check if we found the cheapest"}
  ]
}

Rules:
- Use the minimum number of steps needed.
- Prefer well-known sites (Amazon, Google, LinkedIn, etc.) with known selectors.
- Always end with an evaluate step.
- Keep it under 15 steps.
"""

# Deterministic templates for common patterns — avoids LLM call entirely
TEMPLATES = {
    "amazon_search": [
        {"action": "navigate", "params": {"url": "https://www.amazon.com"}, "description": "Go to Amazon"},
        {"action": "type", "params": {"selector": "#twotabsearchtextbox", "text": "{query}"}, "description": "Type search query"},
        {"action": "click", "params": {"selector": "#nav-search-submit-button"}, "description": "Submit search"},
        {"action": "scroll", "params": {}, "description": "Load more results"},
        {"action": "extract", "params": {"schema": "product"}, "description": "Extract product listings"},
        {"action": "evaluate", "params": {}, "description": "Evaluate results"},
    ],
    "google_search": [
        {"action": "navigate", "params": {"url": "https://www.google.com"}, "description": "Go to Google"},
        {"action": "type", "params": {"selector": "textarea[name=q]", "text": "{query}"}, "description": "Type search query"},
        {"action": "click", "params": {"selector": "input[name=btnK]"}, "description": "Submit search"},
        {"action": "extract", "params": {"schema": "generic"}, "description": "Extract search results"},
        {"action": "evaluate", "params": {}, "description": "Evaluate results"},
    ],
}


def _match_template(goal: str) -> Optional[list[dict]]:
    """Try to match the goal to a deterministic template. Returns None if no match."""
    goal_lower = goal.lower()
    if "amazon" in goal_lower:
        query = goal_lower.replace("find", "").replace("on amazon", "").replace("from amazon", "").strip()
        steps = json.loads(json.dumps(TEMPLATES["amazon_search"]))
        for step in steps:
            if "text" in step.get("params", {}):
                step["params"]["text"] = step["params"]["text"].replace("{query}", query)
        return steps
    return None


class AIPlanner:
    """Plans browser actions for a given user goal."""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        self.model = settings.openai_model

    async def create_plan(self, goal: str) -> list[dict]:
        """Create an action plan from a natural language goal.

        First tries deterministic templates, then falls back to LLM.
        """
        # Try template match first (zero cost)
        template_plan = _match_template(goal)
        if template_plan:
            logger.info("Plan created from template", goal=goal[:80])
            return template_plan

        # Fall back to LLM
        settings = get_settings()
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Goal: {goal}"},
            ],
            max_tokens=settings.max_tokens_plan,
            temperature=0.1,  # Low temperature for deterministic output
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        plan = json.loads(content)

        # Handle both {"steps": [...]} and direct [...]
        if isinstance(plan, dict) and "steps" in plan:
            plan = plan["steps"]

        logger.info("Plan created via LLM", goal=goal[:80], steps=len(plan),
                     tokens_used=response.usage.total_tokens)
        return plan

    async def replan(self, goal: str, context: str, error: str = "") -> list[dict]:
        """Create a revised plan when the agent gets stuck."""
        settings = get_settings()
        replan_prompt = f"""The previous plan failed or got stuck.
Goal: {goal}
Context of what happened: {context}
Error (if any): {error}

Create a new, revised action plan. Avoid the same approach if it failed."""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": replan_prompt},
            ],
            max_tokens=settings.max_tokens_replan,
            temperature=0.2,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        plan = json.loads(content)
        if isinstance(plan, dict) and "steps" in plan:
            plan = plan["steps"]

        logger.info("Re-plan created", steps=len(plan))
        return plan
