# Test Suite

Pytest test suite for the Street Fighter engine.

## Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test
uv run pytest tests/test_collision_detection.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src/street_fighter_3rd
```

## Test Categories

- **Collision**: `test_collision_detection.py`, `test_hitbox_integration.py`
- **SF3 Systems**: `test_sf3_*.py` - SF3-authentic collision, integration
- **Characters**: `test_akuma_integration.py` - Character moveset tests

## Writing Tests

Tests should:
- Test frame-accurate behavior (60 FPS critical)
- Use fixtures in `conftest.py` for common setup
- Test edge cases (frame 1 vs frame 60)

See [docs/TESTING_GUIDE.md](../docs/TESTING_GUIDE.md) for testing philosophy.
