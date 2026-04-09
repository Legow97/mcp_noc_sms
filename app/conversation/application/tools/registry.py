from __future__ import annotations

from collections.abc import Iterable

from app.conversation.application.tools.base import ConversationTool


class ToolRegistry:
    """Registro simple para futuras tools del subsistema conversacional."""

    def __init__(self, tools: Iterable[ConversationTool] | None = None) -> None:
        self._tools = {tool.name: tool for tool in tools or []}

    def register(self, tool: ConversationTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ConversationTool | None:
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        return sorted(self._tools)
