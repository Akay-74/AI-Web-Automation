"""Result Evaluator — Checks if extracted data satisfies the user goal.

Uses deterministic checks first, LLM verification only as fallback.
"""

from typing import Optional
from openai import AsyncOpenAI
import structlog

from app.config import get_settings

logger = structlog.get_logger()


class EvaluationResult:
    def __init__(self, goal_met: bool, needs_replan: bool = False,
                 confidence: float = 0.0, reason: str = ""):
        self.goal_met = goal_met
        self.needs_replan = needs_replan
        self.confidence = confidence
        self.reason = reason

    def to_dict(self) -> dict:
        return {
            "goal_met": self.goal_met,
            "needs_replan": self.needs_replan,
            "confidence": self.confidence,
            "reason": self.reason,
        }


class ResultEvaluator:
    """Evaluates whether extracted results satisfy the user's goal."""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        self.model = settings.openai_model

    def check_deterministic(self, goal: str, results: list[dict]) -> Optional[EvaluationResult]:
        """Fast, zero-cost deterministic evaluation."""
        goal_lower = goal.lower()

        if not results:
            return EvaluationResult(goal_met=False, needs_replan=True,
                                    confidence=1.0, reason="No results extracted yet")

        # Check if we have enough results for search/comparison tasks
        if any(word in goal_lower for word in ["find", "search", "list", "collect"]):
            if len(results) >= 3:
                # Check results have required fields (non-empty)
                valid = [r for r in results if any(v for v in r.values()
                         if v and str(v).strip())]
                if len(valid) >= 3:
                    return EvaluationResult(
                        goal_met=True, confidence=0.8,
                        reason=f"Found {len(valid)} valid results"
                    )

        # Check for "cheapest" / "best" / comparison goals
        if any(word in goal_lower for word in ["cheapest", "lowest price", "best"]):
            priced = [r for r in results if r.get("price")]
            if len(priced) >= 2:
                return EvaluationResult(
                    goal_met=True, confidence=0.85,
                    reason=f"Found {len(priced)} items with prices for comparison"
                )

        return None  # Inconclusive — needs LLM

    async def check_with_llm(self, goal: str, results: list[dict]) -> EvaluationResult:
        """LLM-based evaluation. Used only when deterministic check is inconclusive."""
        prompt = f"""Evaluate if this data satisfies the user's goal.
Goal: {goal}
Data: {str(results)[:2000]}

Respond with JSON: {{"goal_met": bool, "confidence": 0.0-1.0, "reason": "..."}}"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            temperature=0.0,
            response_format={"type": "json_object"},
        )

        import json
        result = json.loads(response.choices[0].message.content)
        return EvaluationResult(
            goal_met=result.get("goal_met", False),
            confidence=result.get("confidence", 0.5),
            reason=result.get("reason", "LLM evaluation"),
        )

    async def evaluate(self, goal: str, results: list[dict]) -> EvaluationResult:
        """Main evaluation entry point. Deterministic first, then LLM."""
        # Try deterministic check
        det_result = self.check_deterministic(goal, results)
        if det_result is not None:
            logger.info("Deterministic evaluation", result=det_result.to_dict())
            return det_result

        # Fall back to LLM
        llm_result = await self.check_with_llm(goal, results)
        logger.info("LLM evaluation", result=llm_result.to_dict())
        return llm_result
