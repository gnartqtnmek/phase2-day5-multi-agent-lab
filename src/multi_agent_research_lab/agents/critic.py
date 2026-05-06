"""Optional critic agent skeleton for bonus work."""

from time import perf_counter

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import record_agent_trace


class CriticAgent(BaseAgent):
    """Optional fact-checking and safety-review agent."""

    name = "critic"

    def run(self, state: ResearchState) -> ResearchState:
        """Validate final answer and append findings."""

        started = perf_counter()
        if not state.final_answer:
            critique = "No final answer to review."
            state.errors.append("critic skipped: final_answer missing")
        else:
            citation_hits = sum(
                1
                for index in range(1, len(state.sources) + 1)
                if f"[{index}]" in state.final_answer
            )
            coverage = 0.0
            if state.sources:
                coverage = citation_hits / len(state.sources)
            critique = (
                f"Citation coverage check: {citation_hits}/{len(state.sources)} "
                f"({coverage:.0%}). Review uncertain claims manually."
            )
        state.agent_results.append(
            AgentResult(agent=AgentName.CRITIC, content=critique, metadata={"auto_check": True})
        )
        record_agent_trace(
            state=state,
            agent_name=self.name,
            input_summary="final answer review",
            output_summary=critique,
            latency_seconds=perf_counter() - started,
        )
        return state
