import time

from src.ipc.message import DebateMessage, MessageType


def test_message_round_trip():
    msg = DebateMessage(
        msg_type=MessageType.ARGUMENT,
        sender="debater_a",
        receiver="judge",
        payload="AI is a major risk.",
        round_num=3,
    )
    restored = DebateMessage.from_dict(msg.to_dict())
    assert restored.msg_type == MessageType.ARGUMENT
    assert restored.sender == "debater_a"
    assert restored.payload == "AI is a major risk."
    assert restored.round_num == 3


def test_message_type_is_string_enum():
    assert MessageType.RELAY.value == "RELAY"
    assert MessageType.SHUTDOWN == "SHUTDOWN"


def test_message_timestamp_auto_set():
    before = time.time()
    msg = DebateMessage(
        msg_type=MessageType.VERDICT, sender="judge", receiver="orchestrator",
        payload="A wins", round_num=10,
    )
    assert msg.timestamp >= before
