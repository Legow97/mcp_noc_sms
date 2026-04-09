from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.conversation.application.reasoning.execution_context import (
    ConversationExecutionContext,
)
from app.conversation.application.tools.base import (
    ConversationTool,
    ToolExecutionStatus,
    ToolResult,
)


class ToolRegistry:
    """Registro simple para futuras tools del subsistema conversacional."""

    def __init__(self, tools: Iterable[ConversationTool] | None = None) -> None:
        self._tools = {tool.name: tool for tool in tools or []}

    def register(self, tool: ConversationTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ConversationTool | None:
        return self._tools.get(name)

    def require(self, name: str) -> ConversationTool:
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Conversation tool not registered: {name}")
        return tool

    def invoke(
        self,
        name: str,
        context: ConversationExecutionContext,
        arguments: dict[str, Any] | None = None,
    ) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                tool_name=name,
                status=ToolExecutionStatus.FAILED,
                errors=[f"Tool not registered: {name}"],
            )

        if not tool.is_enabled(context):
            return ToolResult(
                tool_name=name,
                status=ToolExecutionStatus.DISABLED,
                summary=f"Tool {name} disabled for current context.",
            )

        return tool.execute(context, arguments or {})

    def list_names(self) -> list[str]:
        return sorted(self._tools)
