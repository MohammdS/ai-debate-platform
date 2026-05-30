from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_production_source_files_stay_under_assignment_line_cap():
    offenders = []
    for path in (ROOT / "src").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > 150:
            offenders.append(f"{path.relative_to(ROOT)}: {line_count}")
    assert offenders == []


def test_only_canonical_env_example_is_tracked():
    assert (ROOT / ".env.example").exists()
    assert not (ROOT / ".env-example").exists()


def test_gui_judge_provider_dropdown_includes_openrouter():
    html = (ROOT / "gui" / "index.html").read_text(encoding="utf-8")
    marker = '<select id="judge-provider" name="judge_provider" required>'
    select_start = html.index(marker)
    select_end = html.index("</select>", select_start)
    judge_select = html[select_start:select_end]

    assert '<option value="openrouter">OpenRouter</option>' in judge_select


def test_gui_requires_debate_inputs_before_submit():
    html = (ROOT / "gui" / "index.html").read_text(encoding="utf-8")

    for marker in (
        'name="topic" required',
        'name="stance_a" required',
        'name="stance_b" required',
        'name="rounds" type="number" min="1" max="10" value="10" required',
        "Maximum 10 rounds.",
        'name="provider_a" required',
        'name="provider_b" required',
        'name="judge_provider" required',
        'id="form-status"',
    ):
        assert marker in html


def test_gui_has_single_ai_debate_platform_heading():
    html = (ROOT / "gui" / "index.html").read_text(encoding="utf-8")
    body = html.split("<body>", 1)[1]

    assert body.count(">AI Debate Platform<") == 1
