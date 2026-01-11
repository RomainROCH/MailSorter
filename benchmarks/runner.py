#!/usr/bin/env python3
"""
Benchmark runner for comparing LLM providers.

Runs classification on labeled test dataset and collects metrics:
- Accuracy (overall, per-folder, per-difficulty)
- Latency (avg, p50, p95, p99)
- Token usage and estimated cost
- Error rates

Usage:
    python -m benchmarks.runner --providers ollama openai --output report.json
    python -m benchmarks.runner --providers all --verbose
"""

import argparse
import json
import logging
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.providers.factory import ProviderFactory

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Cost per 1M tokens (approximate, as of 2026)
COST_PER_1M_TOKENS = {
    "ollama": 0.0,  # Local, free
    "openai": 0.15,  # gpt-4o-mini
    "anthropic": 0.25,  # claude-3-haiku
    "gemini": 0.075,  # gemini-1.5-flash
}


@dataclass
class EmailSample:
    """A single test email."""

    id: str
    sender: str
    subject: str
    body: str
    expected_folder: str
    difficulty: str = "medium"
    language: str = "en"


@dataclass
class ClassificationAttempt:
    """Result of a single classification attempt."""

    email_id: str
    provider: str
    predicted_folder: Optional[str]
    expected_folder: str
    confidence: float
    correct: bool
    latency_ms: int
    tokens_used: int
    error: Optional[str] = None


@dataclass
class ProviderMetrics:
    """Aggregated metrics for a provider."""

    provider: str
    total_samples: int = 0
    correct: int = 0
    errors: int = 0
    accuracy: float = 0.0
    latencies_ms: List[int] = field(default_factory=list)
    tokens_total: int = 0
    estimated_cost_usd: float = 0.0

    # Per-folder accuracy
    per_folder: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # Per-difficulty accuracy
    per_difficulty: Dict[str, Dict[str, int]] = field(default_factory=dict)

    # Per-language accuracy
    per_language: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def compute_final(self):
        """Compute final metrics."""
        if self.total_samples > 0:
            self.accuracy = self.correct / self.total_samples

        # Compute per-category accuracies
        for category in [self.per_folder, self.per_difficulty, self.per_language]:
            for key, counts in category.items():
                if counts.get("total", 0) > 0:
                    counts["accuracy"] = counts["correct"] / counts["total"]

    def latency_stats(self) -> Dict[str, float]:
        """Compute latency statistics."""
        if not self.latencies_ms:
            return {"avg": 0, "p50": 0, "p95": 0, "p99": 0, "min": 0, "max": 0}

        sorted_lat = sorted(self.latencies_ms)
        n = len(sorted_lat)

        return {
            "avg": statistics.mean(sorted_lat),
            "p50": sorted_lat[n // 2],
            "p95": sorted_lat[int(n * 0.95)] if n > 1 else sorted_lat[0],
            "p99": sorted_lat[int(n * 0.99)] if n > 1 else sorted_lat[0],
            "min": sorted_lat[0],
            "max": sorted_lat[-1],
        }

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "provider": self.provider,
            "total_samples": self.total_samples,
            "correct": self.correct,
            "errors": self.errors,
            "accuracy": round(self.accuracy, 4),
            "accuracy_pct": f"{self.accuracy * 100:.1f}%",
            "latency": self.latency_stats(),
            "tokens_total": self.tokens_total,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
            "per_folder": self.per_folder,
            "per_difficulty": self.per_difficulty,
            "per_language": self.per_language,
        }


