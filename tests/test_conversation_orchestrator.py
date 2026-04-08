import unittest
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from app.conversation.context_builder import ContextBuilder
from app.conversation.contracts.requests import ConversationMode, ConversationRequest
from app.conversation.contracts.responses import ConversationResponseStatus
from app.conversation.historical_context_service import HistoricalContextService
from app.conversation.model_gateway import (
    ConversationModelGateway,
    ConversationModelInvocation,
    ConversationModelRawResponse,
)
from app.conversation.orchestrator import ConversationOrchestrator
from app.conversation.reasoning_agent import ReasoningAgent
from app.conversation.session_store import InMemorySessionStore
from app.services.retrieval.incident_semantic_search_service import (
    IncidentSemanticSearchMatch,
    IncidentSemanticSearchResult,
)


class DeterministicConversationModelGateway(ConversationModelGateway):
    def invoke(
        self,
        invocation: ConversationModelInvocation,
    ) -> ConversationModelRawResponse:
        payload = json.loads(invocation.user_input)
        message = payload["user_message"]
        session_state = payload["session_state"]
        history_count = session_state["history_count"]
        last_user_message = session_state["last_user_message"]

        if message == "Ayuda":
            output = {
                "intent": "needs_clarification",
                "status": "needs_clarification",
                "response_text": "Necesito más contexto para ayudarte.",
                "missing_information": ["more_detail"],
                "follow_up_questions": [
                    "Puedes compartir más contexto del incidente, síntoma o pregunta que quieres resolver?"
                ],
                "active_incident_ids": [],
                "active_entities": [],
            }
        else:
            prior_note = (
                f" Último mensaje previo en sesión: '{last_user_message}'."
                if last_user_message
                else ""
            )
            output = {
                "intent": "general",
                "status": "completed",
                "response_text": (
                    f"Respuesta LLM de prueba. Historial disponible: {history_count} mensajes."
                    f"{prior_note}"
                ),
                "missing_information": [],
                "follow_up_questions": [],
                "active_incident_ids": [],
                "active_entities": [],
            }

        return ConversationModelRawResponse(
            model_name=invocation.model_name,
            output_text=json.dumps(output, ensure_ascii=False),
            provider_name="test",
        )


class FailingConversationModelGateway(ConversationModelGateway):
    def invoke(
        self,
        invocation: ConversationModelInvocation,
    ) -> ConversationModelRawResponse:
        raise RuntimeError("provider down")


def build_test_orchestrator(
    session_store: InMemorySessionStore | None = None,
) -> ConversationOrchestrator:
    return ConversationOrchestrator(
        session_store=session_store or InMemorySessionStore(),
        reasoning_agent=ReasoningAgent(
            model_gateway=DeterministicConversationModelGateway(),
            model_name="test-conversation-model",
        ),
    )


