"""The safety gate must stop irreversible actions without stopping ordinary ones.

An over-eager gate is not a safe gate: when "Submit search" needs approval,
every task blocks on a human and the agent is useless. These cases are the
regression guard for that.
"""

import pytest

from app.services.browser.state import InteractiveElement
from app.services.safety.permissions import SafetyValidator


@pytest.fixture
def validator():
    return SafetyValidator()


def element(name: str = "", el_type: str = None, tag: str = "button") -> InteractiveElement:
    return InteractiveElement(element_id=1, tag=tag, name=name, type=el_type)


# --- must NOT require approval: ordinary browsing ---

@pytest.mark.parametrize("name", [
    "Submit search",
    "Search",
    "Go",
    "Sign in",
    "Post",
    "Next page",
    "Add to cart",
    "Account settings",
    "Remove filter",
    "Reply",
    "Save changes",
    "Send",
    "Payment history",
    "Order history",
])
def test_ordinary_clicks_are_allowed(validator, name):
    risk = validator.classify("click", {"element_id": 1}, element(name), "https://www.amazon.com/s?k=laptop")
    assert not risk.requires_approval, f'"{name}" should not need approval: {risk.reason}'


def test_typing_into_a_search_box_is_allowed(validator):
    risk = validator.classify(
        "type",
        {"element_id": 1, "text": "rtx 4060 laptop"},
        element("Search Amazon", el_type="text", tag="input"),
        "https://www.amazon.com",
    )
    assert not risk.requires_approval


def test_navigation_is_never_gated(validator):
    risk = validator.classify("navigate", {"url": "https://checkout.example.com/pay"}, None, "")
    assert not risk.requires_approval


def test_scroll_and_extract_are_never_gated(validator):
    assert not validator.classify("scroll", {"direction": "down"}, None, "https://bank.example.com").requires_approval
    assert not validator.classify("extract", {"schema": "product"}, None, "https://paypal.com").requires_approval


# --- must require approval: irreversible ---

@pytest.mark.parametrize("name", [
    "Place your order",
    "Place Order",
    "Confirm order",
    "Buy now",
    "Buy it now",
    "Confirm payment",
    "Complete purchase",
    "Proceed to checkout",
    "Subscribe",
    "Start free trial",
    "Delete my account",
    "Deactivate account",
    "Transfer funds",
])
def test_irreversible_clicks_need_approval(validator, name):
    risk = validator.classify("click", {"element_id": 1}, element(name), "https://shop.example.com/cart")
    assert risk.requires_approval, f'"{name}" should need approval'
    assert risk.risk_level == "high"
    assert risk.reason


def test_password_field_needs_approval(validator):
    risk = validator.classify(
        "type",
        {"element_id": 1, "text": "hunter2"},
        element("Password", el_type="password", tag="input"),
        "https://example.com/login",
    )
    assert risk.requires_approval


def test_clicks_on_financial_domains_need_approval(validator):
    risk = validator.classify("click", {"element_id": 1}, element("Continue"), "https://www.paypal.com/checkout")
    assert risk.requires_approval


def test_unresolved_element_does_not_crash(validator):
    risk = validator.classify("click", {"element_id": 99}, None, "https://example.com")
    assert not risk.requires_approval
