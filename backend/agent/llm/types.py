"""
Provider-agnostic LLM message types.

These types decouple CareAgent from any specific provider SDK.
Each concrete LLMClient subclass is responsible for converting
between this unified format and its provider's native format.

The format follows Claude's content-block model because it
generalises cleanly to OpenAI/DeepSeek (one Claude turn with
mixed text + tool_use maps to one OpenAI assistant message with
content + tool_calls).
"""
from dataclasses import dataclass, field
from typing import Literal, Union

Role = Literal["user", "assistant"]
StopReason = Literal["end_turn", "tool_use", "max_tokens", "stop"]


@dataclass
class TextBlock:
    text: str
    type: Literal["text"] = "text"


@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict
    type: Literal["tool_use"] = "tool_use"


@dataclass
class ToolResultBlock:
    tool_use_id: str
    content: str
    type: Literal["tool_result"] = "tool_result"


ContentBlock = Union[TextBlock, ToolUseBlock, ToolResultBlock]


@dataclass
class Message:
    role: Role
    content: list[ContentBlock] = field(default_factory=list)


@dataclass
class LLMResponse:
    content: list[ContentBlock]
    stop_reason: StopReason

    @property
    def text(self) -> str:
        return " ".join(b.text for b in self.content if isinstance(b, TextBlock))

    @property
    def tool_uses(self) -> list[ToolUseBlock]:
        return [b for b in self.content if isinstance(b, ToolUseBlock)]
