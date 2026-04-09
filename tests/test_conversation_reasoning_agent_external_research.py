import unittest

from app.core.config import settings
from app.conversation.application.reasoning.execution_context import (
    ConversationExecutionContext,
)
from app.conversation.application.reasoning.reasoning_agent import ReasoningAgent
from app.conversation.application.services.clarification_service import (
    ClarificationAssessment,
)
from app.conversation.application.tools.base import (
    ConversationTool,
    ToolExecutionStatus,
    ToolResult,
)
from app.conversation.application.tools.registry import ToolRegistry
from app.conversation.contracts.requests import ConversationMode, ConversationRequest
from app.conversation.contracts.session_models import (
    ConversationContext,
    ConversationSessionState,
)
from app.conversation.infrastructure.llm.model_gateway import (
    ConversationModelGateway,
    ConversationModelInvocation,
    ConversationModelRawResponse,
)
from app.conversation.infrastructure.research.external_research import (
    ExternalResearchResult,
    ExternalResearchSource,
)


class FailingConversationModelGateway(ConversationModelGateway):
    def invoke(
        self,
        invocation: ConversationModelInvocation,
    ) -> ConversationModelRawResponse:
        raise RuntimeError("provider down")


class FakeExternalResearchTool(ConversationTool):
    name = "external_research"

    def __init__(self) -> None:
        self.called = False

    def is_enabled(self, context: ConversationExecutionContext) -> bool:
        return True

    def execute(
        self,
        context: ConversationExecutionContext,
        arguments: dict | None = None,
    ) -> ToolResult:
        self.called = True
        result = ExternalResearchResult(
            enabled=True,
            attempted=True,
            used=True,
            status="completed",
            findings=["AWS Docs (docs.aws.amazon.com): Guía oficial de memory GC."],
            sources=[
                ExternalResearchSource(
                    title="AWS Docs",
                    url="https://docs.aws.amazon.com/example",
                    domain="docs.aws.amazon.com",
                    snippet="Guía oficial de memory GC.",
                    category="whitelist",
                )
            ],
        )
        return ToolResult(
            tool_name=self.name,
            status=ToolExecutionStatus.COMPLETED,
            data=result.model_dump(mode="json"),
        )


class ReasoningAgentExternalResearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_flag = settings.features.allow_external_sources
        settings.features.allow_external_sources = True

    def tearDown(self) -> None:
        settings.features.allow_external_sources = self.original_flag

    def test_agent_invokes_external_research_tool_when_user_requests_official_docs(self) -> None:
        tool = FakeExternalResearchTool()
        agent = ReasoningAgent(
            model_gateway=FailingConversationModelGateway(),
            tool_registry=ToolRegistry([tool]),
            model_name="test-model",
        )

        result = agent.respond(
            request=ConversationRequest(
                message="Puedes consultar documentación oficial de AWS para esto?",
                requested_capabilities=["external_research"],
            ),
            session_state=ConversationSessionState(session_id="conv-test"),
            context=ConversationContext(
                session_id="conv-test",
                mode=ConversationMode.GENERAL,
                latest_user_message="Puedes consultar documentación oficial de AWS para esto?",
            ),
            clarification=ClarificationAssessment(),
        )

        self.assertTrue(tool.called)
        self.assertIn("fuentes externas", result.response_text.lower())
        self.assertIn("AWS Docs", result.response_text)


if __name__ == "__main__":
    unittest.main()
