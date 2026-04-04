import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from app.api.schemas.incident_requests import IngestSmsRequest
from app.services.agentic_incident_ingestion_service import (
    AgenticIncidentIngestionService,
)
from app.services.canonical_extraction_persistence_service import (
    CanonicalPersistenceResult,
)
from app.services.retrieval.incident_retrieval_indexing_service import (
    IncidentRetrievalIndexingResult,
)


def build_payload() -> IngestSmsRequest:
    return IngestSmsRequest.model_validate(
        {
            "raw_text": "INC123456 SMS de prueba",
            "source_channel": "sms",
            "received_at": "2026-04-03T10:00:00-05:00",
        }
    )


def build_orchestration_result(case_id: str = "INC123456") -> Mock:
    accepted_result = SimpleNamespace(
        incident_case=SimpleNamespace(case_id=case_id),
    )
    judge_evaluation = SimpleNamespace(
        decision="accepted",
        score=0.98,
    )
    trace = SimpleNamespace(
        fallback_triggered=False,
    )
    orchestration_result = Mock()
    orchestration_result.accepted_result = accepted_result
    orchestration_result.judge_evaluation = judge_evaluation
    orchestration_result.trace = trace
    orchestration_result.model_dump.return_value = {
        "accepted_result": {"incident_case": {"case_id": case_id}},
        "judge_evaluation": {"decision": "accepted", "score": 0.98},
        "trace": {"fallback_triggered": False},
    }
    return orchestration_result


class AgenticIncidentIngestionServiceTests(unittest.TestCase):
    def test_ingest_sms_indexes_case_after_successful_persistence(self) -> None:
        db = Mock()
        orchestrator = Mock()
        orchestrator.extract.return_value = build_orchestration_result()
        retrieval_indexing_service = Mock()
        retrieval_indexing_service.index_case.return_value = IncidentRetrievalIndexingResult(
            case_id="INC123456",
            document_version="v1",
            indexed=True,
            created=True,
            embedding_dimensions=3,
            document_text_length=128,
        )

        service = AgenticIncidentIngestionService(
            db_session=db,
            orchestrator=orchestrator,
            retrieval_indexing_service=retrieval_indexing_service,
        )
        service._persistence_service = Mock()
        service._persistence_service.save_accepted_result.return_value = (
            CanonicalPersistenceResult(
                case_id="INC123456",
                incident_status="open",
                timeline_entries_saved=2,
                troubleshooting_actions_saved=1,
            )
        )

        result = service.ingest_sms(build_payload())

        self.assertTrue(result.indexed)
        retrieval_indexing_service.index_case.assert_called_once_with("INC123456")
        db.rollback.assert_not_called()

    def test_ingest_sms_keeps_persisted_incident_when_indexing_fails(self) -> None:
        db = Mock()
        orchestrator = Mock()
        orchestrator.extract.return_value = build_orchestration_result()
        retrieval_indexing_service = Mock()
        retrieval_indexing_service.index_case.side_effect = RuntimeError(
            "embedding provider down"
        )

        service = AgenticIncidentIngestionService(
            db_session=db,
            orchestrator=orchestrator,
            retrieval_indexing_service=retrieval_indexing_service,
        )
        service._persistence_service = Mock()
        service._persistence_service.save_accepted_result.return_value = (
            CanonicalPersistenceResult(
                case_id="INC123456",
                incident_status="open",
                timeline_entries_saved=2,
                troubleshooting_actions_saved=1,
            )
        )

        result = service.ingest_sms(build_payload())

        self.assertEqual(result.case_id, "INC123456")
        self.assertFalse(result.indexed)
        retrieval_indexing_service.index_case.assert_called_once_with("INC123456")
        db.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
