"""Tests for src/shared/rate_config.py — load_limits and load_pricing."""
from unittest.mock import patch

from src.shared.rate_config import load_limits, load_pricing


class TestLoadLimits:
    def test_returns_dict_for_known_provider(self):
        result = load_limits("groq")
        assert isinstance(result, dict)

    def test_returns_dict_for_unknown_provider(self):
        """Unknown provider falls back to 'default' key or empty dict."""
        result = load_limits("nonexistent_provider_xyz")
        assert isinstance(result, dict)

    def test_returns_empty_dict_when_file_missing(self):
        with patch("src.shared.rate_config._RATE_LIMITS_PATH") as mock_path:
            mock_path.read_text.side_effect = FileNotFoundError
            result = load_limits("groq")
        assert result == {}

    def test_returns_empty_dict_on_json_decode_error(self):
        with patch("src.shared.rate_config._RATE_LIMITS_PATH") as mock_path:
            mock_path.read_text.return_value = "{bad json"
            result = load_limits("groq")
        assert result == {}


class TestLoadPricing:
    def test_returns_tuple_of_two_floats(self):
        inp, out = load_pricing("groq", "llama-3.1-8b-instant")
        assert isinstance(inp, float) and isinstance(out, float)

    def test_known_model_returns_nonzero_rates(self):
        inp, out = load_pricing("groq", "llama-3.1-8b-instant")
        assert inp > 0 or out > 0

    def test_unknown_model_falls_back_to_default(self):
        inp, out = load_pricing("groq", "model-that-does-not-exist")
        assert isinstance(inp, float) and isinstance(out, float)

    def test_unknown_provider_returns_fallback(self):
        inp, out = load_pricing("unknown_provider", "some-model")
        assert inp == 0.10 and out == 0.10

    def test_returns_fallback_on_file_missing(self):
        with patch("src.shared.rate_config._PRICING_PATH") as mock_path:
            mock_path.read_text.side_effect = FileNotFoundError
            inp, out = load_pricing("groq", "any-model")
        assert inp == 0.10 and out == 0.10

    def test_returns_fallback_on_json_error(self):
        with patch("src.shared.rate_config._PRICING_PATH") as mock_path:
            mock_path.read_text.return_value = "not valid json {"
            inp, out = load_pricing("groq", "any-model")
        assert inp == 0.10 and out == 0.10
