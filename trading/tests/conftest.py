"""
Pytest configuration and common fixtures for the trading project tests.
"""

from unittest.mock import Mock

import pytest
from ibapi.client import EClient


@pytest.fixture
def mock_ib_client():
    """Create a mock IB API client for testing."""
    return Mock(spec=EClient)


@pytest.fixture(autouse=True)
def disable_logging():
    """Disable logging during tests to reduce noise."""
    import logging

    logging.getLogger().setLevel(logging.CRITICAL)
