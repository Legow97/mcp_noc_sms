import unittest

from app.conversation.application.reasoning.execution_context import (
    ConversationExecutionContext,
)
from app.conversation.application.tools.base import (
    ConversationTool,
    ToolExecutionStatus,
    ToolResult,
)
from app.conversation.application.tools.registry import ToolRegistry
from app.conversation.contracts.requests import ConversationRequest
from app.conversation.contracts.session_models import (
    ConversationContext,
    ConversationSessionState,
)


class DummyTool(ConversationTool):
    name = "dummy"

    def is_enabled(self, context: ConversationExecutionContext) -> bool:
        return True

    def execute(
        self,
        context: ConversationExecutionContext,
        arguments: dict | None = None,
    ) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            status=ToolExecutionStatus.COMPLETED,
            data={"echo": arguments or {}},
        )


class ConversationToolRegistryTests(unittest.TestCase):
    def test_registry_invokes_registered_tool(self) -> None:
        registry = ToolRegistry([DummyTool()])
        context = ConversationExecutionContext(
            request=ConversationRequest(message="hola"),
            session_state=ConversationSessionState(session_id="conv-1"),
            context=ConversationContext(
                session_id="conv-1",
                mode="general",
                latest_user_message="hola",
            ),
        )

        result = registry.invoke("dummy", context=context, arguments={"a": 1})

        self.assertEqual(result.status, ToolExecutionStatus.COMPLETED)
        self.assertEqual(result.data["echo"]["a"], 1)


if __name__ == "__main__":
    unittest.main()
