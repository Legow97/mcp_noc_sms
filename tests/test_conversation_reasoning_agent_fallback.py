import unittest

from app.conversation.clarification import ClarificationAssessment
from app.conversation.contracts.requests import ConversationMode, ConversationRequest
from app.conversation.contracts.historical_context import (
    ConversationHistoricalContext,
    SemanticSearchMatchSnapshot,
)
from app.conversation.contracts.responses import ConversationIntent
from app.conversation.contracts.responses import ConversationResponseStatus
from app.conversation.contracts.session_models import (
    ConversationContext,
    ConversationSessionState,
)
from app.conversation.external_research import ExternalResearchResult
from app.conversation.model_gateway import (
    ConversationModelGateway,
    ConversationModelInvocation,
    ConversationModelRawResponse,
)
from app.conversation.reasoning_agent import ReasoningAgent


class FailingConversationModelGateway(ConversationModelGateway):
    def invoke(
        self,
        invocation: ConversationModelInvocation,
    ) -> ConversationModelRawResponse:
        raise RuntimeError("provider down")


class ConversationReasoningAgentFallbackTests(unittest.TestCase):
    def test_falls_back_to_controlled_response_when_llm_fails(self) -> None:
        agent = ReasoningAgent(
            model_gateway=FailingConversationModelGateway(),
            model_name="test-model",
        )

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

        self.assertEqual(result.intent, ConversationIntent.GREETING)
        self.assertIn("Hola", result.response_text)

    def test_fallback_uses_semantic_matches_without_placeholder(self) -> None:
        agent = ReasoningAgent(
            model_gateway=FailingConversationModelGateway(),
            model_name="test-model",
        )

        result = agent.respond(
            request=ConversationRequest(
                message="Tengo error connection refused en APIM"
            ),
            session_state=ConversationSessionState(session_id="conv-test"),
            context=ConversationContext(
                session_id="conv-test",
                mode=ConversationMode.GENERAL,
                latest_user_message="Tengo error connection refused en APIM",
                historical_context=ConversationHistoricalContext(
                    semantic_query_source="user_message",
                    semantic_matches=[
                        SemanticSearchMatchSnapshot(
                            case_id="INC0001",
                            document_version="v1",
                            document_text=(
                                "APIM connection refused resuelto reiniciando gateway"
                            ),
                            distance=0.12,
                        )
                    ],
                ),
            ),
            clarification=ClarificationAssessment(),
            external_research=ExternalResearchResult(),
        )

        self.assertEqual(result.intent, ConversationIntent.TROUBLESHOOTING_REQUEST)
        self.assertIn("evidencia histórica real", result.response_text)
        self.assertIn("INC0001", result.response_text)
        self.assertNotIn("integrarlo luego", result.response_text)
        self.assertEqual(result.latest_historical_matches, ["INC0001"])

    def test_fallback_guides_ambiguous_troubleshooting_with_specific_questions(
        self,
    ) -> None:
        agent = ReasoningAgent(
            model_gateway=FailingConversationModelGateway(),
            model_name="test-model",
        )

        result = agent.respond(
            request=ConversationRequest(message="No funciona la API"),
            session_state=ConversationSessionState(session_id="conv-test"),
            context=ConversationContext(
                session_id="conv-test",
                mode=ConversationMode.GENERAL,
                latest_user_message="No funciona la API",
            ),
            clarification=ClarificationAssessment(
                needs_clarification=True,
                sufficiency_level="sufficient_for_history",
                is_troubleshooting=True,
                known_information={
                    "service_or_component": "API",
                    "symptom": "no funciona",
                },
                missing_information=[
                    "entorno",
                    "alcance",
                    "validaciones_realizadas",
                    "hora_aproximada",
                ],
                follow_up_questions=[
                    "Ocurre en producción, QA u otro entorno?",
                    "Afecta una sola API/servicio o varios?",
                ],
            ),
            external_research=ExternalResearchResult(),
        )

        self.assertEqual(result.intent, ConversationIntent.TROUBLESHOOTING_REQUEST)
        self.assertEqual(result.status, ConversationResponseStatus.NEEDS_CLARIFICATION)
        self.assertIn("entorno", result.missing_information)
        self.assertIn("producción", result.follow_up_questions[0])
        self.assertNotIn("Necesito un poco más de contexto", result.response_text)
        self.assertIn("No confirmo causa", result.response_text)

    def test_fallback_uses_historical_matches_with_clarification_prudently(
        self,
    ) -> None:
        agent = ReasoningAgent(
            model_gateway=FailingConversationModelGateway(),
            model_name="test-model",
        )

        result = agent.respond(
            request=ConversationRequest(message="Mi base de datos se está cargando por network"),
            session_state=ConversationSessionState(session_id="conv-test"),
            context=ConversationContext(
                session_id="conv-test",
                mode=ConversationMode.GENERAL,
                latest_user_message="Mi base de datos se está cargando por network",
                historical_context=ConversationHistoricalContext(
                    semantic_query_source="user_message",
                    semantic_matches=[
                        SemanticSearchMatchSnapshot(
                            case_id="INCNET1",
                            document_version="v1",
                            document_text="Caso previo con lentitud de base de datos por red saturada",
                            distance=0.21,
                        )
                    ],
                ),
            ),
            clarification=ClarificationAssessment(
                needs_clarification=True,
                sufficiency_level="sufficient_for_history",
                is_troubleshooting=True,
                known_information={
                    "service_or_component": "base de datos",
                    "symptom": "network",
                    "has_historical_evidence": "true",
                },
                missing_information=["entorno", "alcance"],
                follow_up_questions=[
                    "Ocurre en producción, QA u otro entorno?",
                    "Afecta una sola API/servicio o varios?",
                ],
            ),
            external_research=ExternalResearchResult(),
        )

        self.assertEqual(result.intent, ConversationIntent.TROUBLESHOOTING_REQUEST)
        self.assertEqual(result.status, ConversationResponseStatus.NEEDS_CLARIFICATION)
        self.assertIn("INCNET1", result.response_text)
        self.assertIn("No lo tomo como causa confirmada", result.response_text)
        self.assertIn("entorno", result.missing_information)


if __name__ == "__main__":
    unittest.main()
