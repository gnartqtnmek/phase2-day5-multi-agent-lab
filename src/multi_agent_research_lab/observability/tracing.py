"""Tracing hooks.

This file intentionally avoids binding to one provider. Students can plug in LangSmith,
Langfuse, OpenTelemetry, or simple JSON traces.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from logging import getLogger
from time import perf_counter
from typing import Any

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.state import ResearchState

logger = getLogger(__name__)


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Minimal span context with optional provider augmentation."""

    started = perf_counter()
    span: dict[str, Any] = {"name": name, "attributes": attributes or {}, "duration_seconds": None}
    try:
        yield span
    finally:
        span["duration_seconds"] = perf_counter() - started


def summarize_text(text: str | None, limit: int = 220) -> str:
    """Compact text summary for traces."""

    if not text:
        return ""
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3]}..."


def record_agent_trace(
    state: ResearchState,
    agent_name: str,
    input_summary: str,
    output_summary: str,
    latency_seconds: float,
    error: str | None = None,
) -> None:
    """Persist agent-level trace into shared state and optional remote provider."""

    payload = {
        "agent": agent_name,
        "input_summary": summarize_text(input_summary),
        "output_summary": summarize_text(output_summary),
        "latency_seconds": round(latency_seconds, 6),
        "error": error,
    }
    state.add_trace_event("agent_step", payload)
    _emit_langsmith_trace("agent_step", payload)


def _emit_langsmith_trace(
    name: str,
    payload: dict[str, Any],
    settings: Settings | None = None,
) -> None:
    """Best-effort LangSmith logging without hard dependency."""

    cfg = settings or get_settings()
    if not cfg.langsmith_enabled or not cfg.langsmith_api_key:
        return
    try:
        from langsmith import Client
    except Exception:
        logger.debug("LangSmith package not installed; skipping provider trace emission.")
        return

    try:
        client = Client(api_key=cfg.langsmith_api_key)
        client.create_run(
            name=name,
            run_type="tool",
            inputs={"input_summary": payload.get("input_summary", "")},
            outputs={
                "output_summary": payload.get("output_summary", ""),
                "error": payload.get("error"),
            },
            extra={"metadata": payload},
            project_name=cfg.langsmith_project,
        )
    except Exception as exc:
        logger.debug("Failed to emit LangSmith trace: %s", exc)
