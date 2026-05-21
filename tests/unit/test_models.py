from src.models.debate import DebateSession, Message


def test_message_model():
    msg = Message(role="user", content="hello")
    assert msg.role == "user"
    assert msg.content == "hello"

def test_debate_session_model():
    session = DebateSession(topic="T", stance_a="A", stance_b="B")
    assert session.topic == "T"
    assert session.history == []
