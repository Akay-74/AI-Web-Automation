"""Agent loop behaviour, with the planner and browser faked out.

These run offline. What they pin down is the shape of the cycle: the loop
re-observes before every decision, it gives up instead of hanging, and a bad
decision costs one step rather than the whole task.
"""

import asyncio

import pytest

from app.services.agent import loop as loop_module
from app.services.agent.loop import AgentLoop
from app.services.browser.state import BrowserState, InteractiveElement
from app.services.perception.page_observer import AutoPauseResult
from app.services.safety.permissions import ActionRisk


class FakeBrowser:
    """Stands in for BrowserController, recording what it was asked to do."""

    def __init__(self, elements=None, execute_results=None):
        self.elements = elements if elements is not None else [
            InteractiveElement(element_id=0, tag="input", name="Search", selector="#q"),
            InteractiveElement(element_id=1, tag="button", name="Go", selector="#go"),
        ]
        self._execute_results = list(execute_results or [])
        self.executed: list[tuple[str, dict]] = []
        self.observations = 0
        self.captcha_waits = 0
        self.closed = False
        self.url = "https://example.com"
        self.page = object()

    @property
    def viewport_size(self):
        return {"width": 1440, "height": 900}

    async def launch(self):
        pass

    async def start_screencast(self, on_frame):
        pass

    async def close(self):
        self.closed = True

    async def get_browser_state(self):
        self.observations += 1
        return BrowserState(
            current_url=self.url,
            page_title="Example",
            interactive_elements=self.elements,
        )

    def resolve_element(self, params):
        element_id = params.get("element_id")
        if element_id is None:
            return None
        return next((e for e in self.elements if e.element_id == element_id), None)

    async def execute(self, action, params):
        self.executed.append((action, params))
        if self._execute_results:
            return self._execute_results.pop(0)
        return {"success": True}

    def resume_after_captcha(self):
        pass

    async def pause_for_human_captcha(self, timeout):
        self.captcha_waits += 1
        return True


class ScriptedPlanner:
    """Returns a fixed list of decisions, then finishes."""

    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.prompts: list[str] = []

    async def decide_next_action(self, goal, page_state, history, steps_left, extracted_count=0):
        self.prompts.append(page_state)
        if self.decisions:
            return self.decisions.pop(0)
        return decision("finish", {"result": "done"})


def decision(action, params=None, description=None):
    return {
        "action": action,
        "params": params or {},
        "description": description or action,
        "reasoning": "test",
    }


@pytest.fixture
def quiet_page(monkeypatch):
    """No CAPTCHA and no credential prompt on the page."""
    async def no_captcha(page):
        return None

    async def no_triggers(page):
        return AutoPauseResult()

    monkeypatch.setattr(loop_module, "detect_captcha", no_captcha)
    monkeypatch.setattr(loop_module, "detect_auto_pause_triggers", no_triggers)


def build_agent(monkeypatch, decisions, browser=None, extract_rows=None, settings_overrides=None):
    """Wire an AgentLoop up to fakes and collect everything it emits."""
    browser = browser or FakeBrowser()
    planner = ScriptedPlanner(decisions)

    monkeypatch.setattr(loop_module, "AIPlanner", lambda: planner)
    monkeypatch.setattr(loop_module, "BrowserController", lambda **kwargs: browser)
    monkeypatch.setattr(loop_module, "register_agent", lambda *a, **k: None)
    monkeypatch.setattr(loop_module, "unregister_agent", lambda *a, **k: None)

    class FakeExtractor:
        async def extract(self, content, schema="generic", goal=""):
            return list(extract_rows or [])

    monkeypatch.setattr(loop_module, "DataExtractor", FakeExtractor)

    events = []

    async def collect(message):
        events.append(message)

    agent = AgentLoop(task_id="11111111-1111-1111-1111-111111111111", goal="Find a laptop", on_event=collect)
    for key, value in (settings_overrides or {}).items():
        setattr(agent.settings, key, value)

    return agent, browser, planner, events


def actions_of(events):
    return [e["action"] for e in events]


