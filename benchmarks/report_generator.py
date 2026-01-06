#!/usr/bin/env python3
"""
Markdown report generator for benchmark results.

Converts JSON benchmark results to human-readable markdown reports.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def generate_markdown_report(report: Dict, output_path: Optional[str] = None) -> str:
    """
    Generate markdown report from benchmark results.
    
    Args:
        report: Benchmark report dictionary
        output_path: Optional path to save markdown file
    
    Returns:
        Markdown string
    """
    lines = []
    
    # Header
    lines.append("# 📊 MailSorter LLM Benchmark Report")
    lines.append("")
    lines.append(f"**Generated:** {report['metadata']['timestamp']}")
    lines.append(f"**Samples:** {report['metadata']['total_samples']}")
    lines.append(f"**Providers:** {', '.join(report['metadata']['providers_tested'])}")
    lines.append("")
    
    # Executive Summary
    if report.get("summary"):
        lines.append("## 🎯 Executive Summary")
        lines.append("")
        s = report["summary"]
        lines.append(f"| Metric | Winner | Value |")
        lines.append("|--------|--------|-------|")
        lines.append(f"| Best Accuracy | **{s['best_accuracy']['provider']}** | {s['best_accuracy']['accuracy']} |")
        lines.append(f"| Fastest | **{s['fastest']['provider']}** | {s['fastest']['avg_latency_ms']:.0f}ms |")
        lines.append(f"| Cheapest | **{s['cheapest']['provider']}** | ${s['cheapest']['cost_usd']:.4f} |")
        lines.append("")
    
    # Comparison Table
    lines.append("## 📈 Provider Comparison")
    lines.append("")
    lines.append("| Provider | Accuracy | Avg Latency | P95 Latency | Errors | Est. Cost |")
    lines.append("|----------|----------|-------------|-------------|--------|-----------|")
    
    for name, metrics in sorted(report.get("providers", {}).items(), key=lambda x: -x[1].get("accuracy", 0)):
        latency = metrics.get("latency", {})
        lines.append(
            f"| {name} | {metrics['accuracy_pct']} | "
            f"{latency.get('avg', 0):.0f}ms | {latency.get('p95', 0):.0f}ms | "
            f"{metrics.get('errors', 0)} | ${metrics.get('estimated_cost_usd', 0):.4f} |"
        )
    
    lines.append("")
    
    # Per-Folder Accuracy
    lines.append("## 📁 Accuracy by Folder")
    lines.append("")
    
    # Build folder accuracy table
    providers = list(report.get("providers", {}).keys())
    folders = set()
    for p_data in report.get("providers", {}).values():
        folders.update(p_data.get("per_folder", {}).keys())
    
    if providers and folders:
        header = "| Folder | " + " | ".join(providers) + " |"
        separator = "|--------|" + "|".join(["--------"] * len(providers)) + "|"
        lines.append(header)
        lines.append(separator)
        
        for folder in sorted(folders):
            row = f"| {folder} |"
            for provider in providers:
                stats = report["providers"].get(provider, {}).get("per_folder", {}).get(folder, {})
                if stats:
                    acc = stats.get("accuracy", 0)
                    total = stats.get("total", 0)
                    row += f" {acc:.0%} ({total}) |"
                else:
                    row += " - |"
            lines.append(row)
        
        lines.append("")
    
    # Per-Difficulty Accuracy
    lines.append("## 🎚️ Accuracy by Difficulty")
    lines.append("")
    
    difficulties = ["easy", "medium", "hard"]
    if providers:
        header = "| Difficulty | " + " | ".join(providers) + " |"
        separator = "|------------|" + "|".join(["--------"] * len(providers)) + "|"
        lines.append(header)
        lines.append(separator)
        
        for diff in difficulties:
            row = f"| {diff.capitalize()} |"
            for provider in providers:
                stats = report["providers"].get(provider, {}).get("per_difficulty", {}).get(diff, {})
                if stats:
                    acc = stats.get("accuracy", 0)
                    total = stats.get("total", 0)
                    row += f" {acc:.0%} ({total}) |"
                else:
                    row += " - |"
            lines.append(row)
        
        lines.append("")
    
    # Latency Distribution
    lines.append("## ⏱️ Latency Distribution")
    lines.append("")
    lines.append("| Provider | Min | P50 | P95 | P99 | Max |")
    lines.append("|----------|-----|-----|-----|-----|-----|")
    
    for name, metrics in report.get("providers", {}).items():
        lat = metrics.get("latency", {})
        lines.append(
            f"| {name} | {lat.get('min', 0):.0f}ms | {lat.get('p50', 0):.0f}ms | "
            f"{lat.get('p95', 0):.0f}ms | {lat.get('p99', 0):.0f}ms | {lat.get('max', 0):.0f}ms |"
        )
    
    lines.append("")
    
    # Cost Analysis
    lines.append("## 💰 Cost Analysis")
    lines.append("")
    lines.append("Estimated cost per 1000 classifications:")
    lines.append("")
    lines.append("| Provider | Tokens/Email | Cost/1K Emails | Monthly (10K/day) |")
    lines.append("|----------|--------------|----------------|-------------------|")
    
    for name, metrics in report.get("providers", {}).items():
        tokens = metrics.get("tokens_total", 0)
        samples = metrics.get("total_samples", 1)
        avg_tokens = tokens / samples if samples > 0 else 0
        cost = metrics.get("estimated_cost_usd", 0)
        cost_per_1k = (cost / samples * 1000) if samples > 0 else 0
        monthly = cost_per_1k * 10 * 30  # 10K/day * 30 days
        
        lines.append(f"| {name} | {avg_tokens:.0f} | ${cost_per_1k:.2f} | ${monthly:.2f} |")
    
    lines.append("")
    
    # Recommendations
    lines.append("## 💡 Recommendations")
    lines.append("")
    for rec in report.get("recommendations", []):
        lines.append(f"- {rec}")
    
    lines.append("")
    
    # Technical Details
    lines.append("## 🔧 Technical Details")
    lines.append("")
    lines.append("```")
    lines.append(f"Dataset: {report['metadata']['dataset']}")
    lines.append(f"Folders: {', '.join(report['metadata']['folders'])}")
    lines.append(f"Timestamp: {report['metadata']['timestamp']}")
    lines.append("```")
    lines.append("")
    
    markdown = "\n".join(lines)
    
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)
    
    return markdown


def main():
    """Convert JSON report to markdown."""
    if len(sys.argv) < 2:
        print("Usage: python report_generator.py <report.json> [output.md]")
        print("\nConverts JSON benchmark report to markdown format.")
        sys.exit(1)
    
    json_path = sys.argv[1]
    md_path = sys.argv[2] if len(sys.argv) > 2 else json_path.replace(".json", ".md")
    
    with open(json_path, "r", encoding="utf-8") as f:
        report = json.load(f)
    
    generate_markdown_report(report, md_path)
    print(f"Generated: {md_path}")


if __name__ == "__main__":
    main()
