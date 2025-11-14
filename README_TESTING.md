# Testing Guide

This document describes the testing setup and how to run tests for the news update script.

## Test Structure

The tests are organized in the `tests/` directory:

- `test_config_loading.py` - Tests for configuration loading
- `test_date_calculation.py` - Tests for date range calculations
- `test_keyword_processing.py` - Tests for keyword normalization and matching
- `test_metrics_tracker.py` - Tests for metrics tracking
- `test_article_processing.py` - Tests for article processing

## Running Tests

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=update_news --cov-report=html
```

This will generate an HTML coverage report in `htmlcov/index.html`.

### Run Specific Test File

```bash
pytest tests/test_config_loading.py
```

### Run Specific Test

```bash
pytest tests/test_config_loading.py::TestLoadConfig::test_load_config_file_exists
```

### Verbose Output

```bash
pytest -v
```

## Test Coverage

The test suite covers:

- ✅ Configuration loading and value retrieval
- ✅ Date range calculations
- ✅ Keyword normalization and matching
- ✅ Metrics tracking and JSON export
- ✅ Article processing and filtering
- ✅ Error handling

## Continuous Integration

Tests can be integrated into CI/CD pipelines. Example GitHub Actions workflow:

```yaml
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest --cov=update_news --cov-report=xml
```

## Writing New Tests

When adding new functionality, follow these guidelines:

1. Create test file in `tests/` directory
2. Name test file `test_<module_name>.py`
3. Use descriptive test class and method names
4. Follow the pattern: `Test<ClassName>` for classes, `test_<functionality>` for methods
5. Use pytest fixtures for setup/teardown
6. Aim for high test coverage (>80%)

## Example Test

```python
def test_example_functionality():
    """Test description."""
    # Arrange
    input_value = "test"
    
    # Act
    result = function_to_test(input_value)
    
    # Assert
    assert result == expected_value
```

