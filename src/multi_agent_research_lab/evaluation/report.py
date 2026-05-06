"""Benchmark report rendering."""

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(
    metrics: list[BenchmarkMetrics],
    test_queries: list[str] | None = None,
    trace_summary: list[str] | None = None,
) -> str:
    """Render benchmark report with lab-friendly sections."""

    lines = [
        "# Benchmark Report",
        "",
        "## Goal",
        "So sanh single-agent baseline va multi-agent workflow.",
        "",
        "## Test Queries",
    ]
    for query_item in test_queries or []:
        lines.append(f"- {query_item}")
    if not test_queries:
        lines.append("- (Not provided)")

    lines.extend(
        [
            "",
            "## Metrics",
            "| Run | Latency | Cost | Quality | Citation coverage | Failure rate | Notes |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for metric in metrics:
        cost = "" if metric.estimated_cost_usd is None else f"{metric.estimated_cost_usd:.4f}"
        quality = "" if metric.quality_score is None else f"{metric.quality_score:.1f}"
        coverage = "" if metric.citation_coverage is None else f"{metric.citation_coverage:.2%}"
        failure_rate = "" if metric.failure_rate is None else f"{metric.failure_rate:.0%}"
        lines.append(
            f"| {metric.run_name} | {metric.latency_seconds:.2f}s | {cost} | {quality} | "
            f"{coverage} | {failure_rate} | {metric.notes} |"
        )

    lines.extend(["", "## Trace Summary"])
    for trace_item in trace_summary or []:
        lines.append(f"- {trace_item}")
    if not trace_summary:
        lines.append("- (Not provided)")

    lines.extend(
        [
            "",
            "## Failure Modes",
            "- Missing API keys or provider package -> fallback to deterministic mock responses.",
            "- Search provider timeout/network errors -> fallback to mock search sources.",
            "- Incomplete intermediate notes -> downstream agents run with conservative "
            "fallback prompts.",
            "- Excessive errors or too many iterations -> supervisor routes to `done` "
            "to avoid infinite loop.",
            "",
            "## Conclusion",
            "Multi-agent phu hop khi bai toan can tach buoc research/analysis/writing "
            "de de kiem soat chat luong, nhung single-agent phu hop hon cho cau hoi "
            "ngan hoac khi can latency thap.",
        ]
    )
    return "\n".join(lines) + "\n"
