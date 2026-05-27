"""
LLMClient — abstract base for all LLM providers.

Add a new provider by:
  1. Subclassing LLMClient
  2. Implementing create_message() with provider-native API calls
  3. Registering the subclass in factory.py

CareAgent is the only consumer; it never imports a concrete client.
"""
from abc import ABC, abstractmethod
from typing import Any

from .types import LLMResponse, Message


class LLMClient(ABC):
    @abstractmethod
    async def create_message(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[dict[str, Any]],
        max_tokens: int,
    ) -> LLMResponse:
        """
        Run one turn of the conversation.

        Args:
            system: System prompt.
            messages: Full conversation history in unified format.
            tools: Tool definitions in unified format (BaseTool.to_claude_definition()).
            max_tokens: Generation cap.

        Returns:
            LLMResponse with content blocks and a stop_reason.
        """
