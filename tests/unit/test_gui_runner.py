import pytest

from src.gui.debate_runner import build_debate_services, run_debate_from_payload, stream_debate_from_payload


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
            "rounds": 1,
        }
    )

    assert result["topic"] == "Space policy"
    assert result["model_info"]["debater_a"]["model"] == "mock-model"
    assert result["model_info"]["judge"]["provider"] == "mock"
    assert len(result["history"]) == 2
    assert "winner" in result["verdict"].lower()
    assert (tmp_path / "results" / "debate.json").exists()


@pytest.mark.asyncio
async def test_stream_debate_from_payload_yields_live_events(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "setup.json").write_text("{}", encoding="utf-8")

    events = [
        event async for event in stream_debate_from_payload(
            {"topic": "Live topic", "provider": "mock", "rounds": 1}
        )
    ]

    assert events[0]["type"] == "start"
    assert events[0]["topic"] == "Live topic"
    assert events[0]["model_info"]["debater_a"]["model"] == "mock-model"
    assert events[0]["model_info"]["judge"]["provider"] == "mock"
    assert len([event for event in events if event["type"] == "message"]) == 2
    assert events[-2]["type"] == "judging"
    assert events[-1]["type"] == "verdict"


@pytest.mark.asyncio
async def test_payload_can_select_judge_provider(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "setup.json").write_text("{}", encoding="utf-8")

    *_, model_info = build_debate_services({
        "topic": "Judge selection",
        "stance_a": "A",
        "stance_b": "B",
        "provider_a": "mock",
        "provider_b": "mock",
        "judge_provider": "gemini",
        "rounds": 1,
    })

    assert model_info["judge"]["provider"] == "gemini"
    assert "Gemini" in model_info["judge"]["display"]
