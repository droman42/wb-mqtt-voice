"""BUG-25 — every other interactive CLI command was swallowed.

Root cause: TWO consumers raced `CLIInput`'s single command queue — the runner's interactive
loop (real) and `InputManager._listen_to_source`, which fed an internal queue that NOTHING
drained (dataflow review P0-8). asyncio alternates queue waiters, so command #1 was processed
and command #2 vanished. The fix deletes the manager's consumer outright: the manager owns
source LIFECYCLE only.
"""

import asyncio

import pytest

from locveil_voice.core.interfaces.input import InputPort
from locveil_voice.inputs.cli import CLIInput
from locveil_voice.inputs.manager import InputManager


class _RecordingSource(InputPort):
    """Minimal source that records whether anyone consumed its stream."""

    def __init__(self):
        super().__init__()
        self.queue: asyncio.Queue = asyncio.Queue()
        self.listen_entered = 0

    async def listen(self):
        self.listen_entered += 1
        while True:
            yield await self.queue.get()

    async def start_listening(self):
        pass

    async def stop_listening(self):
        pass

    def is_listening(self):
        return True

    async def is_available(self):
        return True

    def get_input_type(self):
        return "test"


async def test_manager_start_source_does_not_consume_the_stream():
    """The manager starts/stops sources but must NEVER iterate their listen() stream —
    a second consumer steals items from the one that does the real work."""
    manager = InputManager(component_manager=None)
    source = _RecordingSource()
    await manager.add_source("test", source)
    assert await manager.start_source("test")

    await source.queue.put("first")
    await asyncio.sleep(0.05)  # give any (buggy) background consumer a chance to steal
    assert source.listen_entered == 0, "InputManager consumed the source stream (BUG-25 regressed)"
    assert source.queue.qsize() == 1, "an item was stolen from the source queue"


async def test_cli_two_sequential_commands_reach_the_single_consumer():
    """The runner-loop contract: with the manager running the source, BOTH of two typed
    commands arrive at the one listen() consumer, in order (before the fix, #2 vanished)."""
    manager = InputManager(component_manager=None)
    cli = CLIInput()
    await manager.add_source("cli", cli)
    # start via the manager exactly like the runner path does — but without a TTY we skip
    # the real prompt reader and push into the command queue like the reader would
    cli._listening = True
    assert await manager.start_source("cli")

    await cli._command_queue.put("привет")
    await cli._command_queue.put("расскажи о себе")

    received = []
    async for command in cli.listen():
        received.append(command)
        if len(received) == 2:
            break
    assert received == ["привет", "расскажи о себе"]
