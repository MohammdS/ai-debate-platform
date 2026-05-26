"""Tests for the CLI entry point in src/main.py."""
import sys

import pytest


def test_version_flag_prints_and_exits(capsys):
    """--version prints the version string and exits with code 0."""
    from src.main import main
    from src.shared.version import VERSION

    sys.argv = ["debate", "--version"]
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert VERSION in captured.out
    assert "ai-debate-platform" in captured.out