@pytest.mark.asyncio
async def test_happy_path_navigates_extracts_and_finishes(monkeypatch, quiet_page):
    agent, browser, planner, events = build_agent(
        monkeypatch,
        decisions=[
            decision("navigate", {"url": "https://example.com"}),
            decision("type", {"element_id": 0, "text": "laptop", "submit": True}),
            decision("extract", {"schema": "product"}),
            decision("finish", {"result": "Found 2 laptops"}),
        ],
        extract_rows=[{"name": "Laptop A"}, {"name": "Laptop B"}],
    )

    result = await agent.run()

    assert result["status"] == "completed"
    assert result["summary"] == "Found 2 laptops"
    assert len(result["results"]) == 2
    assert [a for a, _ in browser.executed] == ["navigate", "type", "extract"]
    assert "extracted" in actions_of(events)
    assert browser.closed


@pytest.mark.asyncio
async def test_finish_reporting_failure_is_recorded_as_failed(monkeypatch, quiet_page):
    """Ending tidily on a dead end is still a failed task."""
    agent, _, _, _ = build_agent(
        monkeypatch,
        decisions=[
            decision("finish", {"result": "The product is out of stock everywhere", "success": False})
        ],
    )

    result = await agent.run()

    assert result["status"] == "failed"
    assert result["summary"] == "The product is out of stock everywhere"


@pytest.mark.asyncio
async def test_finish_defaults_to_success_when_unstated(monkeypatch, quiet_page):
    agent, _, _, _ = build_agent(
        monkeypatch, decisions=[decision("finish", {"result": "all done"})]
    )

    result = await agent.run()

    assert result["status"] == "completed"


@pytest.mark.asyncio
async def test_page_is_reobserved_before_every_decision(monkeypatch, quiet_page):
    agent, browser, planner, _ = build_agent(
        monkeypatch,
        decisions=[
            decision("scroll", {"direction": "down"}),
            decision("scroll", {"direction": "down"}),
            decision("finish", {"result": "done"}),
        ],
    )

    await agent.run()

    # One fresh observation per decision, including the one that finished.
    assert browser.observations == 3
    assert len(planner.prompts) == 3


@pytest.mark.asyncio
async def test_a_stale_element_id_costs_one_step_not_the_task(monkeypatch, quiet_page):
    agent, browser, planner, events = build_agent(
        monkeypatch,
        decisions=[
            decision("click", {"element_id": 99}),  # not on the page
            decision("click", {"element_id": 1}),
            decision("finish", {"result": "recovered"}),
        ],
    )

    result = await agent.run()

    assert result["status"] == "completed"
    assert result["summary"] == "recovered"
    # The bad click never reached the browser.
    assert [a for a, _ in browser.executed] == ["click"]
    assert "action_failed" in actions_of(events)
    # The planner was told why it failed.
    assert any("not on this page" in str(h.get("error", "")) for h in agent.history)


@pytest.mark.asyncio
async def test_repeated_failures_stop_the_task(monkeypatch, quiet_page):
    failing = FakeBrowser(
        elements=[
            InteractiveElement(element_id=i, tag="button", name=f"Button {i}", selector=f"#b{i}")
            for i in range(10)
        ],
        execute_results=[{"success": False, "error": "boom"}] * 10,
    )
    # Distinct targets each time, so this exercises the failure counter rather
    # than the stall guard.
    agent, browser, _, events = build_agent(
        monkeypatch,
        decisions=[decision("click", {"element_id": i}) for i in range(10)],
        browser=failing,
        settings_overrides={"max_consecutive_failures": 3},
    )

    result = await agent.run()

    assert result["status"] == "failed"
    assert "failed in a row" in result["summary"]
    assert len(browser.executed) == 3


@pytest.mark.asyncio
async def test_one_failure_does_not_end_the_task(monkeypatch, quiet_page):
    browser = FakeBrowser(execute_results=[
        {"success": False, "error": "transient"},
        {"success": True},
    ])
    agent, _, _, _ = build_agent(
        monkeypatch,
        decisions=[
            decision("click", {"element_id": 1}),
            decision("click", {"element_id": 1}),
            decision("finish", {"result": "second try worked"}),
        ],
        browser=browser,
        settings_overrides={"max_consecutive_failures": 3},
    )

    result = await agent.run()

    assert result["status"] == "completed"
    assert result["summary"] == "second try worked"


