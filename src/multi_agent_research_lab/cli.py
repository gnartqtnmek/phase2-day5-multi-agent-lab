"""Command-line entrypoint for the lab starter."""

from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.storage import LocalArtifactStore

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


def _run_baseline_state(query: str) -> ResearchState:
    request = ResearchQuery(query=query)
    state = ResearchState(request=request)
    llm_client = LLMClient()
    response = llm_client.complete(
        system_prompt=(
            "You are a research assistant. Do research, analysis, and writing in one answer. "
            "Be explicit about uncertainty."
        ),
        user_prompt=(
            f"Query: {request.query}\nAudience: {request.audience}\n"
            "Return a concise and structured response."
        ),
    )
    state.final_answer = response.content
    state.add_usage(response.input_tokens, response.output_tokens, response.cost_usd)
    return state


def _run_multi_agent_state(query: str) -> ResearchState:
    state = ResearchState(request=ResearchQuery(query=query))
    workflow = MultiAgentWorkflow()
    return workflow.run(state)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run single-agent baseline with one LLM call."""

    _init()
    state = _run_baseline_state(query)
    console.print(Panel.fit(state.final_answer or "", title="Single-Agent Baseline"))
    if state.estimated_cost_usd is not None:
        console.print(f"Estimated cost: ${state.estimated_cost_usd:.6f}")


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow."""

    _init()
    result = _run_multi_agent_state(query)
    console.print(result.model_dump_json(indent=2))


@app.command("benchmark")
def benchmark() -> None:
    """Benchmark baseline and multi-agent workflow and persist markdown report."""

    _init()
    queries = [
        "Research GraphRAG state-of-the-art and summarize practical tradeoffs.",
        "Compare vector databases for enterprise RAG deployment in 2026.",
        "What are robust evaluation strategies for multi-agent research assistants?",
    ]
    metrics = []
    trace_summary: list[str] = []
    for query in queries:
        baseline_state, baseline_metrics = run_benchmark(
            run_name=f"baseline:{query[:24]}",
            query=query,
            runner=_run_baseline_state,
        )
        multi_state, multi_metrics = run_benchmark(
            run_name=f"multi-agent:{query[:24]}",
            query=query,
            runner=_run_multi_agent_state,
        )
        metrics.extend([baseline_metrics, multi_metrics])
        trace_summary.append(
            f"{query[:48]}... | baseline routes={baseline_state.route_history or ['single']} "
            f"| multi routes={multi_state.route_history}"
        )

    report = render_markdown_report(
        metrics=metrics,
        test_queries=queries,
        trace_summary=trace_summary,
    )
    path = LocalArtifactStore().write_text("benchmark_report.md", report)
    console.print(Panel.fit(f"Benchmark report written to: {path}", title="Benchmark"))


if __name__ == "__main__":
    app()
