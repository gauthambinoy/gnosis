"""Gnosis SDK — Python client for the Gnosis AI Agent Platform."""
from gnosis_sdk.client import (
    GnosisAuthError,
    GnosisClient,
    GnosisError,
    GnosisNetworkError,
    GnosisNotFoundError,
    GnosisRateLimitError,
    GnosisServerError,
)

__version__ = "0.2.0"
__all__ = [
    "GnosisClient",
    "GnosisError",
    "GnosisAuthError",
    "GnosisNotFoundError",
    "GnosisRateLimitError",
    "GnosisServerError",
    "GnosisNetworkError",
]
