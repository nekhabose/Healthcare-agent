"""
ToolRegistry — central registry for all clinical tools.

Usage:
    registry = ToolRegistry()
    registry.register(SymptomTool(session_repo, escalation_repo))
    registry.register(MedicationTool(session_repo))

    # Get all definitions for Claude
    definitions = registry.definitions

    # Execute a tool by name
    result = await registry.execute("assess_symptom", symptom="chest pain", severity=9)
"""
from typing import Any

from exceptions import ToolExecutionError
from .base import BaseTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return [t.to_claude_definition() for t in self._tools.values()]

    async def execute(self, name: str, **kwargs: Any) -> str:
        tool = self._tools.get(name)
        if not tool:
            raise ToolExecutionError(name, f"tool '{name}' is not registered")
        try:
            return await tool.execute(**kwargs)
        except Exception as exc:
            raise ToolExecutionError(name, str(exc)) from exc
