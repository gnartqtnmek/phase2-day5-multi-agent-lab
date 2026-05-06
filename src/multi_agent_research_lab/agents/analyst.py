"""Analyst agent skeleton."""

from time import perf_counter

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import record_agent_trace, summarize_text
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`."""

        started = perf_counter()
        if not state.research_notes:
            message = "analysis skipped: missing research_notes"
            state.errors.append(message)
            state.analysis_notes = (
                "Insufficient input for deep analysis because research_notes is missing. "
                "Collect sources first."
            )
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.ANALYST,
                    content=state.analysis_notes,
                    metadata={"fallback": True, "reason": "missing_research_notes"},
                )
            )
            record_agent_trace(
                state=state,
                agent_name=self.name,
                input_summary="missing research_notes",
                output_summary=state.analysis_notes,
                latency_seconds=perf_counter() - started,
                error=message,
            )
            return state

        sources_summary = "\n".join(
            [
                f"[{index}] {doc.title} | {doc.url or 'N/A'}"
                for index, doc in enumerate(state.sources, start=1)
            ]
        )
        try:
            llm_response = self.llm_client.complete(
                system_prompt=(
                    "You are an analytical reviewer. Evaluate evidence quality and "
                    "identify blind spots. "
                    "Stay grounded in provided sources."
                ),
                user_prompt=(
                    f"Query: {state.request.query}\n\nResearch notes:\n{state.research_notes}\n\n"
                    f"Sources:\n{sources_summary}\n\n"
                    "Provide sections:\n"
                    "1) Key claims\n2) Evidence strength\n3) Missing information\n"
                    "4) Comparison of viewpoints (if multiple perspectives exist)."
                ),
            )
            state.analysis_notes = llm_response.content
            state.add_usage(
                input_tokens=llm_response.input_tokens,
                output_tokens=llm_response.output_tokens,
                cost_usd=llm_response.cost_usd,
            )
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.ANALYST,
                    content=state.analysis_notes,
                    metadata={"sources_count": len(state.sources)},
                )
            )
            record_agent_trace(
                state=state,
                agent_name=self.name,
                input_summary=f"research_notes={summarize_text(state.research_notes)}",
                output_summary=summarize_text(state.analysis_notes),
                latency_seconds=perf_counter() - started,
            )
            return state
        except Exception as exc:
            error_msg = f"{self.name} failed: {exc}"
            fallback = (
                "Fallback analysis:\n"
                "- Key claims: could not compute reliably.\n"
                "- Evidence strength: unknown.\n"
                "- Missing information: additional sources required.\n"
                "- Comparison of viewpoints: not available."
            )
            state.errors.append(error_msg)
            state.analysis_notes = fallback
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.ANALYST,
                    content=fallback,
                    metadata={"fallback": True, "error": str(exc)},
                )
            )
            record_agent_trace(
                state=state,
                agent_name=self.name,
                input_summary=f"research_notes={summarize_text(state.research_notes)}",
                output_summary=summarize_text(fallback),
                latency_seconds=perf_counter() - started,
                error=error_msg,
            )
            return state