class BenchmarkRunner:
    """
    Benchmark runner for LLM provider comparison.
    """

    def __init__(
        self,
        dataset_path: str = None,
        providers: List[str] = None,
        folders: List[str] = None,
        verbose: bool = False,
        timeout: int = 30,
    ):
        """
        Initialize benchmark runner.

        Args:
            dataset_path: Path to labeled test dataset JSON
            providers: List of provider names to test
            folders: Available folders for classification
            verbose: Enable verbose output
            timeout: Timeout per classification in seconds
        """
        self.dataset_path = dataset_path or self._default_dataset_path()
        self.providers = providers or ["ollama"]
        self.folders = folders or [
            "Inbox",
            "Invoices",
            "Newsletters",
            "Spam",
            "Social",
            "Shipping",
            "Support",
        ]
        self.verbose = verbose
        self.timeout = timeout

        # Results storage
        self.attempts: List[ClassificationAttempt] = []
        self.metrics: Dict[str, ProviderMetrics] = {}

        # Load dataset
        self.emails = self._load_dataset()

    def _default_dataset_path(self) -> str:
        """Get default dataset path."""
        return str(Path(__file__).parent / "test_dataset.json")

    def _load_dataset(self) -> List[EmailSample]:
        """Load test dataset from JSON."""
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        emails = []
        for e in data.get("emails", []):
            emails.append(
                EmailSample(
                    id=e["id"],
                    sender=e["sender"],
                    subject=e["subject"],
                    body=e["body"],
                    expected_folder=e["expected_folder"],
                    difficulty=e.get("difficulty", "medium"),
                    language=e.get("language", "en"),
                )
            )

        logger.info(f"Loaded {len(emails)} test emails from {self.dataset_path}")
        return emails

    def run(self) -> Dict[str, ProviderMetrics]:
        """
        Run benchmark for all configured providers.

        Returns:
            Dict of provider name → ProviderMetrics
        """
        logger.info(f"Starting benchmark with providers: {self.providers}")
        logger.info(f"Available folders: {self.folders}")
        logger.info(f"Test samples: {len(self.emails)}")

        for provider_name in self.providers:
            self._benchmark_provider(provider_name)

        return self.metrics

    def _benchmark_provider(self, provider_name: str):
        """Benchmark a single provider."""
        logger.info(f"\n{'='*60}")
        logger.info(f"Benchmarking provider: {provider_name}")
        logger.info(f"{'='*60}")

        # Initialize metrics
        metrics = ProviderMetrics(provider=provider_name)

        # Try to create provider
        try:
            provider = ProviderFactory.create(provider_name, use_cache=False)
        except Exception as e:
            logger.error(f"Failed to create provider '{provider_name}': {e}")
            metrics.errors = len(self.emails)
            metrics.total_samples = len(self.emails)
            self.metrics[provider_name] = metrics
            return

        # Health check
        try:
            healthy = provider.health_check()
            if not healthy:
                logger.warning(f"Provider '{provider_name}' health check failed")
        except Exception as e:
            logger.warning(f"Health check error for '{provider_name}': {e}")

        # Run classification on each email
        for i, email in enumerate(self.emails):
            attempt = self._classify_email(provider, provider_name, email)
            self.attempts.append(attempt)

            # Update metrics
            metrics.total_samples += 1

            if attempt.error:
                metrics.errors += 1
            else:
                if attempt.correct:
                    metrics.correct += 1

                metrics.latencies_ms.append(attempt.latency_ms)
                metrics.tokens_total += attempt.tokens_used

                # Update per-category counters
                self._update_category_counts(
                    metrics.per_folder, email.expected_folder, attempt.correct
                )
                self._update_category_counts(
                    metrics.per_difficulty, email.difficulty, attempt.correct
                )
                self._update_category_counts(
                    metrics.per_language, email.language, attempt.correct
                )

            # Progress logging
            if self.verbose or (i + 1) % 10 == 0:
                status = "✓" if attempt.correct else "✗" if not attempt.error else "!"
                logger.info(
                    f"[{i+1}/{len(self.emails)}] {status} {email.id}: "
                    f"expected={email.expected_folder}, got={attempt.predicted_folder}, "
                    f"conf={attempt.confidence:.2f}, lat={attempt.latency_ms}ms"
                )

        # Compute final metrics
        metrics.compute_final()

        # Estimate cost
        cost_per_token = COST_PER_1M_TOKENS.get(provider_name, 0.1) / 1_000_000
        metrics.estimated_cost_usd = metrics.tokens_total * cost_per_token

        self.metrics[provider_name] = metrics

        # Summary
        logger.info(f"\n{provider_name} Summary:")
        logger.info(
            f"  Accuracy: {metrics.accuracy:.1%} ({metrics.correct}/{metrics.total_samples})"
        )
        logger.info(f"  Errors: {metrics.errors}")
        logger.info(f"  Avg Latency: {metrics.latency_stats()['avg']:.0f}ms")
        logger.info(f"  Total Tokens: {metrics.tokens_total}")
        logger.info(f"  Estimated Cost: ${metrics.estimated_cost_usd:.4f}")

    def _classify_email(
        self, provider, provider_name: str, email: EmailSample
    ) -> ClassificationAttempt:
        """Classify a single email and return attempt result."""
        start_time = time.time()

        try:
            result = provider.classify_email(
                subject=email.subject,
                body=email.body,
                available_folders=self.folders,
            )

            latency_ms = int((time.time() - start_time) * 1000)

            if result is None:
                return ClassificationAttempt(
                    email_id=email.id,
                    provider=provider_name,
                    predicted_folder=None,
                    expected_folder=email.expected_folder,
                    confidence=0.0,
                    correct=False,
                    latency_ms=latency_ms,
                    tokens_used=0,
                    error="No result returned",
                )

            predicted = result.folder
            correct = predicted.lower() == email.expected_folder.lower()

            return ClassificationAttempt(
                email_id=email.id,
                provider=provider_name,
                predicted_folder=predicted,
                expected_folder=email.expected_folder,
                confidence=result.confidence,
                correct=correct,
                latency_ms=result.latency_ms or latency_ms,
                tokens_used=result.tokens_used or 0,
            )

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.warning(f"Error classifying {email.id} with {provider_name}: {e}")

            return ClassificationAttempt(
                email_id=email.id,
                provider=provider_name,
                predicted_folder=None,
                expected_folder=email.expected_folder,
                confidence=0.0,
                correct=False,
                latency_ms=latency_ms,
                tokens_used=0,
                error=str(e),
            )

    def _update_category_counts(
        self, category_dict: Dict[str, Dict[str, int]], key: str, correct: bool
    ):
        """Update per-category counts."""
        if key not in category_dict:
            category_dict[key] = {"total": 0, "correct": 0}

        category_dict[key]["total"] += 1
        if correct:
            category_dict[key]["correct"] += 1

    def generate_report(self, output_path: str = None) -> Dict:
        """
        Generate benchmark report.

        Args:
            output_path: Optional path to save JSON report

        Returns:
            Report dictionary
        """
        report = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "dataset": self.dataset_path,
                "total_samples": len(self.emails),
                "providers_tested": list(self.metrics.keys()),
                "folders": self.folders,
            },
            "summary": self._generate_summary(),
            "providers": {
                name: metrics.to_dict() for name, metrics in self.metrics.items()
            },
            "comparison": self._generate_comparison(),
            "recommendations": self._generate_recommendations(),
        }

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            logger.info(f"Report saved to {output_path}")

        return report

    def _generate_summary(self) -> Dict:
        """Generate summary section."""
        if not self.metrics:
            return {}

        # Find best provider by accuracy
        best_accuracy = max(self.metrics.values(), key=lambda m: m.accuracy)

        # Find fastest provider
        fastest = min(
            self.metrics.values(),
            key=lambda m: (
                m.latency_stats()["avg"]
                if m.latency_stats()["avg"] > 0
                else float("inf")
            ),
        )

        # Find cheapest provider
        cheapest = min(self.metrics.values(), key=lambda m: m.estimated_cost_usd)

        return {
            "best_accuracy": {
                "provider": best_accuracy.provider,
                "accuracy": f"{best_accuracy.accuracy:.1%}",
            },
            "fastest": {
                "provider": fastest.provider,
                "avg_latency_ms": fastest.latency_stats()["avg"],
            },
            "cheapest": {
                "provider": cheapest.provider,
                "cost_usd": cheapest.estimated_cost_usd,
            },
        }

    def _generate_comparison(self) -> List[Dict]:
        """Generate provider comparison table."""
        comparison = []

        for name, metrics in sorted(self.metrics.items(), key=lambda x: -x[1].accuracy):
            comparison.append(
                {
                    "provider": name,
                    "accuracy": f"{metrics.accuracy:.1%}",
                    "accuracy_raw": metrics.accuracy,
                    "avg_latency_ms": round(metrics.latency_stats()["avg"]),
                    "errors": metrics.errors,
                    "cost_usd": f"${metrics.estimated_cost_usd:.4f}",
                    "tokens": metrics.tokens_total,
                }
            )

        return comparison

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []

        if not self.metrics:
            return ["No providers were benchmarked."]

        # Get ollama metrics if available
        ollama = self.metrics.get("ollama")
        cloud_providers = {k: v for k, v in self.metrics.items() if k != "ollama"}

        if ollama and cloud_providers:
            best_cloud = max(cloud_providers.values(), key=lambda m: m.accuracy)
            accuracy_gap = best_cloud.accuracy - ollama.accuracy

            if accuracy_gap <= 0.03:
                recommendations.append(
                    f"✅ Ollama performs within 3% of {best_cloud.provider} "
                    f"({ollama.accuracy:.1%} vs {best_cloud.accuracy:.1%}). "
                    "Recommend using Ollama as primary for cost savings."
                )
            elif accuracy_gap <= 0.10:
                recommendations.append(
                    f"⚠️ Ollama is {accuracy_gap:.1%} behind {best_cloud.provider}. "
                    "Consider using Ollama for most cases with cloud fallback for low-confidence."
                )
            else:
                recommendations.append(
                    f"❌ Ollama significantly underperforms ({accuracy_gap:.1%} gap). "
                    "Consider using cloud provider as primary or fine-tuning Ollama model."
                )

        # Latency recommendation
        if ollama and ollama.latency_stats()["avg"] > 2000:
            recommendations.append(
                "⚠️ Ollama latency is high (>2s). Consider GPU acceleration or smaller model."
            )

        # Error rate
        for name, metrics in self.metrics.items():
            error_rate = (
                metrics.errors / metrics.total_samples
                if metrics.total_samples > 0
                else 0
            )
            if error_rate > 0.1:
                recommendations.append(
                    f"❌ {name} has high error rate ({error_rate:.1%}). Check API connectivity/keys."
                )

        # Per-folder recommendations
        for name, metrics in self.metrics.items():
            for folder, stats in metrics.per_folder.items():
                if stats.get("accuracy", 1.0) < 0.7 and stats.get("total", 0) >= 3:
                    recommendations.append(
                        f"⚠️ {name} struggles with '{folder}' folder ({stats['accuracy']:.1%} accuracy). "
                        "Consider adding training examples or rules."
                    )

        if not recommendations:
            recommendations.append(
                "✅ All providers performing well. No issues detected."
            )

        return recommendations

    def print_report(self):
        """Print human-readable report to console."""
        report = self.generate_report()

        print("\n" + "=" * 70)
        print("📊 BENCHMARK REPORT")
        print("=" * 70)

        print(f"\n📅 Timestamp: {report['metadata']['timestamp']}")
        print(f"📧 Test samples: {report['metadata']['total_samples']}")
        print(
            f"🤖 Providers tested: {', '.join(report['metadata']['providers_tested'])}"
        )

        # Summary
        if report.get("summary"):
            print("\n" + "-" * 40)
            print("📈 SUMMARY")
            print("-" * 40)
            s = report["summary"]
            print(
                f"  🏆 Best Accuracy: {s['best_accuracy']['provider']} ({s['best_accuracy']['accuracy']})"
            )
            print(
                f"  ⚡ Fastest: {s['fastest']['provider']} ({s['fastest']['avg_latency_ms']:.0f}ms avg)"
            )
            print(
                f"  💰 Cheapest: {s['cheapest']['provider']} (${s['cheapest']['cost_usd']:.4f})"
            )

        # Comparison table
        print("\n" + "-" * 40)
        print("📊 COMPARISON")
        print("-" * 40)
        print(
            f"{'Provider':<12} {'Accuracy':<10} {'Latency':<10} {'Errors':<8} {'Cost':<12}"
        )
        print("-" * 52)
        for row in report.get("comparison", []):
            print(
                f"{row['provider']:<12} {row['accuracy']:<10} "
                f"{row['avg_latency_ms']:<10}ms {row['errors']:<8} {row['cost_usd']:<12}"
            )

        # Recommendations
        print("\n" + "-" * 40)
        print("💡 RECOMMENDATIONS")
        print("-" * 40)
        for rec in report.get("recommendations", []):
            print(f"  {rec}")

        print("\n" + "=" * 70 + "\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark LLM providers for email classification"
    )
    parser.add_argument(
        "--providers",
        "-p",
        nargs="+",
        default=["ollama"],
        help="Providers to benchmark (e.g., ollama openai anthropic gemini)",
    )
    parser.add_argument(
        "--all", "-a", action="store_true", help="Benchmark all registered providers"
    )
    parser.add_argument("--dataset", "-d", help="Path to test dataset JSON")
    parser.add_argument("--output", "-o", help="Path to save JSON report")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=30,
        help="Timeout per classification in seconds",
    )

    args = parser.parse_args()

    # Determine providers
    if args.all:
        providers = ProviderFactory.list_providers()
    else:
        providers = args.providers

    # Create and run benchmark
    runner = BenchmarkRunner(
        dataset_path=args.dataset,
        providers=providers,
        verbose=args.verbose,
        timeout=args.timeout,
    )

    try:
        runner.run()
    except KeyboardInterrupt:
        logger.info("\nBenchmark interrupted by user")

    # Generate and print report
    runner.print_report()

    # Save JSON report if requested
    if args.output:
        runner.generate_report(args.output)
    else:
        # Auto-save to benchmarks directory
        output_dir = Path(__file__).parent / "reports"
        output_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"benchmark_{timestamp}.json"
        runner.generate_report(str(output_path))


if __name__ == "__main__":
    main()
