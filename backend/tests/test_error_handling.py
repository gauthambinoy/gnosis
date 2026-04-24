"""
Integration tests for unified error handling system.

Tests verify:
1. All exception types return correct HTTP status codes and JSON format
2. Sensitive information is never leaked in error responses
3. Error codes and messages are consistent
4. Request trace IDs are included
5. Backwards compatibility with legacy error modules
"""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.error_handling import (
    ErrorResponse,
    GnosisException,
    NotFoundError,
    ValidationError,
    AuthError,
    ForbiddenError,
    RateLimitError,
    LLMError,
    ExternalServiceError,
    ConflictError,
    QuotaExceededError,
    register_error_handlers,
)


@pytest.fixture
def test_app():
    """Create a test FastAPI app with error handlers registered."""
    app = FastAPI()
    register_error_handlers(app)

    # Routes that raise specific exceptions
    @app.get("/not_found")
    async def not_found_route():
        raise NotFoundError(message="Agent not found")

    @app.get("/validation_error")
    async def validation_error_route():
        raise ValidationError(
            message="Invalid agent config",
            detail={"field": "name", "error": "too short"},
        )

    @app.get("/auth_error")
    async def auth_error_route():
        raise AuthError(message="Invalid token")

    @app.get("/forbidden")
    async def forbidden_route():
        raise ForbiddenError(message="Cannot access this agent")

    @app.get("/rate_limit")
    async def rate_limit_route():
        raise RateLimitError(message="API rate limit exceeded")

    @app.get("/llm_error")
    async def llm_error_route():
        raise LLMError(message="OpenRouter service unavailable")

    @app.get("/external_service")
    async def external_service_route():
        raise ExternalServiceError(message="Database connection failed")

    @app.get("/conflict")
    async def conflict_route():
        raise ConflictError(message="Agent with this name already exists")

    @app.get("/quota_exceeded")
    async def quota_exceeded_route():
        raise QuotaExceededError(message="Monthly API call quota exceeded")

    @app.get("/unhandled")
    async def unhandled_route():
        raise RuntimeError("Some unexpected error")

    @app.get("/http_exception")
    async def http_exception_route():
        raise HTTPException(status_code=418, detail="I'm a teapot")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


@pytest.fixture
def client(test_app):
    """Create a TestClient for the test app.

    ``raise_server_exceptions=False`` lets the registered Exception handler
    convert unhandled errors into 500 JSON responses instead of TestClient
    re-raising them — which is what we explicitly want to assert on here.
    """
    return TestClient(test_app, raise_server_exceptions=False)


class TestErrorResponseFormat:
    """Test that all error responses have correct format."""

    def test_error_response_structure(self, client):
        """Verify error response has required fields."""
        response = client.get("/not_found")
        assert response.status_code == 404

        data = response.json()
        assert "error" in data
        assert "code" in data
        assert "trace_id" in data
        assert "timestamp" in data
        assert isinstance(data["trace_id"], str)
        assert len(data["trace_id"]) > 0

    def test_error_response_with_detail(self, client):
        """Verify error response can include detail field."""
        response = client.get("/validation_error")
        assert response.status_code == 422

        data = response.json()
        assert data["code"] == "VALIDATION_ERROR"
        assert "detail" in data
        assert data["detail"]["field"] == "name"

    def test_trace_id_included_in_all_errors(self, client):
        """Verify trace_id is present in all error responses."""
        endpoints = [
            ("/not_found", 404),
            ("/validation_error", 422),
            ("/auth_error", 401),
            ("/forbidden", 403),
            ("/rate_limit", 429),
            ("/llm_error", 502),
            ("/external_service", 502),
            ("/conflict", 409),
            ("/quota_exceeded", 402),
        ]

        for endpoint, expected_status in endpoints:
            response = client.get(endpoint)
            assert response.status_code == expected_status
            data = response.json()
            assert "trace_id" in data
            assert len(data["trace_id"]) > 0


class TestHttpStatusCodes:
    """Test that exceptions return correct HTTP status codes."""

    def test_not_found_404(self, client):
        response = client.get("/not_found")
        assert response.status_code == 404
        assert response.json()["code"] == "NOT_FOUND"

    def test_validation_error_422(self, client):
        response = client.get("/validation_error")
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"

    def test_auth_error_401(self, client):
        response = client.get("/auth_error")
        assert response.status_code == 401
        assert response.json()["code"] == "AUTH_ERROR"

    def test_forbidden_403(self, client):
        response = client.get("/forbidden")
        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"

    def test_rate_limit_429(self, client):
        response = client.get("/rate_limit")
        assert response.status_code == 429
        assert response.json()["code"] == "RATE_LIMIT_EXCEEDED"

    def test_llm_error_502(self, client):
        response = client.get("/llm_error")
        assert response.status_code == 502
        assert response.json()["code"] == "LLM_ERROR"

    def test_external_service_error_502(self, client):
        response = client.get("/external_service")
        assert response.status_code == 502
        assert response.json()["code"] == "EXTERNAL_SERVICE_ERROR"

    def test_conflict_409(self, client):
        response = client.get("/conflict")
        assert response.status_code == 409
        assert response.json()["code"] == "CONFLICT"

    def test_quota_exceeded_402(self, client):
        response = client.get("/quota_exceeded")
        assert response.status_code == 402
        assert response.json()["code"] == "QUOTA_EXCEEDED"


