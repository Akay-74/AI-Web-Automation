"""Result Validator — Constraint‑driven validation for extracted items.

Parses constraints from the user goal (e.g., GPU model) and validates
each extracted item against them. Uses deterministic keyword matching
first, with optional LLM fallback for ambiguous cases.
"""

import re
from typing import Optional
import structlog

logger = structlog.get_logger()

# Common GPU tokens that are NOT valid matches for a given target
GPU_REJECT_TOKENS = [
    "RTX 3050", "RTX 3060", "RTX 3070", "RTX 3080", "RTX 3090",
    "RTX 4050", "RTX 4070", "RTX 4080", "RTX 4090",
    "RTX 5070", "RTX 5080", "RTX 5090",
    "GTX 1650", "GTX 1660",
    "Vega", "integrated", "MX 550", "MX 450", "Intel UHD", "Intel Iris",
]


class ResultValidator:
    """Validates extracted items against user-goal constraints."""

    def __init__(self, goal: str):
        self.goal = goal
        self.constraints = self._parse_constraints(goal)

    def _parse_constraints(self, goal: str) -> dict:
        """Extract key constraints from the goal using deterministic parsing."""
        constraints = {}

        # GPU constraint
        gpu_match = re.search(
            r"(RTX\s*\d{4}\s*(?:Ti|SUPER)?|GTX\s*\d{4}\s*(?:Ti|SUPER)?|RX\s*\d{4}\s*(?:XT)?)",
            goal,
            re.IGNORECASE,
        )
        if gpu_match:
            # Normalize: "RTX 4060" or "rtx4060" → "RTX 4060"
            raw = gpu_match.group(1).upper().strip()
            raw = re.sub(r"(\D)(\d)", r"\1 \2", raw)  # "RTX4060" → "RTX 4060"
            raw = re.sub(r"\s+", " ", raw)
            constraints["gpu"] = raw

        # Price cap
        price_match = re.search(r"under\s*\$?\s*([\d,]+)", goal, re.IGNORECASE)
        if price_match:
            constraints["max_price"] = float(price_match.group(1).replace(",", ""))

        # Brand
        brands = ["asus", "msi", "gigabyte", "zotac", "evga", "pny", "dell", "hp", "lenovo", "acer"]
        for brand in brands:
            if brand in goal.lower():
                constraints["brand"] = brand
                break

        logger.info("Parsed constraints", constraints=constraints)
        return constraints

    def validate_item(self, item: dict) -> dict:
        """Validate a single extracted item. Returns item with validation_reason."""
        reasons = []
        valid = True

        gpu_constraint = self.constraints.get("gpu")
        if gpu_constraint:
            # Build a search string from name + specs
            search_text = (item.get("name", "") + " " + str(item.get("gpu", "")) +
                           " " + str(item.get("specs", ""))).upper()

            # Normalize the search text
            normalized = re.sub(r"(\D)(\d)", r"\1 \2", search_text)
            normalized = re.sub(r"\s+", " ", normalized)

            if gpu_constraint in normalized:
                reasons.append(f"✓ Contains {gpu_constraint}")
            else:
                # Check for known wrong GPUs
                for reject in GPU_REJECT_TOKENS:
                    if reject.upper() in normalized:
                        valid = False
                        reasons.append(f"✗ Contains wrong GPU: {reject} (need {gpu_constraint})")
                        break
                else:
                    # GPU not explicitly found — might be ambiguous
                    if any(tok in normalized for tok in ["RTX", "GTX", "RX", "RADEON"]):
                        valid = False
                        reasons.append(f"✗ GPU found but doesn't match {gpu_constraint}")
                    else:
                        reasons.append(f"⚠ GPU not specified, cannot confirm {gpu_constraint}")
                        # Still allow — might be a listing without GPU in title

        # Price constraint
        max_price = self.constraints.get("max_price")
        if max_price and item.get("price"):
            try:
                price_val = float(str(item["price"]).replace("$", "").replace(",", "").strip())
                if price_val > max_price:
                    valid = False
                    reasons.append(f"✗ Price ${price_val:.2f} exceeds ${max_price:.2f}")
                else:
                    reasons.append(f"✓ Price ${price_val:.2f} within budget")
            except (ValueError, TypeError):
                reasons.append("⚠ Could not parse price for validation")

        # Brand constraint
        brand_constraint = self.constraints.get("brand")
        if brand_constraint:
            name_lower = item.get("name", "").lower()
            if brand_constraint in name_lower:
                reasons.append(f"✓ Brand matches: {brand_constraint}")
            else:
                reasons.append(f"⚠ Brand '{brand_constraint}' not found in name")

        item["validation_reason"] = "; ".join(reasons) if reasons else "No constraints to validate"
        item["is_valid"] = valid
        return item

    def validate_all(self, items: list[dict]) -> tuple[list[dict], list[dict]]:
        """Validate all items. Returns (valid_items, all_items_with_reasons)."""
        all_validated = [self.validate_item(item) for item in items]
        valid = [item for item in all_validated if item.get("is_valid", True)]
        logger.info("Validation complete", total=len(items), valid=len(valid))
        return valid, all_validated
