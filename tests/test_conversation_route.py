import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException

from app.api.routes.conversation import process_conversation_message
from app.conversation.contracts.requests import ConversationMode, ConversationRequest
from app.conversation.contracts.responses import (
    ConversationResponse,
    ConversationResponseStatus,
)


class ConversationRouteTests(unittest.TestCase):
    def test_process_conversation_message_returns_structured_response(self) -> None:
        payload = ConversationRequest(
            message="Necesito contexto del incidente INC-200",
            mode=ConversationMode.GENERAL,
        )
        expected_response = ConversationResponse(
            session_id="conv-123",
            mode=ConversationMode.GENERAL,
            status=ConversationResponseStatus.COMPLETED,
            response_text="Workflow conversacional base inicializado.",
            context_summary=["session_history_messages=0"],
            missing_information=[],
            follow_up_questions=[],
        )

        with patch(
            "app.api.routes.conversation.build_conversation_orchestrator"
        ) as orchestrator_builder:
            orchestrator = Mock()
            orchestrator.handle.return_value = expected_response
            orchestrator_builder.return_value = orchestrator

            response = process_conversation_message(payload, db=Mock())

        self.assertEqual(response.session_id, "conv-123")
        self.assertEqual(response.status, ConversationResponseStatus.COMPLETED)
        orchestrator.handle.assert_called_once_with(payload)

    def test_process_conversation_message_returns_422_for_validation_error(self) -> None:
        with patch(
            "app.api.routes.conversation.build_conversation_orchestrator"
        ) as orchestrator_builder:
            orchestrator = Mock()
            orchestrator.handle.side_effect = ValueError("message no puede estar vacío")
            orchestrator_builder.return_value = orchestrator

            with self.assertRaises(HTTPException) as exc_context:
                process_conversation_message(
                    ConversationRequest(message="texto suficiente"),
                    db=Mock(),
                )

        self.assertEqual(exc_context.exception.status_code, 422)
        self.assertEqual(
            exc_context.exception.detail,
            "message no puede estar vacío",
        )


if __name__ == "__main__":
    unittest.main()