@pytest.mark.asyncio
async def test_step_budget_is_enforced(monkeypatch, quiet_page):
    agent, browser, _, _ = build_agent(
        monkeypatch,
        decisions=[decision("scroll", {"direction": "down"}) for _ in range(50)],
        settings_overrides={"max_steps_per_task": 4},
    )

    result = await agent.run()

    assert result["status"] == "failed"  # nothing was collected
    assert "4-step limit" in result["summary"]
    assert len(browser.executed) == 4


@pytest.mark.asyncio
async def test_budget_exhausted_with_results_still_counts_as_completed(monkeypatch, quiet_page):
    agent, _, _, _ = build_agent(
        monkeypatch,
        decisions=[decision("extract", {"schema": "generic"})] + [
            decision("scroll", {"direction": "down"}) for _ in range(10)
        ],
        extract_rows=[{"title": "something"}],
        settings_overrides={"max_steps_per_task": 3},
    )

    result = await agent.run()

    assert result["status"] == "completed"
    assert len(result["results"]) == 1


@pytest.mark.asyncio
async def test_repeating_one_action_stops_the_task(monkeypatch, quiet_page):
    """The failure that burned a whole step budget on a blocked search page."""
    agent, browser, _, _ = build_agent(
        monkeypatch,
        decisions=[decision("click", {"element_id": 1}) for _ in range(20)],
        settings_overrides={"max_repeated_actions": 3, "max_steps_per_task": 20},
    )

    result = await agent.run()

    assert result["status"] == "failed"
    assert "Stuck repeating 'click'" in result["summary"]
    assert len(browser.executed) == 2  # the third attempt is refused


@pytest.mark.asyncio
async def test_repeated_scrolling_is_allowed(monkeypatch, quiet_page):
    """Scrolling the same way repeatedly is how you load a long page."""
    agent, browser, _, _ = build_agent(
        monkeypatch,
        decisions=[decision("scroll", {"direction": "down", "amount": 600}) for _ in range(6)],
        settings_overrides={"max_repeated_actions": 3, "max_steps_per_task": 6},
    )

    result = await agent.run()

    assert "Stuck repeating" not in result["summary"]
    assert len(browser.executed) == 6


@pytest.mark.asyncio
async def test_the_same_action_on_a_new_page_is_not_a_repeat(monkeypatch, quiet_page):
    browser = FakeBrowser()
    agent, _, _, _ = build_agent(
        monkeypatch,
        decisions=[decision("click", {"element_id": 1}) for _ in range(4)] + [
            decision("finish", {"result": "moved along"})
        ],
        browser=browser,
        settings_overrides={"max_repeated_actions": 3},
    )

    # Each click lands somewhere new, which is progress, not a loop.
    original = browser.execute
    counter = {"n": 0}

    async def execute_and_move(action, params):
        counter["n"] += 1
        browser.url = f"https://example.com/page/{counter['n']}"
        return await original(action, params)

    monkeypatch.setattr(browser, "execute", execute_and_move)

    result = await agent.run()

    assert result["status"] == "completed"
    assert len(browser.executed) == 4


@pytest.mark.asyncio
async def test_extract_finding_nothing_counts_against_the_agent(monkeypatch, quiet_page):
    """A 0-row extract used to read as success, so the planner retried forever."""
    agent, browser, _, events = build_agent(
        monkeypatch,
        decisions=[decision("extract", {"schema": "generic"}) for _ in range(10)],
        extract_rows=[],
        settings_overrides={"max_consecutive_failures": 3, "max_repeated_actions": 99},
    )

    result = await agent.run()

    assert result["status"] == "failed"
    assert "Nothing extractable" in result["summary"]
    assert len(browser.executed) == 3
    assert any(not h["ok"] and "0 items" in h.get("error", "") for h in agent.history)


