"""Search client abstraction for ResearcherAgent."""

import json
import re
from hashlib import sha256
from logging import getLogger
from urllib.error import URLError
from urllib.request import Request, urlopen

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.schemas import SourceDocument

logger = getLogger(__name__)


class SearchClient:
    """Provider-agnostic search client with Tavily + deterministic fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query."""

        max_results = max(1, min(max_results, 20))
        if self.settings.tavily_api_key:
            try:
                return self._search_tavily(query=query, max_results=max_results)
            except Exception as exc:
                logger.warning("Tavily search failed, fallback to mock provider: %s", exc)
        return self._search_mock(query=query, max_results=max_results)

    def _search_tavily(self, query: str, max_results: int) -> list[SourceDocument]:
        payload = {
            "api_key": self.settings.tavily_api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        }
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url="https://api.tavily.com/search",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        timeout = float(self.settings.timeout_seconds)
        try:
            with urlopen(request, timeout=timeout) as response:
                response_body = response.read().decode("utf-8")
        except URLError as exc:
            raise RuntimeError(f"Tavily request failed: {exc}") from exc

        data = json.loads(response_body)
        raw_results = data.get("results", [])
        if not isinstance(raw_results, list):
            return []

        documents: list[SourceDocument] = []
        for index, item in enumerate(raw_results[:max_results], start=1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "Untitled source")
            url = item.get("url")
            snippet = str(item.get("content") or item.get("snippet") or "")
            metadata = {
                "provider": "tavily",
                "rank": index,
                "score": item.get("score"),
                "published_date": item.get("published_date"),
            }
            documents.append(
                SourceDocument(
                    title=title,
                    url=str(url) if isinstance(url, str) and url else None,
                    snippet=snippet[:1200],
                    metadata=metadata,
                )
            )
        return documents

    @staticmethod
    def _search_mock(query: str, max_results: int) -> list[SourceDocument]:
        slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-") or "query"
        digest = sha256(query.encode("utf-8")).hexdigest()
        documents: list[SourceDocument] = []
        for index in range(1, max_results + 1):
            chunk = digest[(index - 1) * 6 : (index - 1) * 6 + 6]
            score = int(chunk, 16) / 0xFFFFFF if chunk else 0.5
            documents.append(
                SourceDocument(
                    title=f"Mock source {index} for {query}",
                    url=f"https://example.com/{slug}/{index}",
                    snippet=(
                        f"Deterministic mock snippet {index} for query '{query}'. "
                        "This placeholder keeps pipeline behavior stable "
                        "when no search API key is set."
                    ),
                    metadata={"provider": "mock", "rank": index, "score": round(score, 4)},
                )
            )
        return documents
