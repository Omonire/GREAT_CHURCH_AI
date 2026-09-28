"""Optional server-side generation.

Disabled by default. When ``AI_PROVIDER_BASE_URL`` and ``AI_PROVIDER_API_KEY``
are set, this talks to any OpenAI-compatible ``/chat/completions`` endpoint so
generation can move off the browser. Nothing here is required for the product
to work.

The key is read from the environment and is never logged, echoed, or returned.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from church_ai_api.ai.context import PreparedPrompt
from church_ai_api.config import Settings, get_settings

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """Raised when the upstream model provider fails."""


class ServerProvider:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return self.settings.server_side_ai_enabled

    def complete(self, prompt: PreparedPrompt) -> str:
        if not self.enabled:
            raise ProviderError("Server-side AI is not configured.")

        payload = {
            "model": self.settings.ai_model,
            "messages": [
                {"role": "system", "content": prompt.system},
                *[
                    {"role": turn.role, "content": turn.content}
                    for turn in prompt.messages
                ],
            ],
            "temperature": 0.7,
        }

        url = self.settings.ai_provider_base_url.rstrip("/") + "/chat/completions"
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.ai_provider_api_key}",
                "User-Agent": "GreatChurchAI/0.2",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.settings.ai_timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            logger.warning("AI provider returned HTTP %s", error.code)
            raise ProviderError("The AI provider rejected the request.") from error
        except urllib.error.URLError as error:
            logger.warning("AI provider unreachable: %s", error.reason)
            raise ProviderError("The AI provider could not be reached.") from error
        except TimeoutError as error:
            raise ProviderError("The AI provider timed out.") from error

        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise ProviderError("The AI provider returned an unexpected response.") from error

        if not isinstance(content, str) or not content.strip():
            raise ProviderError("The AI provider returned an empty response.")

        return content.strip()
