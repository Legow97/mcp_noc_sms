from __future__ import annotations

from app.conversation.application.tools.external_research_tool import (
    ExternalResearchTool,
)
from app.conversation.application.tools.registry import ToolRegistry


def build_conversation_tool_registry() -> ToolRegistry:
    """
    Registro mínimo de tools formales disponibles para el subsistema conversacional.
    """

    return ToolRegistry(
        tools=[
            ExternalResearchTool(),
        ]
    )
