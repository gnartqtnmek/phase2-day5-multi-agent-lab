"""Researcher agent skeleton."""

from time import perf_counter, time

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import record_agent_trace, summarize_text
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        search_client: SearchClient | None = None,
    ) -> None:
        self.llm_client = llm_client or LLMClient()
        self.search_client = search_client or SearchClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""

        started = perf_counter()
        if state.started_at is None:
            state.started_at = time()

        query = state.request.query
        try:
            sources = self.search_client.search(query=query, max_results=state.request.max_sources)
            state.sources = sources

            sources_context = _format_sources_for_prompt(sources)
            llm_response = self.llm_client.complete(
                system_prompt=(
                    "You are a rigorous research assistant. Summarize evidence faithfully and cite "
                    "source indices like [1], [2] when making claims."
                ),
                user_prompt=(
                    f"Research query: {query}\n\nSources:\n{sources_context}\n\n"
                    "Return concise research notes with: (1) key facts (2) what is uncertain "
                    "(3) source-backed observations."
                ),
            )
            state.research_notes = llm_response.content
            state.add_usage(
                input_tokens=llm_response.input_tokens,
                output_tokens=llm_response.output_tokens,
                cost_usd=llm_response.cost_usd,
            )
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.RESEARCHER,
                    content=state.research_notes,
                    metadata={"sources_count": len(sources)},
                )
            )
            record_agent_trace(
                state=state,
                agent_name=self.name,
                input_summary=f"query={query}; max_sources={state.request.max_sources}",
                output_summary=(
                    f"sources={len(sources)}; "
                    f"notes={summarize_text(state.research_notes)}"
                ),
                latency_seconds=perf_counter() - started,
            )
            return state
        except Exception as exc:
            error_msg = f"{self.name} failed: {exc}"
            state.errors.append(error_msg)
            fallback_notes = _fallback_notes(state)
            state.research_notes = fallback_notes
            state.agent_results.append(
                AgentResult(
                    agent=AgentName.RESEARCHER,
                    content=fallback_notes,
                    metadata={"fallback": True, "error": str(exc)},
                )
            )
            record_agent_trace(
                state=state,
                agent_name=self.name,
                input_summary=f"query={query}; max_sources={state.request.max_sources}",
                output_summary=summarize_text(fallback_notes),
                latency_seconds=perf_counter() - started,
                error=error_msg,
            )
            return state


def _format_sources_for_prompt(sources: list[SourceDocument]) -> str:
    if not sources:
        return "No sources available."
    lines: list[str] = []
    for index, source in enumerate(sources, start=1):
        url = source.url or "N/A"
        lines.append(f"[{index}] {source.title} | {url}\nSnippet: {source.snippet}")
    return "\n\n".join(lines)


def _fallback_notes(state: ResearchState) -> str:
    if not state.sources:
        return (
            "Unable to gather external sources. "
            "Use baseline reasoning and mark uncertainty clearly."
        )
    snippets = []
    for index, source in enumerate(state.sources[:3], start=1):
        snippets.append(f"[{index}] {source.title}: {source.snippet}")
    return "Fallback research notes based on available snippets:\n" + "\n".join(snippets)
