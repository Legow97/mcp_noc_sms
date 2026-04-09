from __future__ import annotations

from app.core.config import settings
from app.conversation.application.reasoning.execution_context import (
    ConversationExecutionContext,
)
from app.conversation.application.tools.base import ConversationTool, ToolResult
from app.conversation.infrastructure.research.external_research import (
    ExternalResearchResult,
    ExternalResearchService,
)


class ExternalResearchTool(ConversationTool):
    """
    Tool formal para investigación externa controlada por policy y sanitización.
    """

    name = "external_research"
    description = "Consulta controlada de fuentes externas permitidas."

    def __init__(
        self,
        research_service: ExternalResearchService | None = None,
    ) -> None:
        self._research_service = research_service or ExternalResearchService()

    def is_enabled(self, context: ConversationExecutionContext) -> bool:
        if not settings.features.allow_external_sources:
            return False

        requested = {capability.strip().lower() for capability in context.enabled_tools}
        if not requested:
            return True

        return self.name in requested

    def execute(
        self,
        context: ConversationExecutionContext,
        arguments: dict[str, object] | None = None,
    ) -> ToolResult:
        result = self._research_service.research(
            request=context.request,
            context=context.context,
            session_state=context.session_state,
            clarification=context.clarification_assessment,
            arguments=arguments or {},
        )
        return result.to_tool_result(self.name)

    @staticmethod
    def empty_result() -> ExternalResearchResult:
        return ExternalResearchResult()
