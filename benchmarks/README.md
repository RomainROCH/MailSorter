# MailSorter LLM Benchmarks

Benchmarking suite for comparing LLM provider performance in email classification.

## Quick Start

```bash
# Quick sanity check (tests all available providers)
make benchmark-quick

# Full benchmark on Ollama only (free)
make benchmark

# Compare all providers (may incur API costs)
make benchmark-compare
```

## Components

| File | Purpose |
|------|---------|
| `runner.py` | Main benchmark orchestrator |
| `quick_test.py` | Fast sanity check (5 samples) |
| `test_dataset.json` | 40 labeled test emails |
| `report_generator.py` | JSON → Markdown converter |

## Test Dataset

40 carefully labeled emails covering:

- **7 Categories**: Inbox, Invoices, Newsletters, Spam, Social, Shipping, Support
- **3 Languages**: English, French, German
- **3 Difficulty Levels**: Easy, Medium, Hard

## Running Benchmarks

### Quick Test (5 samples, fast)
```bash
python -m benchmarks.quick_test
python -m benchmarks.quick_test --provider ollama
python -m benchmarks.quick_test -v  # verbose
```

### Full Benchmark
```bash
# Ollama only (free)
python -m benchmarks.runner --providers ollama

# Multiple providers
python -m benchmarks.runner --providers ollama openai anthropic

# All registered providers
python -m benchmarks.runner --all

# Save JSON report
python -m benchmarks.runner --providers ollama --output results.json
```

### Generate Markdown Report
```bash
python -m benchmarks.report_generator reports/benchmark_*.json
```

## Metrics Collected

### Accuracy
- Overall accuracy (correct/total)
- Per-folder accuracy
- Per-difficulty accuracy
- Per-language accuracy

### Latency
- Average, P50, P95, P99
- Min/Max response times

### Cost
- Token usage
- Estimated API cost (USD)
- Projected monthly costs

## Output

Reports are saved to `benchmarks/reports/`:
- `benchmark_YYYYMMDD_HHMMSS.json` - Raw results
- `benchmark_YYYYMMDD_HHMMSS.md` - Human-readable report

## Interpreting Results

### Ollama Suitability Thresholds

| Accuracy | Recommendation |
|----------|---------------|
| ≥95% | ✅ Excellent - use as primary |
| 90-95% | ✅ Good - suitable for production |
| 85-90% | ⚠️ Acceptable with cloud fallback |
| 80-85% | ⚠️ Marginal - needs improvement |
| <80% | ❌ Insufficient - use cloud or fine-tune |

### Latency Guidelines

| Avg Latency | Status |
|-------------|--------|
| <500ms | ✅ Excellent UX |
| 500-1000ms | ✅ Good |
| 1-2s | ⚠️ Acceptable |
| >2s | ⚠️ Consider GPU/smaller model |

## Adding Test Cases

Edit `test_dataset.json` to add more test emails:

```json
{
  "id": "test_XX",
  "sender": "example@domain.com",
  "subject": "Email subject",
  "body": "Email body content",
  "expected_folder": "Invoices",
  "difficulty": "medium",
  "language": "en"
}
```

## Provider Configuration

Providers are configured in `backend/config.json`. Ensure API keys are set for cloud providers:

```json
{
  "providers": {
    "ollama": {"enabled": true, "model": "llama3.2"},
    "openai": {"enabled": true, "api_key_env": "OPENAI_API_KEY"},
    "anthropic": {"enabled": true, "api_key_env": "ANTHROPIC_API_KEY"},
    "gemini": {"enabled": true, "api_key_env": "GOOGLE_API_KEY"}
  }
}
```

## A/B Testing Workflow

1. Run baseline benchmark: `make benchmark`
2. Make changes (prompts, model, etc.)
3. Run comparison: `make benchmark`
4. Compare reports in `benchmarks/reports/`
