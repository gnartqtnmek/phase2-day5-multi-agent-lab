"""LangGraph workflow skeleton."""

from time import time

from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.state import ResearchState


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.supervisor = SupervisorAgent(settings=self.settings)
        self.researcher = ResearcherAgent()
        self.analyst = AnalystAgent()
        self.writer = WriterAgent()

    def build(self) -> object:
        """Create a graph descriptor.

        The implementation uses a deterministic loop runner for reliability when LangGraph
        is unavailable, while preserving a graph-like interface.
        """

        return {
            "nodes": ["supervisor", "researcher", "analyst", "writer"],
            "routes": {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "done": "done",
            },
            "max_iterations": self.settings.max_iterations,
        }

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the workflow and return final state."""

        _ = self.build()
        if state.started_at is None:
            state.started_at = time()

        hard_limit = self.settings.max_iterations + 3
        for _step in range(hard_limit):
            state = self.supervisor.run(state)
            route = state.next_route or "done"
            if route == "done":
                break
            if route == "researcher":
                state = self.researcher.run(state)
                continue
            if route == "analyst":
                state = self.analyst.run(state)
                continue
            if route == "writer":
                state = self.writer.run(state)
                continue

            state.errors.append(f"Unknown route from supervisor: {route}")
            state.record_route("done")
            break
        else:
            state.errors.append("Workflow stopped by hard iteration limit.")
            state.record_route("done")

        state.completed_at = time()
        return state
