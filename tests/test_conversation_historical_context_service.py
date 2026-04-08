import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from app.conversation.contracts.requests import ConversationRequest
from app.conversation.contracts.session_models import ConversationSessionState
from app.conversation.historical_context_service import HistoricalContextService
from app.services.retrieval.incident_semantic_search_service import (
    IncidentSemanticSearchMatch,
    IncidentSemanticSearchResult,
)


class ConversationHistoricalContextServiceTests(unittest.TestCase):
    def test_exact_lookup_by_incident_id_returns_real_incident_snapshot(self) -> None:
        incident_repository = Mock()
        incident_repository.get_by_case_id.return_value = self._incident_case()
        timeline_repository = Mock()
        troubleshooting_repository = Mock()
        troubleshooting_repository.list_by_case_id.return_value = []

        service = HistoricalContextService(
            db_session=Mock(),
            incident_repository=incident_repository,
            timeline_repository=timeline_repository,
            troubleshooting_repository=troubleshooting_repository,
            semantic_search_service=Mock(),
        )

        context = service.build_for_request(
            ConversationRequest(message="Recupera el SMS del INC000009209914")
        )

        self.assertEqual(context.incident_ids, ["INC000009209914"])
        self.assertIsNotNone(context.primary_incident)
        self.assertEqual(context.primary_incident.case_id, "INC000009209914")
        self.assertEqual(context.primary_incident.raw_sms, "SMS original")
        incident_repository.get_by_case_id.assert_called_once_with("INC000009209914")
        timeline_repository.list_by_case_id.assert_not_called()

    def test_timeline_request_returns_ordered_timeline_entries(self) -> None:
        incident_repository = Mock()
        incident_repository.get_by_case_id.return_value = self._incident_case()
        timeline_repository = Mock()
        timeline_repository.list_by_case_id.return_value = [
            SimpleNamespace(
                event_time="10:00",
                event_text="Se detecta falla",
                sequence_order=1,
            ),
            SimpleNamespace(
                event_time="10:05",
                event_text="Se escala a APIM",
                sequence_order=2,
            ),
        ]
        troubleshooting_repository = Mock()
        troubleshooting_repository.list_by_case_id.return_value = []

        service = HistoricalContextService(
            db_session=Mock(),
            incident_repository=incident_repository,
            timeline_repository=timeline_repository,
            troubleshooting_repository=troubleshooting_repository,
            semantic_search_service=Mock(),
        )

        context = service.build_for_request(
            ConversationRequest(
                message="Genera línea de tiempo de INC000009209914"
            )
        )

        self.assertEqual(len(context.timeline_entries), 2)
        self.assertEqual(context.timeline_entries[0].event_text, "Se detecta falla")
        timeline_repository.list_by_case_id.assert_called_once_with("INC000009209914")

    def test_semantic_search_request_returns_matches_when_no_incident_id(self) -> None:
        semantic_search_service = Mock()
        semantic_search_service.search.return_value = IncidentSemanticSearchResult(
            query_text="Tengo error connection refused en APIM",
            document_version="v1",
            limit=3,
            distance_threshold=None,
            query_embedding_dimensions=3,
            results=[
                IncidentSemanticSearchMatch(
                    case_id="INC0001",
                    document_version="v1",
                    document_text="APIM connection refused resuelto reiniciando gateway",
                    distance=0.12,
                )
            ],
        )

        service = HistoricalContextService(
            db_session=Mock(),
            incident_repository=Mock(),
            timeline_repository=Mock(),
            troubleshooting_repository=Mock(),
            semantic_search_service=semantic_search_service,
        )

        context = service.build_for_request(
            ConversationRequest(message="Tengo error connection refused en APIM")
        )

        self.assertEqual(len(context.semantic_matches), 1)
        self.assertEqual(context.semantic_matches[0].case_id, "INC0001")
        semantic_search_service.search.assert_called_once_with(
            "Tengo error connection refused en APIM",
            limit=3,
        )

    def test_semantic_search_request_with_incident_id_uses_case_document(self) -> None:
        incident_repository = Mock()
        incident_repository.get_by_case_id.return_value = self._incident_case()
        troubleshooting_repository = Mock()
        troubleshooting_repository.list_by_case_id.return_value = []
        semantic_search_service = Mock()
        semantic_search_service.search_similar_to_case.return_value = (
            self._semantic_result_for_case_query()
        )

        service = HistoricalContextService(
            db_session=Mock(),
            incident_repository=incident_repository,
            timeline_repository=Mock(),
            troubleshooting_repository=troubleshooting_repository,
            semantic_search_service=semantic_search_service,
        )

        context = service.build_for_request(
            ConversationRequest(message="Busca 5 casos similares a INC000009209914")
        )

        self.assertEqual(context.semantic_limit, 5)
        self.assertEqual(context.semantic_query_source, "retrieval_document:INC000009209914")
        self.assertEqual(context.semantic_matches[0].case_id, "INC0002")
        semantic_search_service.search_similar_to_case.assert_called_once_with(
            "INC000009209914",
            limit=5,
        )

    def test_semantic_search_request_uses_active_incident_from_session(self) -> None:
        incident_repository = Mock()
        incident_repository.get_by_case_id.return_value = self._incident_case()
        troubleshooting_repository = Mock()
        troubleshooting_repository.list_by_case_id.return_value = []
        semantic_search_service = Mock()
        semantic_search_service.search_similar_to_case.return_value = (
            self._semantic_result_for_case_query()
        )

        service = HistoricalContextService(
            db_session=Mock(),
            incident_repository=incident_repository,
            timeline_repository=Mock(),
            troubleshooting_repository=troubleshooting_repository,
            semantic_search_service=semantic_search_service,
        )

        context = service.build_for_request(
            ConversationRequest(message="Ahora busca 5 casos similares a este"),
            session_state=ConversationSessionState(
                session_id="conv-test",
                active_incident_ids=["INC000009209914"],
            ),
        )

        self.assertEqual(context.incident_ids, ["INC000009209914"])
        self.assertIsNotNone(context.primary_incident)
        self.assertEqual(context.semantic_matches[0].case_id, "INC0002")
        semantic_search_service.search_similar_to_case.assert_called_once_with(
            "INC000009209914",
            limit=5,
        )

    def test_semantic_search_falls_back_to_incident_snapshot_when_document_missing(
        self,
    ) -> None:
        incident_repository = Mock()
        incident_repository.get_by_case_id.return_value = self._incident_case()
        troubleshooting_repository = Mock()
        troubleshooting_repository.list_by_case_id.return_value = []
        semantic_search_service = Mock()
        semantic_search_service.search_similar_to_case.return_value = (
            IncidentSemanticSearchResult(
                query_text="case_id:INC000009209914",
                document_version="v1",
                limit=3,
                distance_threshold=None,
                query_embedding_dimensions=0,
                results=[],
            )
        )
        semantic_search_service.search.return_value = self._semantic_result_for_text_query()

        service = HistoricalContextService(
            db_session=Mock(),
            incident_repository=incident_repository,
            timeline_repository=Mock(),
            troubleshooting_repository=troubleshooting_repository,
            semantic_search_service=semantic_search_service,
        )

        context = service.build_for_request(
            ConversationRequest(message="Busca casos similares a INC000009209914")
        )

        self.assertEqual(context.semantic_query_source, "incident_snapshot:INC000009209914")
        self.assertEqual(context.semantic_matches[0].case_id, "INC0001")
        semantic_search_service.search.assert_called_once()

    def test_missing_incident_adds_retrieval_note_without_semantic_search(self) -> None:
        incident_repository = Mock()
        incident_repository.get_by_case_id.return_value = None
        semantic_search_service = Mock()

        service = HistoricalContextService(
            db_session=Mock(),
            incident_repository=incident_repository,
            timeline_repository=Mock(),
            troubleshooting_repository=Mock(),
            semantic_search_service=semantic_search_service,
        )

        context = service.build_for_request(
            ConversationRequest(message="Muéstrame el incidente INC404")
        )

        self.assertIsNone(context.primary_incident)
        self.assertIn("No se encontró", context.retrieval_notes[0])
        semantic_search_service.search.assert_not_called()
        semantic_search_service.search_similar_to_case.assert_not_called()

    def test_semantic_search_no_results_keeps_grounded_empty_context(self) -> None:
        semantic_search_service = Mock()
        semantic_search_service.search.return_value = IncidentSemanticSearchResult(
            query_text="Busca incidentes parecidos a carga por sesiones",
            document_version="v1",
            limit=3,
            distance_threshold=None,
            query_embedding_dimensions=3,
            results=[],
        )

        service = HistoricalContextService(
            db_session=Mock(),
            incident_repository=Mock(),
            timeline_repository=Mock(),
            troubleshooting_repository=Mock(),
            semantic_search_service=semantic_search_service,
        )

        context = service.build_for_request(
            ConversationRequest(
                message="Busca incidentes parecidos a carga por sesiones"
            )
        )

        self.assertEqual(context.semantic_matches, [])
        self.assertEqual(context.semantic_query_source, "user_message")
        self.assertIn("Semantic search recuperó 0 resultados.", context.retrieval_notes)

    def _incident_case(self) -> SimpleNamespace:
        return SimpleNamespace(
            case_id="INC000009209914",
            source_type="sms_bitacora",
            status="closed",
            header="Header real",
            failure_text="Falla real",
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

    def _semantic_result_for_text_query(self) -> IncidentSemanticSearchResult:
        return IncidentSemanticSearchResult(
            query_text="Tengo error connection refused en APIM",
            document_version="v1",
            limit=3,
            distance_threshold=None,
            query_embedding_dimensions=3,
            results=[
                IncidentSemanticSearchMatch(
                    case_id="INC0001",
                    document_version="v1",
                    document_text="APIM connection refused resuelto reiniciando gateway",
                    distance=0.12,
                )
            ],
        )

    def _semantic_result_for_case_query(self) -> IncidentSemanticSearchResult:
        return IncidentSemanticSearchResult(
            query_text="documento retrieval del caso base",
            document_version="v1",
            limit=5,
            distance_threshold=None,
            query_embedding_dimensions=3072,
            results=[
                IncidentSemanticSearchMatch(
                    case_id="INC0002",
                    document_version="v1",
                    document_text="Incidente similar con APIM y connection refused",
                    distance=0.18,
                )
            ],
        )


if __name__ == "__main__":
    unittest.main()
