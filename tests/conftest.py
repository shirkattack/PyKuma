"""Pytest configuration and fixtures."""
import sys
from pathlib import Path

# Add src to Python path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

import pytest

@pytest.fixture
def mock_pygame():
    """Mock pygame for headless testing."""
    # Add pygame mocking if needed for CI/CD
    pass
