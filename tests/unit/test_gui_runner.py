import pytest

from src.gui.debate_runner import run_debate_from_payload, stream_debate_from_payload


@pytest.mark.asyncio
async def test_run_debate_from_payload_exports_data(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "setup.json").write_text(
        '{"api": {"rate_limit_rpm": 1000}}',
        encoding="utf-8",
    )

    result = await run_debate_from_payload(
        {
            "topic": "Space policy",
            "stance_a": "Go to Mars",
            "stance_b": "Stay on Earth",
            "provider": "mock",
        }
    )

    assert result["topic"] == "Space policy"
    assert len(result["history"]) == 20
    assert "winner" in result["verdict"].lower()
    assert (tmp_path / "results" / "debate.json").exists()


@pytest.mark.asyncio
async def test_stream_debate_from_payload_yields_live_events(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "setup.json").write_text("{}", encoding="utf-8")

    events = [
        event async for event in stream_debate_from_payload(
            {"topic": "Live topic", "provider": "mock"}
        )
    ]

    assert events[0] == {"type": "start", "topic": "Live topic"}
    assert len([event for event in events if event["type"] == "message"]) == 20
    assert events[-2]["type"] == "judging"
    assert events[-1]["type"] == "verdict"
