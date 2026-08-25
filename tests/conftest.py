"""Pytest configuration and fixtures."""
import os
import sys
from pathlib import Path

# Add src to Python path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
# ...and the repo root, so tests can import tests.asset_guard / tools.*
sys.path.insert(0, str(Path(__file__).parent.parent))

# The copyable discrepancy log (bugs/discrepancies.log) is for the HUMAN's
# play sessions; tests seed deliberate discrepancies and would fill it with
# noise. Must be set before street_fighter_3rd.core.frame_lab is imported
# (the path is read at module load).
os.environ.setdefault("PYKUMA_DISCREPANCY_LOG", "")

import pytest

@pytest.fixture
def mock_pygame():
    """Mock pygame for headless testing."""
    # Add pygame mocking if needed for CI/CD
    pass
