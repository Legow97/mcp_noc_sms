import json
import tempfile
import unittest
from pathlib import Path

from app.core.config import settings
from app.conversation.application.reasoning.reasoning_agent import ReasoningAgent
from app.conversation.application.services.clarification_service import (
    ClarificationAssessment,
)
from app.conversation.contracts.requests import ConversationMode, ConversationRequest
from app.conversation.contracts.responses import (
    ConversationIntent,
    ConversationResponseStatus,
)
from app.conversation.contracts.session_models import (
    ConversationContext,
    ConversationSessionState,
)
from app.conversation.infrastructure.llm.model_gateway import (
    ConversationModelGateway,
    ConversationModelInvocation,
    ConversationModelRawResponse,
)
from app.conversation.infrastructure.prompts.prompt_loader import MarkdownPromptLoader
from app.conversation.infrastructure.research.external_research import (
    ExternalResearchResult,
)


class CapturingConversationModelGateway(ConversationModelGateway):
    def __init__(self, output: dict) -> None:
        self.output = output
        self.last_invocation: ConversationModelInvocation | None = None

    def invoke(
        self,
        invocation: ConversationModelInvocation,
    ) -> ConversationModelRawResponse:
        self.last_invocation = invocation
        return ConversationModelRawResponse(
            model_name=invocation.model_name,
            output_text=json.dumps(self.output, ensure_ascii=False),
            provider_name="test",
        )


class ConversationReasoningAgentTests(unittest.TestCase):
    def test_uses_model_configured_from_settings(self) -> None:
        original_model = settings.conversation_reasoning.model_name
        settings.conversation_reasoning.model_name = "brain-test-model"
        gateway = CapturingConversationModelGateway(
            {
                "intent": "greeting",
                "status": "completed",
                "response_text": "Hola, puedo ayudarte con incidentes.",
                "missing_information": [],
                "follow_up_questions": [],
                "active_incident_ids": [],
                "active_entities": [],
            }
        )
        try:
            agent = ReasoningAgent(model_gateway=gateway)
            result = agent.respond(
                request=ConversationRequest(message="Hola"),
                session_state=ConversationSessionState(session_id="conv-test"),
                context=ConversationContext(
                    session_id="conv-test",
                    mode=ConversationMode.GENERAL,
                    latest_user_message="Hola",
                ),
                clarification=ClarificationAssessment(needs_clarification=True),
                external_research=ExternalResearchResult(),
            )
        finally:
            settings.conversation_reasoning.model_name = original_model

        self.assertEqual(result.intent, ConversationIntent.GREETING)
        self.assertIsNotNone(gateway.last_invocation)
        self.assertEqual(gateway.last_invocation.model_name, "brain-test-model")

    def test_parses_timeline_request_output(self) -> None:
        gateway = CapturingConversationModelGateway(
            {
                "intent": "timeline_request",
                "status": "completed",
                "response_text": (
                    "Entendí que necesitas una línea de tiempo de INC000009209914."
                ),
                "missing_information": [],
                "follow_up_questions": [],
                "active_incident_ids": ["INC000009209914"],
                "active_entities": [],
            }
        )
        agent = ReasoningAgent(
            model_gateway=gateway,
            model_name="test-model",
        )

        result = agent.respond(
            request=ConversationRequest(
                message="Genera línea de tiempo de INC000009209914"
            ),
            session_state=ConversationSessionState(session_id="conv-test"),
            context=ConversationContext(
                session_id="conv-test",
                mode=ConversationMode.GENERAL,
                latest_user_message="Genera línea de tiempo de INC000009209914",
            ),
            clarification=ClarificationAssessment(),
            external_research=ExternalResearchResult(),
        )

        self.assertEqual(result.intent, ConversationIntent.TIMELINE_REQUEST)
        self.assertEqual(result.active_incident_ids, ["INC000009209914"])

    def test_parses_troubleshooting_request_output(self) -> None:
        gateway = CapturingConversationModelGateway(
            {
                "intent": "troubleshooting_request",
                "status": "needs_clarification",
                "response_text": "Entendí el síntoma en APIM y necesito datos de impacto.",
                "missing_information": ["impacto"],
                "follow_up_questions": ["Desde cuándo ocurre y qué servicio impacta?"],
                "active_incident_ids": [],
                "active_entities": ["APIM"],
            }
        )
        agent = ReasoningAgent(
            model_gateway=gateway,
            model_name="test-model",
        )

        result = agent.respond(
            request=ConversationRequest(message="Tengo error connection refused en APIM"),
            session_state=ConversationSessionState(session_id="conv-test"),
            context=ConversationContext(
                session_id="conv-test",
                mode=ConversationMode.GENERAL,
                latest_user_message="Tengo error connection refused en APIM",
            ),
            clarification=ClarificationAssessment(),
            external_research=ExternalResearchResult(),
        )

        self.assertEqual(result.intent, ConversationIntent.TROUBLESHOOTING_REQUEST)
        self.assertEqual(result.status, ConversationResponseStatus.NEEDS_CLARIFICATION)
        self.assertEqual(result.active_entities, ["APIM"])

    def test_loads_instructions_from_markdown_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            prompts_dir = Path(tmp_dir)
            (prompts_dir / "reasoning_agent_system.md").write_text(
                "# System\nUsa reglas conversacionales.",
                encoding="utf-8",
            )
            (prompts_dir / "response_policy.md").write_text(
                "# Policy\nDevuelve JSON.",
                encoding="utf-8",
            )

            loader = MarkdownPromptLoader(str(prompts_dir))
            prompt = loader.load_system_instruction()

        self.assertIn("Usa reglas conversacionales.", prompt)
        self.assertIn("Devuelve JSON.", prompt)


if __name__ == "__main__":
    unittest.main()
