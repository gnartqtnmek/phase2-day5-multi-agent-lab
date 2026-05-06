"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

from dataclasses import dataclass
from hashlib import sha256
from logging import getLogger
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import Settings, get_settings

logger = getLogger(__name__)

_MODEL_PRICING_PER_1M: dict[str, tuple[float, float]] = {
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1-nano": (0.10, 0.40),
}


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Provider-agnostic LLM client skeleton."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion from OpenAI with safe fallback."""

        if not self.settings.openai_api_key:
            return self._mock_response(system_prompt=system_prompt, user_prompt=user_prompt)

        try:
            return self._complete_with_retry(system_prompt=system_prompt, user_prompt=user_prompt)
        except Exception as exc:
            logger.warning("LLM request failed, using deterministic fallback: %s", exc)
            return self._mock_response(system_prompt=system_prompt, user_prompt=user_prompt)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(RuntimeError),
        reraise=True,
    )
    def _complete_with_retry(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        return self._call_openai(system_prompt=system_prompt, user_prompt=user_prompt)

    def _call_openai(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        try:
            from openai import OpenAI
        except Exception as exc:
            raise RuntimeError("OpenAI SDK is not installed.") from exc

        try:
            client = OpenAI(
                api_key=self.settings.openai_api_key,
                timeout=float(self.settings.timeout_seconds),
            )
            response = client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
        except Exception as exc:
            raise RuntimeError(f"OpenAI completion call failed: {exc}") from exc

        content = self._extract_content(response)
        input_tokens = self._extract_token_count(response, "prompt_tokens")
        output_tokens = self._extract_token_count(response, "completion_tokens")
        cost_usd = self._estimate_cost_usd(
            model=self.settings.openai_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
        )

    def _mock_response(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        digest = sha256(f"{system_prompt}\n{user_prompt}".encode()).hexdigest()[:10]
        content = (
            "Mock LLM response (no API key or provider unavailable).\n"
            f"Digest: {digest}\n"
            f"Prompt: {user_prompt.strip()[:320]}"
        )
        estimated_input = max(1, len(system_prompt.split()) + len(user_prompt.split()))
        estimated_output = max(1, len(content.split()))
        return LLMResponse(
            content=content,
            input_tokens=estimated_input,
            output_tokens=estimated_output,
            cost_usd=0.0,
        )

    @staticmethod
    def _extract_content(response: Any) -> str:
        choices = getattr(response, "choices", None)
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        if message is None:
            return ""
        content = getattr(message, "content", "")
        return content if isinstance(content, str) else ""

    @staticmethod
    def _extract_token_count(response: Any, field_name: str) -> int | None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return None
        value = getattr(usage, field_name, None)
        return value if isinstance(value, int) else None

    @staticmethod
    def _estimate_cost_usd(
        model: str,
        input_tokens: int | None,
        output_tokens: int | None,
    ) -> float | None:
        pricing = _MODEL_PRICING_PER_1M.get(model)
        if pricing is None or input_tokens is None or output_tokens is None:
            return None
        input_rate, output_rate = pricing
        cost = (input_tokens / 1_000_000 * input_rate) + (output_tokens / 1_000_000 * output_rate)
        return round(cost, 8)
