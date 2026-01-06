#!/usr/bin/env python3
"""
Quick benchmark test with minimal setup.

This script runs a fast sanity check on available providers
without requiring the full test dataset.

Usage:
    python -m benchmarks.quick_test
    python -m benchmarks.quick_test --provider openai
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.providers.factory import ProviderFactory


# Quick test emails
TEST_EMAILS = [
    {
        "subject": "Your Amazon order #123-456 has shipped",
        "body": "Your package is on its way! Track it here.",
        "expected": "Shipping",
    },
    {
        "subject": "Invoice #2024-001 from Acme Corp",
        "body": "Please find attached your invoice for $500. Payment due in 30 days.",
        "expected": "Invoices",
    },
    {
        "subject": "You won $1,000,000! Claim now!!!",
        "body": "Click here to claim your prize. Limited time offer!!!",
        "expected": "Spam",
    },
    {
        "subject": "Weekly Tech Newsletter - AI Updates",
        "body": "This week in AI: New models released, industry trends, and more. Unsubscribe here.",
        "expected": "Newsletters",
    },
    {
        "subject": "Re: Meeting tomorrow",
        "body": "Sounds good, let's meet at 2pm. Looking forward to it.",
        "expected": "Inbox",
    },
]

FOLDERS = ["Inbox", "Invoices", "Newsletters", "Spam", "Social", "Shipping", "Support"]


def test_provider(provider_name: str, verbose: bool = False) -> dict:
    """Test a single provider with quick samples."""
    results = {
        "provider": provider_name,
        "available": False,
        "healthy": False,
        "samples_tested": 0,
        "correct": 0,
        "accuracy": 0.0,
        "avg_latency_ms": 0,
        "errors": [],
    }
    
    # Try to create provider
    try:
        provider = ProviderFactory.create(provider_name, use_cache=False)
        results["available"] = True
    except Exception as e:
        results["errors"].append(f"Failed to create: {e}")
        return results
    
    # Health check
    try:
        results["healthy"] = provider.health_check()
    except Exception as e:
        results["errors"].append(f"Health check failed: {e}")
    
    if not results["healthy"]:
        results["errors"].append("Provider not healthy, skipping classification tests")
        return results
    
    # Test classifications
    latencies = []
    
    for i, email in enumerate(TEST_EMAILS):
        try:
            start = time.time()
            result = provider.classify_email(
                subject=email["subject"],
                body=email["body"],
                available_folders=FOLDERS,
            )
            latency = int((time.time() - start) * 1000)
            latencies.append(latency)
            
            results["samples_tested"] += 1
            
            if result and result.folder:
                correct = result.folder.lower() == email["expected"].lower()
                if correct:
                    results["correct"] += 1
                
                if verbose:
                    status = "✓" if correct else "✗"
                    print(f"  {status} Sample {i+1}: expected={email['expected']}, "
                          f"got={result.folder}, conf={result.confidence:.2f}, lat={latency}ms")
            else:
                results["errors"].append(f"Sample {i+1}: No result returned")
                
        except Exception as e:
            results["errors"].append(f"Sample {i+1}: {e}")
    
    # Compute final metrics
    if results["samples_tested"] > 0:
        results["accuracy"] = results["correct"] / results["samples_tested"]
    
    if latencies:
        results["avg_latency_ms"] = sum(latencies) // len(latencies)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Quick provider sanity check")
    parser.add_argument(
        "--provider", "-p",
        help="Specific provider to test (default: all available)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show per-sample results"
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 50)
    print("🧪 QUICK BENCHMARK TEST")
    print("=" * 50)
    
    # Get providers to test
    if args.provider:
        providers = [args.provider]
    else:
        providers = ProviderFactory.list_providers()
    
    print(f"\nProviders to test: {providers}")
    print(f"Test samples: {len(TEST_EMAILS)}")
    print()
    
    all_results = []
    
    for provider_name in providers:
        print(f"\n{'─' * 40}")
        print(f"Testing: {provider_name}")
        print("─" * 40)
        
        results = test_provider(provider_name, verbose=args.verbose)
        all_results.append(results)
        
        # Summary
        if results["available"]:
            print(f"  Available: ✓")
            print(f"  Healthy: {'✓' if results['healthy'] else '✗'}")
            
            if results["samples_tested"] > 0:
                print(f"  Accuracy: {results['accuracy']:.0%} ({results['correct']}/{results['samples_tested']})")
                print(f"  Avg Latency: {results['avg_latency_ms']}ms")
        else:
            print(f"  Available: ✗")
        
        if results["errors"]:
            print(f"  Errors:")
            for err in results["errors"][:3]:  # Show max 3 errors
                print(f"    - {err}")
    
    # Summary table
    print("\n" + "=" * 50)
    print("📊 SUMMARY")
    print("=" * 50)
    print(f"{'Provider':<12} {'Status':<10} {'Accuracy':<10} {'Latency':<10}")
    print("-" * 42)
    
    for r in all_results:
        status = "✓ Ready" if r["healthy"] else "✗ Unavail"
        acc = f"{r['accuracy']:.0%}" if r["samples_tested"] > 0 else "N/A"
        lat = f"{r['avg_latency_ms']}ms" if r["avg_latency_ms"] > 0 else "N/A"
        print(f"{r['provider']:<12} {status:<10} {acc:<10} {lat:<10}")
    
    # Recommendation
    print("\n💡 Quick Assessment:")
    
    ready_providers = [r for r in all_results if r["healthy"] and r["samples_tested"] > 0]
    
    if not ready_providers:
        print("  ❌ No providers are currently available. Check configuration.")
    else:
        best = max(ready_providers, key=lambda r: (r["accuracy"], -r["avg_latency_ms"]))
        print(f"  ✅ Best performing: {best['provider']} ({best['accuracy']:.0%} accuracy)")
        
        ollama = next((r for r in ready_providers if r["provider"] == "ollama"), None)
        if ollama:
            if ollama["accuracy"] >= 0.8:
                print("  ✅ Ollama suitable for production use")
            elif ollama["accuracy"] >= 0.6:
                print("  ⚠️ Ollama marginal - consider cloud fallback for low confidence")
            else:
                print("  ❌ Ollama needs improvement - use cloud provider or fine-tune")
    
    print()


if __name__ == "__main__":
    main()
