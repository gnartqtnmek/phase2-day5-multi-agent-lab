"""Benchmark skeleton for single-agent vs multi-agent."""

import re
from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def run_benchmark(
    run_name: str,
    query: str,
    runner: Runner,
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure latency, token-cost proxy, quality rubric, and failure indicators."""

    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started
    citation_coverage = _citation_coverage(state)
    quality = _quality_score(state, citation_coverage=citation_coverage)
    is_failure = 1.0 if (state.final_answer is None or len(state.errors) > 0) else 0.0
    notes_parts = [
        f"iterations={state.iteration}",
        f"routes={','.join(state.route_history)}" if state.route_history else "routes=n/a",
    ]
    if state.errors:
        notes_parts.append(f"errors={'; '.join(state.errors[:2])}")
    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=state.estimated_cost_usd,
        quality_score=quality,
        citation_coverage=citation_coverage,
        failure_rate=is_failure,
        notes=" | ".join(notes_parts),
    )
    return state, metrics


def _citation_coverage(state: ResearchState) -> float:
    if not state.final_answer or not state.sources:
        return 0.0
    cited_sources = 0
    for index, source in enumerate(state.sources, start=1):
        marker = f"[{index}]"
        has_marker = marker in state.final_answer
        has_url = bool(source.url and source.url in state.final_answer)
        if has_marker or has_url:
            cited_sources += 1
    return round(cited_sources / len(state.sources), 3)


def _quality_score(state: ResearchState, citation_coverage: float) -> float:
    score = 0.0
    if state.final_answer:
        score += 4.0
        sections = len(re.findall(r"(?im)^(#{1,6}\\s+|\\w[\\w\\s]+:)", state.final_answer))
        score += min(2.0, sections * 0.5)
    if state.research_notes:
        score += 1.5
    if state.analysis_notes:
        score += 1.5
    score += min(1.0, citation_coverage)
    if state.errors:
        score = max(0.0, score - min(2.0, 0.5 * len(state.errors)))
    return round(min(10.0, score), 2)
