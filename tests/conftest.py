"""
Pytest configuration for test suite.

This conftest.py sets up the Python path and common fixtures.
"""

import sys
import os
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# For Docker container, add /app to path
if Path("/app").exists() and "/app" not in sys.path:
    sys.path.insert(0, "/app")


@pytest_asyncio.fixture
async def api_client():
    """HTTPX AsyncClient for E2E API testing."""
    from api.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client