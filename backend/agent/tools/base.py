"""
BaseTool abstract class.

Every clinical tool is a self-contained object that knows its own
Claude tool definition and how to execute itself. The registry
collects them; the agent calls them by name.
"""
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name Claude uses to call this tool."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Plain-English description for the Claude system prompt."""

    @property
    @abstractmethod
    def input_schema(self) -> dict[str, Any]:
        """JSON Schema for the tool's input parameters."""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """Run the tool and return a plain-text result for Claude."""

    def to_claude_definition(self) -> dict[str, Any]:
        """Serialize to the format Claude's API expects."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
