"""Search client abstraction for ResearcherAgent."""

from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import SourceDocument


class SearchClient:
    """Provider-agnostic search client skeleton."""

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query.

        TODO(student): Implement with Tavily, Bing, SerpAPI, internal docs, or a local mock.
        """

        raise StudentTodoError("TODO(student): implement SearchClient.search")