@pytest.mark.asyncio
async def test_extract_records_how_much_it_found(monkeypatch, quiet_page):
    agent, _, _, _ = build_agent(
        monkeypatch,
        decisions=[
            decision("extract", {"schema": "product"}),
            decision("finish", {"result": "got them"}),
        ],
        extract_rows=[{"name": "A"}, {"name": "B"}, {"name": "C"}],
    )

    await agent.run()

    extract_entry = next(h for h in agent.history if h["action"] == "extract")
    assert extract_entry["ok"]
    assert extract_entry["note"] == "3 item(s) extracted"


@pytest.mark.asyncio
async def test_declined_approval_skips_the_action(monkeypatch, quiet_page):
    agent, browser, _, events = build_agent(
        monkeypatch,
        decisions=[
            decision("click", {"element_id": 1}, "Place the order"),
            decision("finish", {"result": "stopped short of buying"}),
        ],
        settings_overrides={"approval_timeout_seconds": 0.05},
    )

    # Force the gate on, and let the approval request time out (nobody answers).
    monkeypatch.setattr(
        agent.safety,
        "classify",
        lambda *a, **k: ActionRisk(True, "places an order", "high"),
    )

    result = await agent.run()

    assert result["status"] == "completed"
    assert browser.executed == []  # the click never ran
    assert "approval_requested" in actions_of(events)
    assert "approval_denied" in actions_of(events)


@pytest.mark.asyncio
async def test_approved_action_runs(monkeypatch, quiet_page):
    agent, browser, _, events = build_agent(
        monkeypatch,
        decisions=[
            decision("click", {"element_id": 1}, "Place the order"),
            decision("finish", {"result": "ordered"}),
        ],
        settings_overrides={"approval_timeout_seconds": 2},
    )
    monkeypatch.setattr(
        agent.safety,
        "classify",
        lambda *a, **k: ActionRisk(True, "places an order", "high"),
    )

    original_request = agent.control.request_approval

    async def auto_approve(action, timeout):
        pending = asyncio.create_task(original_request(action, timeout))
        await asyncio.sleep(0)  # let the request register before answering it
        await agent.control.respond_to_approval(True)
        return await pending

    monkeypatch.setattr(agent.control, "request_approval", auto_approve)

    result = await agent.run()

    assert result["status"] == "completed"
    assert [a for a, _ in browser.executed] == ["click"]
    assert "approval_granted" in actions_of(events)


@pytest.mark.asyncio
async def test_cancellation_stops_the_loop(monkeypatch, quiet_page):
    agent, browser, _, _ = build_agent(
        monkeypatch,
        decisions=[decision("scroll", {"direction": "down"}) for _ in range(20)],
    )

    original = agent.browser.execute

    async def cancel_after_first(action, params):
        agent.cancel()
        return await original(action, params)

    monkeypatch.setattr(agent.browser, "execute", cancel_after_first)

    result = await agent.run()

    assert result["status"] == "cancelled"
    assert len(browser.executed) == 1
    assert browser.closed


@pytest.mark.asyncio
async def test_a_credential_prompt_pauses_for_the_human(monkeypatch):
    async def no_captcha(page):
        return None

    async def login_page(page):
        return AutoPauseResult(True, "login_page", "A password field is on screen")

    monkeypatch.setattr(loop_module, "detect_captcha", no_captcha)
    monkeypatch.setattr(loop_module, "detect_auto_pause_triggers", login_page)

    agent, browser, _, events = build_agent(
        monkeypatch,
        decisions=[decision("finish", {"result": "never reached"})],
        settings_overrides={"human_pause_timeout_seconds": 0.1},
    )

    result = await agent.run()

    assert "auto_pause_triggered" in actions_of(events)
    # Nobody took over, so the task gives up rather than hanging forever.
    assert result["status"] == "failed"
    assert "Stopped waiting for a human" in result["summary"]


