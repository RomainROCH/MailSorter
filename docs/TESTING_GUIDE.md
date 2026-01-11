# MailSorter Testing Guide

> Complete guide for testing the MailSorter email classification system.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Test Categories](#test-categories)
3. [Running Tests](#running-tests)
4. [Test Coverage Report](#test-coverage-report)
5. [Live Integration Tests](#live-integration-tests)
6. [Load & Performance Tests](#load--performance-tests)
7. [Deployment Tests](#deployment-tests)
8. [CI/CD Integration](#cicd-integration)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

```bash
# Navigate to project root
cd MailSorter

# Create and activate virtual environment
python -m venv backend/.venv

# Windows
backend\.venv\Scripts\activate

# Linux/macOS
source backend/.venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### Run All Unit Tests (Fastest)

```bash
# Run only unit tests (no external dependencies needed)
pytest tests/unit/ -v

# Quick sanity check
pytest tests/unit/ -x --tb=short
```

### Run Full Test Suite

```bash
# All tests except slow/live
pytest tests/ -v -m "not slow and not live"

# All tests including slow
pytest tests/ -v
```

---

## Test Categories

### Unit Tests (`tests/unit/`)

Fast, isolated tests that mock all external dependencies.

| Test File | Coverage Area |
|-----------|--------------|
| `test_providers.py` | LLM provider classes (OpenAI, Anthropic, Gemini) |
| `test_rate_limiter.py` | Token bucket rate limiting |
| `test_circuit_breaker.py` | Circuit breaker pattern |
| `test_smart_cache.py` | Response caching |
| `test_privacy.py` | GDPR/privacy compliance |
| `test_security_owasp.py` | OWASP security checks |
| `test_feedback_loop.py` | Model fine-tuning feedback |
| `test_prompt_engine.py` | Prompt templating |
| `test_confidence.py` | Confidence calibration |
| `test_batch_processor.py` | Batch email processing |
| `test_fuzz.py` | Fuzz testing for edge cases |
| `test_regression.py` | Regression tests |
| `test_secrets.py` | Secret management |
| `test_logger.py` | Logging utilities |
| `test_performance.py` | Performance benchmarks |
| `test_factory.py` | Provider factory pattern |
| `test_attachment_heuristic.py` | Attachment-based classification |

### Integration Tests (`tests/integration/`)

Tests that verify component interactions and system behavior.

| Test File | Coverage Area |
|-----------|--------------|
| `test_orchestrator.py` | Full orchestration pipeline |
| `test_e2e_communication.py` | End-to-end message flow |
| `test_stress.py` | Stress testing |
| `test_cross_platform.py` | Cross-platform compatibility |
| `test_smoke.py` | Smoke tests for quick validation |
| `test_llm_providers_live.py` | **Live LLM provider tests** |
| `test_native_messaging_e2e.py` | **Native messaging protocol** |
| `test_deployment.py` | **Installation & packaging** |
| `test_load_performance.py` | **Load & performance testing** |

---

## Running Tests

### Basic Commands

```bash
# All tests with verbose output
pytest -v

# Specific test file
pytest tests/unit/test_providers.py -v

# Specific test class
pytest tests/unit/test_providers.py::TestOpenAIProvider -v

# Specific test function
pytest tests/unit/test_providers.py::TestOpenAIProvider::test_classify_success -v

# Stop on first failure
pytest -x

# Show print statements
pytest -s

# Parallel execution (if pytest-xdist installed)
pytest -n auto
```

### Filter by Markers

```bash
# Only unit tests
pytest -m unit

# Only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Skip live tests (require external services)
pytest -m "not live"

# Only load tests
pytest -m load

# Only deployment tests
pytest -m deployment
```

### Common Test Scenarios

```bash
# Development: Quick feedback loop
pytest tests/unit/ -x --tb=short -q

# Pre-commit: Full unit + fast integration
pytest tests/ -m "not slow and not live" --tb=short

# CI/CD: All tests with coverage
pytest tests/ --cov=backend --cov-report=html --cov-report=term

# Pre-release: Everything including slow tests
pytest tests/ -v --tb=long
```

---

## Test Coverage Report

### Generate Coverage Report

```bash
# Terminal report
pytest tests/ --cov=backend --cov-report=term

# HTML report (opens in browser)
pytest tests/ --cov=backend --cov-report=html
# Open htmlcov/index.html in browser

# XML report (for CI tools)
pytest tests/ --cov=backend --cov-report=xml
```

### Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| Core modules | ≥ 80% | ✅ |
| Providers | ≥ 90% | ✅ |
| Utilities | ≥ 70% | ✅ |
| Integration | ≥ 60% | ✅ |

---

## Live Integration Tests

These tests require actual external services and are marked with `@pytest.mark.live`.

### LLM Provider Tests (`test_llm_providers_live.py`)

#### Ollama (Local)

```bash
# 1. Start Ollama
ollama serve

# 2. Pull required model
ollama pull llama3

# 3. Run Ollama tests
pytest tests/integration/test_llm_providers_live.py -v -m live -k "Ollama"
```

#### OpenAI

```bash
# 1. Set API key
python -c "from backend.utils.secrets import set_api_key; set_api_key('openai', 'sk-...')"

# 2. Run OpenAI tests
pytest tests/integration/test_llm_providers_live.py -v -m live -k "OpenAI"
```

#### Anthropic (Claude)

```bash
# 1. Set API key
python -c "from backend.utils.secrets import set_api_key; set_api_key('anthropic', 'sk-ant-...')"

# 2. Run Anthropic tests
pytest tests/integration/test_llm_providers_live.py -v -m live -k "Anthropic"
```

#### Google Gemini

```bash
# 1. Set API key
python -c "from backend.utils.secrets import set_api_key; set_api_key('gemini', 'AIza...')"

# 2. Run Gemini tests
pytest tests/integration/test_llm_providers_live.py -v -m live -k "Gemini"
```

#### Run All Available Providers

```bash
# This will skip providers without configured API keys
pytest tests/integration/test_llm_providers_live.py -v -m live
```

### Native Messaging Tests (`test_native_messaging_e2e.py`)

```bash
# Protocol tests (no external deps)
pytest tests/integration/test_native_messaging_e2e.py -v -m "not live"

# Live tests (starts actual backend process)
pytest tests/integration/test_native_messaging_e2e.py -v -m live
```

### Testing with Thunderbird/Betterbird

1. **Install the extension:**
   ```bash
   # Package XPI
   python scripts/package_xpi.py
   
   # Install in Thunderbird: Tools > Add-ons > Install from file > dist/mailsorter-*.xpi
   ```

2. **Register native messaging host:**
   ```bash
   # Windows (run as admin or in elevated prompt)
   installers\register.bat
   
   # Linux/macOS
   chmod +x installers/register.sh
   ./installers/register.sh
   ```

3. **Verify connection:**
   - Open Thunderbird
   - Click MailSorter icon in toolbar
   - Check for "Connected" status

---

## Load & Performance Tests

### Quick Load Test

```bash
# Run load tests (excludes very slow tests)
pytest tests/integration/test_load_performance.py -v -m "not slow"
```

### Full Load Test Suite

```bash
# Run all load tests including 10K email stress test
pytest tests/integration/test_load_performance.py -v

# With memory profiling output
pytest tests/integration/test_load_performance.py -v -s
```

### Specific Load Test Scenarios

```bash
# 1000 email sequential processing
pytest tests/integration/test_load_performance.py::TestHighVolumeProcessing::test_process_1000_emails_sequential -v

# Memory stability test
pytest tests/integration/test_load_performance.py::TestMemoryUsage -v

# Cache performance
pytest tests/integration/test_load_performance.py::TestCachePerformance -v

# Concurrent processing
pytest tests/integration/test_load_performance.py::TestConcurrentProcessing -v

# CPU efficiency
pytest tests/integration/test_load_performance.py::TestCPUPerformance -v
```

### Performance Targets

| Metric | Target | Test |
|--------|--------|------|
| Emails/hour | ≥ 1,000 | `test_process_5000_emails` |
| Classification latency | < 500ms | `test_burst_100_in_1_second` |
| Memory growth (1K emails) | < 100MB | `test_memory_stable_after_1000_classifications` |
| Cache lookup | < 1ms | `test_cache_performance_1000_lookups` |
| Concurrent requests | 10 threads | `test_concurrent_classifications` |

---

## Deployment Tests

### Installation Script Tests

```bash
# Test registration scripts
pytest tests/integration/test_deployment.py::TestRegisterBatScript -v  # Windows
pytest tests/integration/test_deployment.py::TestRegisterShScript -v   # Linux/macOS
```

### XPI Packaging Tests

```bash
# Validate XPI structure
pytest tests/integration/test_deployment.py::TestXPIPackaging -v
pytest tests/integration/test_deployment.py::TestXPIStructure -v
```

### Configuration Tests

```bash
# Verify config files
pytest tests/integration/test_deployment.py::TestConfigurationSetup -v
```

### Version & Upgrade Tests

```bash
# Check version consistency
pytest tests/integration/test_deployment.py::TestUpgradePaths -v
```

### Manual Deployment Testing Checklist

1. **Fresh Install:**
   ```bash
   # 1. Clone repo to new directory
   git clone https://github.com/your/MailSorter.git test-install
   cd test-install
   
   # 2. Run setup
   python -m venv backend/.venv
   source backend/.venv/bin/activate  # or .\backend\.venv\Scripts\activate
   pip install -r backend/requirements.txt
   
   # 3. Run tests
   pytest tests/unit/ -v
   ```

2. **XPI Installation:**
   ```bash
   # Package
   python scripts/package_xpi.py --version 1.0.0
   
   # Verify XPI
   unzip -l dist/mailsorter-1.0.0.xpi
   ```

3. **Native Messaging Registration:**
   ```bash
   # Windows
   installers\register.bat
   # Verify: Check registry HKCU\Software\Mozilla\NativeMessagingHosts\com.mailsorter.backend
   
   # Linux
   ./installers/register.sh
   # Verify: Check ~/.mozilla/native-messaging-hosts/com.mailsorter.backend.json
   ```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -r backend/requirements.txt
    
    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=backend --cov-report=xml
    
    - name: Run integration tests
      run: |
        pytest tests/integration/ -v -m "not live and not slow"
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash
set -e

echo "Running tests..."
pytest tests/unit/ -x --tb=short -q

echo "Running linting..."
python -m flake8 backend/ --max-line-length=100 --ignore=E501

echo "All checks passed!"
```

---

## Troubleshooting

### Common Issues

#### "ModuleNotFoundError: No module named 'backend'"

```bash
# Ensure you're in the project root
cd MailSorter

# Ensure PYTHONPATH includes project root
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Or run pytest from project root
python -m pytest tests/ -v
```

#### "Test timeout exceeded"

```bash
# Increase timeout for slow tests
pytest tests/ -v --timeout=60

# Or disable timeout
pytest tests/ -v --timeout=0
```

#### "Ollama not running"

```bash
# Start Ollama service
ollama serve

# Check if running
curl http://localhost:11434/api/tags
```

#### "API key not configured"

```bash
# Set API key in keyring
python -c "from backend.utils.secrets import set_api_key; set_api_key('openai', 'your-key')"

# Verify
python -c "from backend.utils.secrets import get_api_key; print(get_api_key('openai'))"
```

#### Memory Tests Failing

```bash
# Install psutil
pip install psutil

# Run with more lenient memory limits
pytest tests/integration/test_load_performance.py::TestMemoryUsage -v -s
```

### Debug Mode

```bash
# Run with debug output
pytest tests/ -v -s --tb=long

# Drop into debugger on failure
pytest tests/ --pdb

# Run specific test with verbose logging
pytest tests/unit/test_providers.py::TestOpenAIProvider -v -s --log-cli-level=DEBUG
```

### Test Discovery Issues

```bash
# List all discovered tests
pytest --collect-only

# Check test file is being found
pytest --collect-only tests/integration/test_llm_providers_live.py
```

---

## Test File Reference

### Test Statistics (as of v1.0.0)

| Category | Files | Tests | Coverage |
|----------|-------|-------|----------|
| Unit | 17 | ~400 | 85% |
| Integration | 9 | ~160 | 75% |
| **Total** | **26** | **~560** | **80%** |

### Test Execution Time

| Category | Typical Duration |
|----------|-----------------|
| Unit tests only | 10-30 seconds |
| Integration (no live) | 30-60 seconds |
| Full suite | 2-5 minutes |
| Load tests (slow) | 5-15 minutes |
| Live provider tests | 2-10 minutes (varies) |

---

## Summary

| What to Test | Command |
|-------------|---------|
| Quick development check | `pytest tests/unit/ -x -q` |
| Before commit | `pytest tests/ -m "not slow and not live"` |
| Full validation | `pytest tests/ -v --cov=backend` |
| Live LLM tests | `pytest -m live -v` |
| Load testing | `pytest tests/integration/test_load_performance.py -v` |
| Deployment check | `pytest tests/integration/test_deployment.py -v` |

For questions or issues, see [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) or open an issue on GitHub.
