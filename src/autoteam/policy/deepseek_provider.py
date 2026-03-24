"""DeepSeek Judge Provider.

Uses DeepSeek API (OpenAI-compatible) for Judge decisions.
"""

import asyncio
import json
import time
from typing import Any

import httpx

from autoteam.contracts import JudgeDecision
from autoteam.policy.base_provider import (
    BaseJudgeProvider,
    JudgeProviderConfig,
    JudgeProviderType,
    JudgeRequest,
    JudgeResponse,
)


# DeepSeek API defaults
DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_DEFAULT_MODEL = "deepseek-chat"


class DeepSeekJudgeProvider(BaseJudgeProvider):
    """Judge provider using DeepSeek API.
    
    DeepSeek API is OpenAI-compatible, making it easy to use.
    Good balance of cost and capability for Judge decisions.
    
    Environment variable: DEEPSEEK_API_KEY
    """

    def __init__(self, config: JudgeProviderConfig | None = None):
        if config is None:
            config = JudgeProviderConfig(
                provider_type=JudgeProviderType.DEEPSEEK,
            )
        super().__init__(config)
        
        self._api_base = config.api_base or DEEPSEEK_API_BASE
        self._model = config.model or DEEPSEEK_DEFAULT_MODEL
        self._api_key = config.api_key or self._get_api_key()

    def _get_api_key(self) -> str:
        """Get API key from environment."""
        import os
        key = os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise ValueError(
                "DEEPSEEK_API_KEY environment variable not set. "
                "Get your API key from https://platform.deepseek.com/"
            )
        return key

    @property
    def name(self) -> str:
        return f"DeepSeek ({self._model})"

    async def judge(self, request: JudgeRequest) -> JudgeResponse:
        """Evaluate evidence using DeepSeek API."""
        start_time = time.monotonic()

        try:
            # Build messages
            messages = [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": self._build_user_prompt(request)},
            ]

            # Make API request
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.post(
                    f"{self._api_base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "messages": messages,
                        "temperature": self.config.temperature,
                        "max_tokens": self.config.max_tokens,
                        "response_format": {"type": "json_object"},
                    },
                )
                response.raise_for_status()
                data = response.json()

            latency = time.monotonic() - start_time

            # Extract response
            raw_content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            # Parse decision
            decision = self._parse_decision(raw_content)

            return JudgeResponse(
                decision=decision,
                raw_response=raw_content,
                success=decision is not None,
                error=None if decision else "Failed to parse decision",
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                latency_seconds=latency,
            )

        except httpx.HTTPStatusError as e:
            return JudgeResponse(
                decision=None,
                raw_response=str(e.response.text if e.response else ""),
                success=False,
                error=f"HTTP error {e.response.status_code}: {e.response.text[:200]}",
                latency_seconds=time.monotonic() - start_time,
            )
        except Exception as e:
            return JudgeResponse(
                decision=None,
                raw_response="",
                success=False,
                error=str(e),
                latency_seconds=time.monotonic() - start_time,
            )

    def _parse_decision(self, raw: str) -> JudgeDecision | None:
        """Parse Judge decision from raw response."""
        try:
            # Try direct JSON parse
            data = json.loads(raw.strip())
            return JudgeDecision.from_dict(data)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                    return JudgeDecision.from_dict(data)
                except (json.JSONDecodeError, KeyError):
                    pass
        except KeyError as e:
            # Missing required field
            return None
        return None

    async def health_check(self) -> tuple[bool, str]:
        """Check DeepSeek API availability."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    f"{self._api_base}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                if response.status_code == 200:
                    return True, "DeepSeek API available"
                elif response.status_code == 401:
                    return False, "Invalid API key"
                else:
                    return False, f"API returned status {response.status_code}"
        except Exception as e:
            return False, f"Connection failed: {e}"


def create_deepseek_judge(
    api_key: str | None = None,
    model: str = DEEPSEEK_DEFAULT_MODEL,
    temperature: float = 0.1,
) -> DeepSeekJudgeProvider:
    """Factory function to create DeepSeek Judge provider.
    
    Args:
        api_key: DeepSeek API key (or use DEEPSEEK_API_KEY env var)
        model: Model to use (default: deepseek-chat)
        temperature: Sampling temperature (default: 0.1 for consistency)
        
    Returns:
        Configured DeepSeekJudgeProvider
    """
    config = JudgeProviderConfig(
        provider_type=JudgeProviderType.DEEPSEEK,
        api_key=api_key,
        model=model,
        temperature=temperature,
    )
    return DeepSeekJudgeProvider(config)
