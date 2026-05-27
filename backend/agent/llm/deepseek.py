"""
DeepSeekClient — DeepSeek provider implementation.

DeepSeek's API is OpenAI-compatible, so we use the openai SDK
with a custom base_url. Supports DeepSeek v3.x and v4 models
(deepseek-chat, deepseek-reasoner, etc.).

Translation differences vs. Claude:
- One Claude turn with mixed [TextBlock, ToolUseBlock] becomes
  one OpenAI assistant message with `content` + `tool_calls`.
- Claude ToolResult blocks (sent in a user message) become
  separate OpenAI messages with role="tool".
- OpenAI tool definitions wrap the schema in a `function` key.
"""
import json
from typing import Any

from openai import AsyncOpenAI

from .base import LLMClient
from .types import (
    LLMResponse,
    Message,
    StopReason,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)


# OpenAI finish_reason → unified StopReason
_STOP_REASON_MAP: dict[str, StopReason] = {
    "stop": "end_turn",
    "tool_calls": "tool_use",
    "length": "max_tokens",
}


class DeepSeekClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.deepseek.com/v1",
    ) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def create_message(
        self,
        *,
        system: str,
        messages: list[Message],
        tools: list[dict[str, Any]],
        max_tokens: int,
    ) -> LLMResponse:
        native_messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        for msg in messages:
            native_messages.extend(self._message_to_native(msg))

        native_tools = [self._tool_to_native(t) for t in tools]

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": native_messages,
            "max_tokens": max_tokens,
        }
        if native_tools:
            kwargs["tools"] = native_tools
            kwargs["tool_choice"] = "auto"

        response = await self._client.chat.completions.create(**kwargs)
        return self._from_native(response)

    # ------------------------------------------------------------------
    # Unified → OpenAI/DeepSeek
    # ------------------------------------------------------------------

    @staticmethod
    def _message_to_native(msg: Message) -> list[dict[str, Any]]:
        """
        Translate one unified Message into one or more OpenAI messages.

        A unified user message containing ToolResult blocks becomes one
        OpenAI tool-role message per result. A unified assistant message
        with mixed text + tool_use becomes a single OpenAI assistant message.
        """
        if msg.role == "user":
            return DeepSeekClient._user_message_to_native(msg)
        return [DeepSeekClient._assistant_message_to_native(msg)]

    @staticmethod
    def _user_message_to_native(msg: Message) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        text_parts: list[str] = []

        for block in msg.content:
            if isinstance(block, TextBlock):
                text_parts.append(block.text)
            elif isinstance(block, ToolResultBlock):
                out.append({
                    "role": "tool",
                    "tool_call_id": block.tool_use_id,
                    "content": block.content,
                })

        if text_parts:
            out.insert(0, {"role": "user", "content": " ".join(text_parts)})
        return out

    @staticmethod
    def _assistant_message_to_native(msg: Message) -> dict[str, Any]:
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []

        for block in msg.content:
            if isinstance(block, TextBlock):
                text_parts.append(block.text)
            elif isinstance(block, ToolUseBlock):
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input),
                    },
                })

        out: dict[str, Any] = {
            "role": "assistant",
            "content": " ".join(text_parts) if text_parts else None,
        }
        if tool_calls:
            out["tool_calls"] = tool_calls
        return out

    @staticmethod
    def _tool_to_native(tool: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }

    # ------------------------------------------------------------------
    # OpenAI/DeepSeek → Unified
    # ------------------------------------------------------------------

    @staticmethod
    def _from_native(response: Any) -> LLMResponse:
        choice = response.choices[0]
        msg = choice.message
        blocks: list = []

        if msg.content:
            blocks.append(TextBlock(text=msg.content))

        for tc in (msg.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            blocks.append(ToolUseBlock(id=tc.id, name=tc.function.name, input=args))

        stop = _STOP_REASON_MAP.get(choice.finish_reason or "stop", "end_turn")
        return LLMResponse(content=blocks, stop_reason=stop)
