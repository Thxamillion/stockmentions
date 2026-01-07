# Stock Mentions Test Suite

Comprehensive unit tests for the Stock Mentions application.

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_ticker_extraction.py

# Run with coverage report
pytest --cov=worker --cov-report=term-missing

# Run specific test class
pytest tests/test_ticker_extraction.py::TestAITickerHandling

# Run specific test
pytest tests/test_ticker_extraction.py::TestAITickerHandling::test_bare_ai_not_matched
```

## Test Coverage

### Currently Tested (48 tests)

**ticker_extraction.py** - Comprehensive coverage of ticker detection logic:
- AI ticker special handling (9 tests)
- Contraction false positives (5 tests)
- Dollar prefix patterns (7 tests)
- Plain ticker patterns (10 tests)
- Mixed patterns (3 tests)
- Edge cases (8 tests)
- Real-world Reddit examples (6 tests)

### Coverage: 29% of worker.py
- ✅ `extract_tickers()` - Fully tested
- ⏳ `load_valid_tickers()` - Not tested (AWS dependency)
- ⏳ Reddit fetching logic - Not tested (integration tests needed)
- ⏳ DynamoDB writes - Not tested (integration tests needed)

## Test Structure

```
tests/
├── README.md                       # This file
├── __init__.py
├── test_ticker_extraction.py       # Ticker detection logic (48 tests)
└── fixtures/                       # Test data (future)
```

## Adding New Tests

1. Create test file: `tests/test_<module>.py`
2. Import function to test
3. Write test classes and methods following pytest conventions
4. Run tests: `pytest tests/test_<module>.py`

Example:
```python
def test_my_feature():
    result = my_function("input")
    assert result == "expected"
```

## CI/CD Integration

To run tests automatically on every push, add to GitHub Actions:

```yaml
- name: Run tests
  run: |
    pip install -r requirements-dev.txt
    pytest tests/ -v --cov=worker
```
