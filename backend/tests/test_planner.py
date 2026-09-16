"""Planner output parsing.

The decision comes back as model-authored JSON, so it has to survive being
malformed, wrapped in an envelope, or missing fields, without taking the run
down with it.
"""

import json

from app.services.agent.planner import _format_history, _parse_decision


def test_parses_a_well_formed_decision():
    decision = _parse_decision(json.dumps({
        "action": "click",
        "params": {"element_id": 12},
        "description": "Click the search button",
        "reasoning": "It submits the query",
    }))

    assert decision["action"] == "click"
    assert decision["params"] == {"element_id": 12}
    assert decision["description"] == "Click the search button"


def test_action_is_normalised():
    assert _parse_decision('{"action": "  CLICK  "}')["action"] == "click"


def test_unwraps_a_nested_decision():
    decision = _parse_decision(json.dumps({
        "next_action": {"action": "navigate", "params": {"url": "https://example.com"}}
    }))
    assert decision["action"] == "navigate"
    assert decision["params"]["url"] == "https://example.com"


def test_takes_the_first_step_of_a_plan_shaped_reply():
    decision = _parse_decision(json.dumps({
        "steps": [
            {"action": "navigate", "params": {"url": "https://a.example"}},
            {"action": "click", "params": {"element_id": 3}},
        ]
    }))
    assert decision["action"] == "navigate"


def test_malformed_json_finishes_instead_of_raising():
    decision = _parse_decision("not json at all")
    assert decision["action"] == "finish"
    assert decision["params"]["result"]


def test_missing_action_finishes():
    assert _parse_decision('{"params": {"url": "https://x.example"}}')["action"] == "finish"


def test_none_content_finishes():
    assert _parse_decision(None)["action"] == "finish"


def test_non_dict_params_are_replaced():
    decision = _parse_decision('{"action": "scroll", "params": "down"}')
    assert decision["params"] == {}


def test_description_falls_back_to_the_action_name():
    assert _parse_decision('{"action": "scroll"}')["description"] == "scroll"


def test_history_is_summarised_with_outcomes():
    text = _format_history([
        {"action": "navigate", "description": "Open Amazon", "ok": True},
        {"action": "click", "description": "Click result", "ok": False, "error": "selector not found"},
    ])

    assert "Open Amazon" in text
    assert "ok" in text
    assert "FAILED" in text
    assert "selector not found" in text


def test_empty_history_says_so():
    assert "none yet" in _format_history([])


def test_history_is_capped():
    history = [{"action": "scroll", "description": f"step {i}", "ok": True} for i in range(50)]
    assert len(_format_history(history, limit=5).splitlines()) == 5
