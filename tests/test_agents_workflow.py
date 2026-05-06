from multi_agent_research_lab.agents import SupervisorAgent
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow


def test_supervisor_routes_to_researcher_first() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state = SupervisorAgent().run(state)
    assert state.next_route == "researcher"
    assert state.route_history == ["researcher"]


def test_workflow_produces_final_answer() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems clearly"))
    result = MultiAgentWorkflow().run(state)
    assert result.final_answer is not None
    assert result.route_history
