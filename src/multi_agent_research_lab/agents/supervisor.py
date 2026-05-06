"""Supervisor / router skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.state import ResearchState


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route.

        TODO(student): Implement routing policy. Suggested steps:
        - Inspect request, current notes, and missing fields.
        - Choose one of: researcher, analyst, writer, done.
        - Enforce max iterations and failure fallback.
        """

        raise StudentTodoError("TODO(student): implement SupervisorAgent.run")
