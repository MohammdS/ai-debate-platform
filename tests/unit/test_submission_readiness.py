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
    marker = '<select name="judge_provider">'
    select_start = html.index(marker)
    select_end = html.index("</select>", select_start)
    judge_select = html[select_start:select_end]

    assert '<option value="openrouter">OpenRouter</option>' in judge_select