class ConversationOrchestratorTests(unittest.TestCase):
    def test_handle_returns_structured_response_and_persists_session_history(self) -> None:
        session_store = InMemorySessionStore()
        orchestrator = build_test_orchestrator(session_store=session_store)

        first_response = orchestrator.handle(
            ConversationRequest(
                message="Necesito entender el estado del incidente INC-100",
            )
        )

        second_response = orchestrator.handle(
            ConversationRequest(
                session_id=first_response.session_id,
                message="Agrega el contexto del impacto en pagos",
                mode=ConversationMode.TROUBLESHOOTING,
            )
        )

        self.assertEqual(first_response.status, ConversationResponseStatus.COMPLETED)
        self.assertEqual(second_response.session_id, first_response.session_id)
        self.assertEqual(second_response.mode, ConversationMode.TROUBLESHOOTING)

        saved_session = session_store.get_session(
            session_id=first_response.session_id,
            mode=ConversationMode.TROUBLESHOOTING,
        )
        self.assertEqual(len(saved_session.history), 4)
        self.assertEqual(saved_session.current_mode, ConversationMode.TROUBLESHOOTING)
        self.assertEqual(
            saved_session.last_user_message,
            "Agrega el contexto del impacto en pagos",
        )
        self.assertEqual(saved_session.history[0].role, "user")
        self.assertEqual(saved_session.history[1].role, "assistant")

    def test_handle_requests_clarification_for_short_messages(self) -> None:
        orchestrator = build_test_orchestrator()

        response = orchestrator.handle(
            ConversationRequest(
                message="Ayuda",
                mode=ConversationMode.CLARIFICATION,
            )
        )

        self.assertEqual(
            response.status,
            ConversationResponseStatus.NEEDS_CLARIFICATION,
        )
        self.assertIn("more_detail", response.missing_information)
        self.assertEqual(len(response.follow_up_questions), 1)

    def test_handle_uses_previous_session_message_in_agent_context(self) -> None:
        session_store = InMemorySessionStore()
        orchestrator = build_test_orchestrator(session_store=session_store)

        session_state = session_store.get_session("conv-shared", ConversationMode.GENERAL)
        session_state.last_user_message = "Mensaje previo"
        session_store.save_session(session_state)

        response = orchestrator.handle(
            ConversationRequest(
                session_id="conv-shared",
                message="Necesito seguimiento del incidente",
            )
        )

        self.assertIn("Último mensaje previo en sesión: 'Mensaje previo'.", response.response_text)

    def test_handle_uses_active_incident_for_follow_up_semantic_search(self) -> None:
        session_store = InMemorySessionStore()
        incident_repository = Mock()
        incident_repository.get_by_case_id.return_value = SimpleNamespace(
            case_id="INC000009209914",
            source_type="sms_bitacora",
            status="closed",
            header="Header real",
            failure_text="Falla APIM connection refused",
            impact_text="Impacto real",
            start_time=datetime(2026, 4, 1, tzinfo=timezone.utc),
            solution_time=None,
            raw_sms="SMS original",
            probable_cause_text=None,
            resolution_summary="Se normalizó el servicio",
            services_affected=["APIM"],
            symptoms=["connection refused"],
            teams_involved=["NOC"],
            tickets=["INC000009209914"],
            tags=["apim"],
        )
        troubleshooting_repository = Mock()
        troubleshooting_repository.list_by_case_id.return_value = []
        semantic_search_service = Mock()
        semantic_search_service.search_similar_to_case.return_value = (
            IncidentSemanticSearchResult(
                query_text="documento retrieval del caso base",
                document_version="v1",
                limit=5,
                distance_threshold=None,
                query_embedding_dimensions=3072,
                results=[
                    IncidentSemanticSearchMatch(
                        case_id="INC0002",
                        document_version="v1",
                        document_text="Caso similar APIM connection refused",
                        distance=0.18,
                    )
                ],
            )
        )
        historical_context_service = HistoricalContextService(
            db_session=Mock(),
            incident_repository=incident_repository,
            timeline_repository=Mock(),
            troubleshooting_repository=troubleshooting_repository,
            semantic_search_service=semantic_search_service,
        )
        orchestrator = ConversationOrchestrator(
            session_store=session_store,
            context_builder=ContextBuilder(
                historical_context_service=historical_context_service,
            ),
            reasoning_agent=ReasoningAgent(
                model_gateway=FailingConversationModelGateway(),
                model_name="test-model",
            ),
        )

        first_response = orchestrator.handle(
            ConversationRequest(message="Recupera INC000009209914")
        )
        second_response = orchestrator.handle(
            ConversationRequest(
                session_id=first_response.session_id,
                message="Ahora busca 5 casos similares a este",
            )
        )

        self.assertIn("INC0002", second_response.response_text)
        self.assertIn("semantic_query_source=retrieval_document:INC000009209914", second_response.context_summary)
        semantic_search_service.search_similar_to_case.assert_called_once_with(
            "INC000009209914",
            limit=5,
        )

    def test_handle_persists_troubleshooting_state_for_follow_up(self) -> None:
        session_store = InMemorySessionStore()
        orchestrator = ConversationOrchestrator(
            session_store=session_store,
            reasoning_agent=ReasoningAgent(
                model_gateway=FailingConversationModelGateway(),
                model_name="test-model",
            ),
        )

        first_response = orchestrator.handle(
            ConversationRequest(message="Tengo error connection refused en APIM")
        )
        second_response = orchestrator.handle(
            ConversationRequest(
                session_id=first_response.session_id,
                message="Ocurre en producción",
            )
        )

        self.assertEqual(
            first_response.status,
            ConversationResponseStatus.NEEDS_CLARIFICATION,
        )
        self.assertEqual(
            second_response.status,
            ConversationResponseStatus.NEEDS_CLARIFICATION,
        )
        self.assertEqual(second_response.session_id, first_response.session_id)
        self.assertIn("Nuevo dato: Ocurre en producción", second_response.active_issue_summary)
        self.assertNotIn("entorno", second_response.missing_information)

        saved_session = session_store.get_session(
            session_id=first_response.session_id,
            mode=ConversationMode.GENERAL,
        )
        self.assertTrue(saved_session.awaiting_more_info)
        self.assertIn("APIM", saved_session.active_entities)
        self.assertIn("environment", saved_session.troubleshooting_context)
        self.assertNotIn("entorno", saved_session.missing_information)
        self.assertIn("connection refused", saved_session.active_issue_summary)

    def test_new_session_does_not_reuse_troubleshooting_state(self) -> None:
        session_store = InMemorySessionStore()
        orchestrator = ConversationOrchestrator(
            session_store=session_store,
            reasoning_agent=ReasoningAgent(
                model_gateway=FailingConversationModelGateway(),
                model_name="test-model",
            ),
        )

        first_response = orchestrator.handle(
            ConversationRequest(message="Tengo error connection refused en APIM")
        )
        second_response = orchestrator.handle(
            ConversationRequest(message="Ocurre en producción")
        )

        self.assertNotEqual(first_response.session_id, second_response.session_id)
        self.assertIsNone(second_response.active_issue_summary)
        self.assertNotIn("Nuevo dato", second_response.response_text)


if __name__ == "__main__":
    unittest.main()
