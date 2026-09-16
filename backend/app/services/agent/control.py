"""Control state machine — who is driving the browser, the agent or the human.

    AI_ACTIVE  ←→  AI_PAUSED  ←→  HUMAN_ACTIVE
    AI_ACTIVE  ←→  WAITING_FOR_APPROVAL

There is no separate "re-syncing" state: the agent re-reads the page before
every decision anyway, so whatever the human did by hand is simply part of the
next observation.

Every wait here is bounded. An agent that blocks forever on a human who has
closed the tab is the single worst failure mode for an unattended task.
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Awaitable, Callable, Optional

import structlog

logger = structlog.get_logger()


class ControlState(str, Enum):
    AI_ACTIVE = "AI_ACTIVE"
    AI_PAUSED = "AI_PAUSED"
    HUMAN_ACTIVE = "HUMAN_ACTIVE"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


_TERMINAL = (ControlState.COMPLETED, ControlState.FAILED)


class ControlStateMachine:
    """Tracks control state and gates the agent loop on it."""

    def __init__(
        self,
        on_state_change: Optional[Callable[[ControlState, ControlState], Awaitable[None]]] = None,
    ):
        self._state = ControlState.AI_ACTIVE
        self._on_state_change = on_state_change

        # Set only while the agent is allowed to act.
        self._ai_can_act = asyncio.Event()
        self._ai_can_act.set()

        self._pending_approval: Optional[dict] = None
        self._approval_granted: Optional[bool] = None
        self._approval_event = asyncio.Event()

        self._entered_at = datetime.now(timezone.utc)

    @property
    def state(self) -> ControlState:
        return self._state

    @property
    def is_terminal(self) -> bool:
        return self._state in _TERMINAL

    def can_act(self) -> bool:
        return self._state == ControlState.AI_ACTIVE

    # ------ transitions ------

    async def _transition(self, new_state: ControlState) -> ControlState:
        """Move to *new_state*, notifying the listener if it changed."""
        if new_state == self._state:
            return self._state

        old_state = self._state
        self._state = new_state
        self._entered_at = datetime.now(timezone.utc)

        if new_state == ControlState.AI_ACTIVE:
            self._ai_can_act.set()
        else:
            self._ai_can_act.clear()

        logger.info("Control state changed", from_state=old_state.value, to_state=new_state.value)

        if self._on_state_change:
            await self._on_state_change(old_state, new_state)
        return new_state

    async def pause_for_human(self) -> ControlState:
        """Suspend the agent, leaving the browser as it is."""
        if self._state in _TERMINAL:
            return self._state
        return await self._transition(ControlState.AI_PAUSED)

    async def take_control(self) -> ControlState:
        """Hand the browser to the human."""
        if self._state in _TERMINAL:
            return self._state
        return await self._transition(ControlState.HUMAN_ACTIVE)

    async def give_control_back(self) -> ControlState:
        """Return the browser to the agent."""
        if self._state in _TERMINAL:
            return self._state
        return await self._transition(ControlState.AI_ACTIVE)

    async def mark_completed(self) -> ControlState:
        return await self._transition(ControlState.COMPLETED)

    async def mark_failed(self) -> ControlState:
        return await self._transition(ControlState.FAILED)

    # ------ gating ------

    def release(self) -> None:
        """Unblock anything waiting on this machine, without changing state.

        Used to tear a cancelled task down: the loop wakes, sees the cancel
        flag, and unwinds instead of the state machine pretending the human
        handed control back.
        """
        self._ai_can_act.set()
        self._approval_event.set()

    async def wait_until_active(self, timeout: float) -> bool:
        """Block until the agent may act again.

        Returns False if *timeout* elapsed first, which the loop reports as a
        task that ran out of patience rather than one that hung.
        """
        if self.can_act():
            return True

        logger.info("Agent waiting for control", state=self._state.value, timeout=timeout)
        try:
            await asyncio.wait_for(self._ai_can_act.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            logger.warning("Agent gave up waiting for control", state=self._state.value)
            return False

    # ------ approval ------

    async def request_approval(self, action: dict, timeout: float) -> tuple[bool, bool]:
        """Ask the human to approve *action*.

        Returns ``(approved, timed_out)``. A timeout counts as not approved.
        """
        self._pending_approval = action
        self._approval_granted = None
        self._approval_event.clear()
        await self._transition(ControlState.WAITING_FOR_APPROVAL)

        try:
            await asyncio.wait_for(self._approval_event.wait(), timeout=timeout)
            timed_out = False
        except asyncio.TimeoutError:
            logger.warning("Approval request timed out", timeout=timeout)
            timed_out = True

        approved = bool(self._approval_granted)
        self._pending_approval = None
        await self._transition(ControlState.AI_ACTIVE)
        return approved, timed_out

    async def respond_to_approval(self, approved: bool) -> None:
        """Record the human's answer to a pending approval request."""
        if self._state != ControlState.WAITING_FOR_APPROVAL:
            logger.debug("Approval response with nothing pending", state=self._state.value)
            return
        self._approval_granted = approved
        self._approval_event.set()

    def get_status(self) -> dict:
        """Current control status, for the frontend."""
        return {
            "state": self._state.value,
            "entered_at": self._entered_at.isoformat(),
            "pending_approval": self._pending_approval,
        }
