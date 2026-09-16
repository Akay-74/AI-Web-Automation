"""Control state machine — handover must work, and no wait may be unbounded.

The old machine could strand a task forever: an approval request waited on an
event with no timeout, and the SYNCING state cleared the "agent may act" event
that the loop was waiting on.
"""

import asyncio

import pytest

from app.services.agent.control import ControlState, ControlStateMachine


@pytest.mark.asyncio
async def test_starts_with_the_agent_driving():
    control = ControlStateMachine()
    assert control.state == ControlState.AI_ACTIVE
    assert control.can_act()
    assert await control.wait_until_active(timeout=0.1)


@pytest.mark.asyncio
async def test_human_takes_and_returns_control():
    control = ControlStateMachine()

    await control.take_control()
    assert control.state == ControlState.HUMAN_ACTIVE
    assert not control.can_act()

    await control.give_control_back()
    assert control.state == ControlState.AI_ACTIVE
    assert control.can_act()


@pytest.mark.asyncio
async def test_pause_then_resume():
    control = ControlStateMachine()

    await control.pause_for_human()
    assert control.state == ControlState.AI_PAUSED
    assert not control.can_act()

    await control.give_control_back()
    assert control.can_act()


@pytest.mark.asyncio
async def test_waiting_agent_wakes_when_control_returns():
    control = ControlStateMachine()
    await control.take_control()

    async def hand_back():
        await asyncio.sleep(0.05)
        await control.give_control_back()

    asyncio.create_task(hand_back())
    assert await control.wait_until_active(timeout=2.0)
    assert control.can_act()


@pytest.mark.asyncio
async def test_waiting_for_an_absent_human_times_out():
    control = ControlStateMachine()
    await control.pause_for_human()

    resumed = await control.wait_until_active(timeout=0.1)
    assert resumed is False
    assert control.state == ControlState.AI_PAUSED


@pytest.mark.asyncio
async def test_approval_granted():
    control = ControlStateMachine()

    async def approve():
        await asyncio.sleep(0.05)
        await control.respond_to_approval(True)

    asyncio.create_task(approve())
    approved, timed_out = await control.request_approval({"action": "click"}, timeout=2.0)

    assert approved is True
    assert timed_out is False
    assert control.state == ControlState.AI_ACTIVE


@pytest.mark.asyncio
async def test_approval_rejected():
    control = ControlStateMachine()

    async def reject():
        await asyncio.sleep(0.05)
        await control.respond_to_approval(False)

    asyncio.create_task(reject())
    approved, timed_out = await control.request_approval({"action": "click"}, timeout=2.0)

    assert approved is False
    assert timed_out is False
    assert control.state == ControlState.AI_ACTIVE


@pytest.mark.asyncio
async def test_approval_times_out_instead_of_hanging():
    control = ControlStateMachine()

    approved, timed_out = await control.request_approval({"action": "click"}, timeout=0.1)

    assert approved is False
    assert timed_out is True
    # The agent is released, not stuck in WAITING_FOR_APPROVAL.
    assert control.state == ControlState.AI_ACTIVE


@pytest.mark.asyncio
async def test_state_changes_are_reported_once_each():
    seen = []

    async def listener(old, new):
        seen.append((old.value, new.value))

    control = ControlStateMachine(on_state_change=listener)
    await control.pause_for_human()
    await control.pause_for_human()  # already paused — no second notification
    await control.give_control_back()

    assert seen == [
        ("AI_ACTIVE", "AI_PAUSED"),
        ("AI_PAUSED", "AI_ACTIVE"),
    ]


@pytest.mark.asyncio
async def test_terminal_state_ignores_further_handover():
    control = ControlStateMachine()
    await control.mark_completed()

    await control.take_control()
    assert control.state == ControlState.COMPLETED
    assert control.is_terminal


@pytest.mark.asyncio
async def test_stray_approval_response_is_ignored():
    control = ControlStateMachine()
    await control.respond_to_approval(True)  # nothing pending
    assert control.state == ControlState.AI_ACTIVE
