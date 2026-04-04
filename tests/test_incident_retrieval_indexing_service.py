import unittest
from unittest.mock import Mock

from app.db.repositories.incident_retrieval_document_repository import (
    IncidentRetrievalDocumentUpsertPayload,
)
from app.services.retrieval.incident_retrieval_indexing_service import (
    IncidentRetrievalIndexingService,
)
from app.services.retrieval.incident_retrieval_source_reader import (
    IncidentRetrievalCaseData,
    IncidentRetrievalSourceData,
)


def build_source_data(case_id: str) -> IncidentRetrievalSourceData:
    return IncidentRetrievalSourceData(
        incident_case=IncidentRetrievalCaseData(
            case_id=case_id,
            start_time=None,
            header="Header",
            failure_text="Failure",
            impact_text="Impact",
            services_affected=["Portal"],
            components_affected=["AWS"],
            solution_time=None,
            probable_cause_text="Cause",
            resolution_summary="Resolved",
            tags=["tag1"],
        ),
        timeline_entries=[],
        troubleshooting_actions=[],
    )


class IncidentRetrievalIndexingServiceTests(unittest.TestCase):
    def test_index_case_returns_none_for_missing_case(self) -> None:
        db = Mock()
        source_reader = Mock()
        source_reader.read.return_value = None

        service = IncidentRetrievalIndexingService(
            db_session=db,
            source_reader=source_reader,
            document_builder=Mock(),
            embedding_service=Mock(),
            document_repository=Mock(),
        )

        result = service.index_case("INC404")

        self.assertIsNone(result)
        db.commit.assert_not_called()

    def test_index_case_creates_document(self) -> None:
        db = Mock()
        source_reader = Mock()
        source_reader.read.return_value = build_source_data("INC100")
        document_builder = Mock()
        document_builder.build.return_value = {
            "case_id": "INC100",
            "document_text": "doc text",
        }
        embedding_service = Mock()
        embedding_service.embed_text.return_value = [0.1, 0.2, 0.3]
        document_repository = Mock()
        document_repository.get_by_case_id_and_version.return_value = None

        service = IncidentRetrievalIndexingService(
            db_session=db,
            source_reader=source_reader,
            document_builder=document_builder,
            embedding_service=embedding_service,
            document_repository=document_repository,
        )

        result = service.index_case("INC100")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertTrue(result.indexed)
        self.assertTrue(result.created)
        self.assertEqual(result.embedding_dimensions, 3)
        self.assertEqual(result.document_text_length, 8)
        payload = document_repository.upsert.call_args.args[0]
        self.assertIsInstance(payload, IncidentRetrievalDocumentUpsertPayload)
        self.assertEqual(payload.case_id, "INC100")
        self.assertEqual(payload.document_version, "v1")
        self.assertEqual(payload.embedding, [0.1, 0.2, 0.3])
        db.commit.assert_called_once()

    def test_index_case_reindexes_existing_document(self) -> None:
        db = Mock()
        source_reader = Mock()
        source_reader.read.return_value = build_source_data("INC200")
        document_builder = Mock()
        document_builder.build.return_value = {
            "case_id": "INC200",
            "document_text": "updated doc",
        }
        embedding_service = Mock()
        embedding_service.embed_text.return_value = [0.4, 0.5]
        document_repository = Mock()
        document_repository.get_by_case_id_and_version.return_value = object()

        service = IncidentRetrievalIndexingService(
            db_session=db,
            source_reader=source_reader,
            document_builder=document_builder,
            embedding_service=embedding_service,
            document_repository=document_repository,
        )

        result = service.index_case("INC200")

        self.assertIsNotNone(result)
        assert result is not None
        self.assertFalse(result.created)
        db.commit.assert_called_once()

    def test_index_case_rolls_back_on_failure(self) -> None:
        db = Mock()
        source_reader = Mock()
        source_reader.read.return_value = build_source_data("INC300")
        document_builder = Mock()
        document_builder.build.return_value = {
            "case_id": "INC300",
            "document_text": "doc",
        }
        embedding_service = Mock()
        embedding_service.embed_text.return_value = [0.1]
        document_repository = Mock()
        document_repository.get_by_case_id_and_version.return_value = None
        document_repository.upsert.side_effect = RuntimeError("db fail")

        service = IncidentRetrievalIndexingService(
            db_session=db,
            source_reader=source_reader,
            document_builder=document_builder,
            embedding_service=embedding_service,
            document_repository=document_repository,
        )

        with self.assertRaisesRegex(RuntimeError, "db fail"):
            service.index_case("INC300")

        db.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