@pytest.mark.asyncio
async def test_a_handover_forces_a_fresh_observation(monkeypatch):
    """After a CAPTCHA is cleared the page has moved, so the old view is void."""
    captcha_seen = {"n": 0}

    async def captcha_once(page):
        captcha_seen["n"] += 1
        return "recaptcha" if captcha_seen["n"] == 1 else None

    async def no_triggers(page):
        return AutoPauseResult()

    monkeypatch.setattr(loop_module, "detect_captcha", captcha_once)
    monkeypatch.setattr(loop_module, "detect_auto_pause_triggers", no_triggers)

    agent, browser, planner, events = build_agent(
        monkeypatch,
        decisions=[decision("finish", {"result": "done after the handover"})],
        # No solver key, so it hands straight over to the human.
        settings_overrides={"human_pause_timeout_seconds": 0.1, "captcha_api_key": ""},
    )

    result = await agent.run()

    assert "captcha_detected" in actions_of(events)
    assert browser.captcha_waits == 1
    # Two observations: the one that hit the CAPTCHA, and the fresh one after.
    assert browser.observations == 2
    # The planner was only consulted on the fresh view, never the stale one.
    assert len(planner.prompts) == 1
    assert result["summary"] == "done after the handover"


@pytest.mark.asyncio
async def test_cancelling_a_paused_task_unwinds_it(monkeypatch):
    """Cancel must release a loop that is blocked waiting on a human."""
    async def no_captcha(page):
        return None

    async def login_page(page):
        return AutoPauseResult(True, "login_page", "A password field is on screen")

    monkeypatch.setattr(loop_module, "detect_captcha", no_captcha)
    monkeypatch.setattr(loop_module, "detect_auto_pause_triggers", login_page)

    agent, browser, _, _ = build_agent(
        monkeypatch,
        decisions=[decision("finish", {"result": "unreachable"})],
        # Long enough that only the cancel can end this.
        settings_overrides={"human_pause_timeout_seconds": 30},
    )

    async def cancel_shortly():
        await asyncio.sleep(0.2)
        agent.cancel()

    asyncio.create_task(cancel_shortly())
    result = await asyncio.wait_for(agent.run(), timeout=5.0)

    assert result["status"] == "cancelled"
    assert browser.closed


@pytest.mark.asyncio
async def test_release_does_not_pretend_control_came_back(monkeypatch):
    from app.services.agent.control import ControlState, ControlStateMachine

    control = ControlStateMachine()
    await control.pause_for_human()
    control.release()

    # The waiter is freed, but the recorded state is still "paused" — the human
    # never actually handed anything back.
    assert await control.wait_until_active(timeout=0.1)
    assert control.state == ControlState.AI_PAUSED


@pytest.mark.asyncio
async def test_planner_failure_fails_the_task_cleanly(monkeypatch, quiet_page):
    agent, browser, planner, _ = build_agent(monkeypatch, decisions=[])

    async def explode(*args, **kwargs):
        raise RuntimeError("model unreachable")

    monkeypatch.setattr(planner, "decide_next_action", explode)

    result = await agent.run()

    assert result["status"] == "failed"
    assert "model unreachable" in result["summary"]
    assert browser.closed  # the browser is still cleaned up


@pytest.mark.asyncio
async def test_events_carry_a_consistent_envelope(monkeypatch, quiet_page):
    agent, _, _, events = build_agent(
        monkeypatch,
        decisions=[
            decision("navigate", {"url": "https://example.com"}),
            decision("finish", {"result": "done"}),
        ],
    )

    await agent.run()

    assert events
    for event in events:
        assert event["task_id"] == agent.task_id
        assert "action" in event
        assert "raw_event" in event
        assert "timestamp" in event
        if "ui_event" in event:
            assert event["ui_event"]["type"] in ("info", "action", "result", "error")
            assert event["ui_event"]["message"]


@pytest.mark.asyncio
async def test_screencast_frames_are_emitted_without_a_feed_line(monkeypatch, quiet_page):
    agent, _, _, events = build_agent(
        monkeypatch, decisions=[decision("finish", {"result": "done"})]
    )

    await agent._emit_frame("BASE64DATA")

    frame = next(e for e in events if e["action"] == "screencast_frame")
    assert frame["raw_event"]["image"] == "BASE64DATA"
    assert frame["raw_event"]["format"] == "jpeg"
    assert "ui_event" not in frame  # must not spam the execution feed
