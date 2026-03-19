"""
Pytest configuration for test suite.

This conftest.py sets up the Python path and common fixtures.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# For Docker container, add /app to path
if Path("/app").exists() and "/app" not in sys.path:
    sys.path.insert(0, "/app")