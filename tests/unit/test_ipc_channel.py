import asyncio

import pytest

from src.ipc.channel import IpcChannel
from src.ipc.message import DebateMessage, MessageType


@pytest.mark.asyncio
async def test_send_receive_round_trip():
    ch = IpcChannel("test_channel", timeout=5.0)
    msg = DebateMessage(
        msg_type=MessageType.RELAY, sender="judge", receiver="debater_b",
        payload="Counter this argument.", round_num=2,
    )
    await ch.send(msg)
    received = await ch.receive()

    assert received.msg_type == MessageType.RELAY
    assert received.sender == "judge"
    assert received.payload == "Counter this argument."
    assert received.round_num == 2


@pytest.mark.asyncio
async def test_receive_timeout_raises():
    ch = IpcChannel("timeout_channel", timeout=0.05)
    with pytest.raises(asyncio.TimeoutError):
        await ch.receive()


@pytest.mark.asyncio
async def test_multiple_messages_ordered():
    ch = IpcChannel("ordered_channel", timeout=5.0)
    for i in range(3):
        await ch.send(DebateMessage(
            msg_type=MessageType.ARGUMENT, sender="debater_a", receiver="judge",
            payload=f"arg_{i}", round_num=i,
        ))
    for i in range(3):
        msg = await ch.receive()
        assert msg.payload == f"arg_{i}"
