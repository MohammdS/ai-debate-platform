import pytest

from src.sdk.exceptions import (
    AIClientError,
    InvalidResponseError,
    MissingAPIKeyError,
    ProviderHTTPError,
    ProviderTimeoutError,
    RateLimitError,
)


def test_missing_api_key_error_is_subclass():
    assert issubclass(MissingAPIKeyError, AIClientError)


def test_provider_http_error_stores_fields():
    exc = ProviderHTTPError(status_code=500, body="Internal Server Error")
    assert exc.status_code == 500
    assert exc.body == "Internal Server Error"
    assert "500" in str(exc)


def test_provider_http_error_is_subclass():
    assert issubclass(ProviderHTTPError, AIClientError)


def test_rate_limit_error_is_subclass():
    assert issubclass(RateLimitError, AIClientError)


def test_provider_timeout_error_is_subclass():
    assert issubclass(ProviderTimeoutError, AIClientError)


def test_invalid_response_error_is_subclass():
    assert issubclass(InvalidResponseError, AIClientError)


def test_all_errors_are_exceptions():
    for cls in (AIClientError, MissingAPIKeyError, ProviderHTTPError,
                ProviderTimeoutError, RateLimitError, InvalidResponseError):
        assert issubclass(cls, Exception)


def test_provider_http_error_truncates_long_body():
    long_body = "x" * 500
    exc = ProviderHTTPError(status_code=400, body=long_body)
    assert len(str(exc)) < len(long_body)


def test_ai_client_error_can_be_raised_and_caught():
    with pytest.raises(AIClientError):
        raise MissingAPIKeyError("no key")
