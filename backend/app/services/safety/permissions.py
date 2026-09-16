"""Safety gate — decides which actions need a human to say yes first.

The bar is deliberately high: only actions that move money, destroy an account,
or hand over credentials. Flagging ordinary navigation ("submit the search
form", "open account settings") means every task stops dead waiting for a
human, which is worse than not gating at all.

Classification runs on the *resolved* target — the accessible name and input
type the perception layer read off the real element — not on the model's prose
description of what it thinks it is doing.
"""

import re
from typing import Optional

import structlog

logger = structlog.get_logger()


# Irreversible money movement or account destruction, matched against the
# element's accessible name. Anchored to whole phrases to avoid matching
# "post" inside "postcode" or "pay" inside "payment history".
_HIGH_RISK_TARGET_PATTERNS = [
    (r"\b(place|submit|confirm|complete)\s+(?:\w+\s+)?order\b", "places an order"),
    (r"\bbuy\s+(it\s+)?now\b", "completes a purchase"),
    (r"\b(confirm|complete|authorise|authorize)\s+(the\s+)?(payment|purchase)\b", "authorises a payment"),
    (r"\bpay\s+(now|\$|₹|€|£)", "sends a payment"),
    (r"\bproceed\s+to\s+(checkout|payment)\b", "starts checkout"),
    (r"\b(subscribe|start\s+(my\s+)?(free\s+)?trial)\b", "starts a paid subscription"),
    (r"\bdelete\s+(my\s+)?(account|profile)\b", "deletes an account"),
    (r"\b(deactivate|close)\s+(my\s+)?account\b", "closes an account"),
    (r"\bdelete\s+(permanently|forever|everything|all)\b", "permanently deletes data"),
    (r"\btransfer\s+(funds|money)\b", "transfers money"),
]

# Domains where any click is worth a confirmation.
_HIGH_RISK_DOMAIN_PATTERNS = [
    r"(^|\.)paypal\.com",
    r"(^|\.)stripe\.com",
    r"(^|\.)venmo\.com",
    r"\bbank\b",
    r"(^|\.)coinbase\.com",
]


class ActionRisk:
    """Verdict for a single action."""

    def __init__(self, requires_approval: bool, reason: str = "", risk_level: str = "low"):
        self.requires_approval = requires_approval
        self.reason = reason
        self.risk_level = risk_level

    def to_dict(self) -> dict:
        return {
            "requires_approval": self.requires_approval,
            "reason": self.reason,
            "risk_level": self.risk_level,
        }


_SAFE = ActionRisk(False, "No high-risk pattern matched")


class SafetyValidator:
    """Classifies an action as free to run or needing human approval."""

    def classify(
        self,
        action: str,
        params: dict,
        element: Optional[object] = None,
        current_url: str = "",
    ) -> ActionRisk:
        """Classify one action.

        Args:
            action: Action name, e.g. ``click``.
            params: Action parameters.
            element: The resolved ``InteractiveElement``, when the action targets one.
            current_url: URL the action will run against.
        """
        # Typing a credential into a real password field.
        if action == "type" and element is not None:
            if (getattr(element, "type", "") or "").lower() == "password":
                return ActionRisk(True, "Types into a password field", "high")

        if action != "click":
            return _SAFE

        target_name = (getattr(element, "name", "") or "").lower()
        target_value = (getattr(element, "value", "") or "").lower()
        haystack = f"{target_name} {target_value}".strip()

        if haystack:
            for pattern, reason in _HIGH_RISK_TARGET_PATTERNS:
                if re.search(pattern, haystack):
                    logger.info("High-risk action detected", target=haystack[:80], reason=reason)
                    return ActionRisk(True, f'Clicking "{target_name[:60]}" {reason}', "high")

        host = _host_of(current_url)
        for pattern in _HIGH_RISK_DOMAIN_PATTERNS:
            if re.search(pattern, host):
                return ActionRisk(True, f"Clicking on a financial site ({host})", "high")

        return _SAFE


def _host_of(url: str) -> str:
    match = re.match(r"^[a-z]+://([^/]+)", url.lower())
    return match.group(1) if match else ""
