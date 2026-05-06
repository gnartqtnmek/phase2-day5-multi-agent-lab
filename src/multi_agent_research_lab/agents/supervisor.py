"""Supervisor / router skeleton."""

from time import perf_counter

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import record_agent_trace


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def run(self, state: ResearchState) -> ResearchState:
        """Update route using deterministic policy with stop conditions."""

        started = perf_counter()
        route = self._decide_route(state)
        state.record_route(route)
        record_agent_trace(
            state=state,
            agent_name=self.name,
            input_summary=(
                f"iteration={state.iteration} research_notes={bool(state.research_notes)} "
                f"analysis_notes={bool(state.analysis_notes)} "
                f"final_answer={bool(state.final_answer)} "
                f"errors={len(state.errors)}"
            ),
            output_summary=f"next_route={route}",
            latency_seconds=perf_counter() - started,
        )
        return state

    def _decide_route(self, state: ResearchState) -> str:
        if len(state.errors) >= 4:
            if not state.final_answer and state.analysis_notes:
                return "writer"
            return "done"
        if state.iteration >= self.settings.max_iterations:
            return "done"
        if not state.research_notes:
            return "researcher"
        if not state.analysis_notes:
            return "analyst"
        if not state.final_answer:
            return "writer"
        return "done"
