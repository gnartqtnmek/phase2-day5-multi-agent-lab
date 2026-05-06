"""Writer agent skeleton."""

from time import perf_counter

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import record_agent_trace, summarize_text
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`."""

        started = perf_counter()
        analysis = state.analysis_notes or (
            "Analysis notes are missing. Derive cautious conclusions only from research notes."
        )
        if state.analysis_notes is None:
            state.errors.append("writer fallback: analysis_notes missing")

        sources_context = "\n".join(
            [
                f"[{index}] {src.title} | {src.url or 'N/A'}\nSnippet: {src.snippet}"
                for index, src in enumerate(state.sources, start=1)
            ]
        )
        try:
            llm_response = self.llm_client.complete(
                system_prompt=(
                    "You are a technical writer. Produce a clear and actionable final answer. "
                    "Every key claim should reference source indices like [1], [2]."
                ),
                user_prompt=(
                    f"Audience: {state.request.audience}\nQuery: {state.request.query}\n\n"
                    f"Research notes:\n{state.research_notes or 'N/A'}\n\n"
                    f"Analysis notes:\n{analysis}\n\n"
                    f"Sources:\n{sources_context or 'No sources available'}\n\n"
                    "Write the final answer with sections: Summary, Details, Caveats, Next steps."
                ),
            )
            final_answer = llm_response.content
            if state.sources and "[" not in final_answer:
                final_answer = f"{final_answer}\n\nSources:\n{_render_source_list(state)}"
            state.final_answer = final_answer
            state.add_usage(
                input_tokens=llm_response.input_tokens,
                output_tokens=llm_response.output_tokens,
                cost_usd=llm_response.cost_usd,
            )
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.WRITER,
                    content=final_answer,
                    metadata={"sources_count": len(state.sources)},
                )
            )
            record_agent_trace(
                state=state,
                agent_name=self.name,
                input_summary=(
                    f"research={summarize_text(state.research_notes)} "
                    f"analysis={summarize_text(state.analysis_notes)}"
                ),
                output_summary=summarize_text(final_answer),
                latency_seconds=perf_counter() - started,
            )
            return state
        except Exception as exc:
            error_msg = f"{self.name} failed: {exc}"
            state.errors.append(error_msg)
            fallback_answer = _fallback_answer(state)
            state.final_answer = fallback_answer
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.WRITER,
                    content=fallback_answer,
                    metadata={"fallback": True, "error": str(exc)},
                )
            )
            record_agent_trace(
                state=state,
                agent_name=self.name,
                input_summary=(
                    f"research={summarize_text(state.research_notes)} "
                    f"analysis={summarize_text(state.analysis_notes)}"
                ),
                output_summary=summarize_text(fallback_answer),
                latency_seconds=perf_counter() - started,
                error=error_msg,
            )
            return state


def _render_source_list(state: ResearchState) -> str:
    lines: list[str] = []
    for index, source in enumerate(state.sources, start=1):
        lines.append(f"[{index}] {source.title} - {source.url or 'N/A'}")
    return "\n".join(lines)


def _fallback_answer(state: ResearchState) -> str:
    answer = "Final answer fallback:\n"
    answer += f"- Query: {state.request.query}\n"
    if state.analysis_notes:
        answer += f"- Analysis summary: {summarize_text(state.analysis_notes, limit=400)}\n"
    elif state.research_notes:
        answer += f"- Research summary: {summarize_text(state.research_notes, limit=400)}\n"
    if state.sources:
        answer += "\nReferences:\n" + _render_source_list(state)
    return answer