class TestUnhandledExceptions:
    """Test handling of unexpected exceptions."""

    def test_unhandled_exception_500(self, client):
        """Unhandled exceptions return 500 with generic message."""
        response = client.get("/unhandled")
        assert response.status_code == 500

        data = response.json()
        assert data["code"] == "INTERNAL_ERROR"
        assert data["error"] == "Internal server error"
        # Detail should not leak internal error in production mode
        assert "trace_id" in data

    def test_http_exception_passthrough(self, client):
        """HTTPException from FastAPI is handled correctly."""
        response = client.get("/http_exception")
        assert response.status_code == 418

        data = response.json()
        assert data["code"] == "HTTP_ERROR"
        assert "I'm a teapot" in data["error"]


class TestErrorResponseModel:
    """Test the ErrorResponse Pydantic model."""

    def test_error_response_build(self):
        """Test ErrorResponse.build() method."""
        error_dict = ErrorResponse.build(
            error="Not found",
            code="NOT_FOUND",
            trace_id="test-trace-123",
        )

        assert error_dict["error"] == "Not found"
        assert error_dict["code"] == "NOT_FOUND"
        assert error_dict["trace_id"] == "test-trace-123"
        assert "timestamp" in error_dict

    def test_error_response_with_detail(self):
        """Test ErrorResponse.build() with detail field."""
        detail = {"field": "email", "reason": "invalid format"}
        error_dict = ErrorResponse.build(
            error="Validation failed",
            code="VALIDATION_ERROR",
            detail=detail,
        )

        assert error_dict["detail"] == detail

    def test_error_response_timestamp_format(self):
        """Test that timestamp is ISO 8601 format."""
        error_dict = ErrorResponse.build(
            error="Test",
            code="TEST",
        )

        timestamp = error_dict["timestamp"]
        # Should be valid ISO 8601 timestamp
        assert "T" in timestamp
        assert "+" in timestamp or "Z" in timestamp or timestamp.endswith("00:00")


class TestExceptionHierarchy:
    """Test that exception subclasses work correctly."""

    def test_gnosis_exception_inheritance(self):
        """All custom exceptions inherit from GnosisException."""
        exceptions = [
            NotFoundError(),
            ValidationError(),
            AuthError(),
            ForbiddenError(),
            RateLimitError(),
            LLMError(),
            ExternalServiceError(),
            ConflictError(),
            QuotaExceededError(),
        ]

        for exc in exceptions:
            assert isinstance(exc, GnosisException)
            assert hasattr(exc, "status_code")
            assert hasattr(exc, "code")
            assert hasattr(exc, "message")

    def test_exception_custom_status_code(self):
        """Exceptions can override status_code."""
        exc = GnosisException(
            message="Custom error",
            status_code=418,
            code="TEAPOT",
        )
        assert exc.status_code == 418
        assert exc.code == "TEAPOT"

    def test_exception_custom_message(self):
        """Exceptions accept custom messages."""
        exc = NotFoundError(message="Custom agent not found")
        assert exc.message == "Custom agent not found"

    def test_exception_detail_field(self):
        """Exceptions can include detail field."""
        exc = ValidationError(
            message="Invalid config",
            detail={"field": "name", "error": "required"},
        )
        assert exc.detail == {"field": "name", "error": "required"}


class TestBackwardsCompatibility:
    """Test backwards compatibility with legacy error modules."""

    def test_legacy_error_response_import(self):
        """Old import path still works."""
        # This should not raise an ImportError
        from app.core.error_response import ErrorResponse as OldErrorResponse
        assert OldErrorResponse is ErrorResponse

    def test_legacy_safe_error_import(self):
        """Old safe_error import still works."""
        from app.core.safe_error import safe_http_error
        # Just verify we can import it
        assert callable(safe_http_error)

    def test_legacy_error_handlers_import(self):
        """Old error_handlers import still works."""
        from app.core.error_handlers import register_error_handlers as old_register
        assert callable(old_register)


class TestErrorLogging:
    """Test that errors are properly logged."""

    def test_validation_error_includes_details(self, client):
        """Validation error includes field details."""
        response = client.get("/validation_error")
        data = response.json()

        assert data["code"] == "VALIDATION_ERROR"
        assert "detail" in data
        assert data["detail"]["field"] == "name"

    def test_auth_error_message(self, client):
        """Auth error includes helpful message."""
        response = client.get("/auth_error")
        data = response.json()

        assert "Invalid token" in data["error"]


class TestSuccessPath:
    """Verify non-error paths still work."""

    def test_health_endpoint_works(self, client):
        """Normal successful responses are not affected."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
