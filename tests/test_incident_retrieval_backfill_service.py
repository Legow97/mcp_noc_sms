import unittest
from unittest.mock import Mock

from app.services.retrieval.incident_retrieval_backfill_service import (
    IncidentRetrievalBackfillService,
)
from app.services.retrieval.incident_retrieval_indexing_service import (
    IncidentRetrievalIndexingResult,
)


class IncidentRetrievalBackfillServiceTests(unittest.TestCase):
    def test_index_cases_collects_ok_failed_and_skipped(self) -> None:
        db = Mock()
        indexing_service = Mock()
        indexing_service.index_case.side_effect = [
            IncidentRetrievalIndexingResult(
                case_id="INC1",
                document_version="v1",
                indexed=True,
                created=True,
                embedding_dimensions=3,
                document_text_length=100,
            ),
            RuntimeError("provider down"),
        ]
        incident_case_repository = Mock()
        document_repository = Mock()
        document_repository.get_by_case_id_and_version.side_effect = [
            None,
            object(),
            None,
        ]

        service = IncidentRetrievalBackfillService(
            db_session=db,
            indexing_service=indexing_service,
            incident_case_repository=incident_case_repository,
            document_repository=document_repository,
        )

        result = service.index_cases(
            ["INC1", "INC2", "INC3"],
            skip_existing=True,
        )

        self.assertEqual(result.succeeded, 1)
        self.assertEqual(result.skipped, 1)
        self.assertEqual(result.failed, 1)
        self.assertEqual(
            [item.status for item in result.results],
            ["ok", "skipped", "failed"],
        )
        db.rollback.assert_called_once()

    def test_index_cases_marks_missing_case_as_failed(self) -> None:
        db = Mock()
        indexing_service = Mock()
        indexing_service.index_case.return_value = None
        service = IncidentRetrievalBackfillService(
            db_session=db,
            indexing_service=indexing_service,
            incident_case_repository=Mock(),
            document_repository=Mock(),
        )

        result = service.index_cases(["INC404"])

        self.assertEqual(result.failed, 1)
        self.assertEqual(result.results[0].status, "failed")
        self.assertIn("was not found", result.results[0].reason)

    def test_index_missing_cases_uses_repository_query(self) -> None:
        incident_case_repository = Mock()
        document_repository = Mock()
        document_repository.list_missing_case_ids.return_value = ["INC1", "INC2"]
        document_repository.get_by_case_id_and_version.return_value = None
        indexing_service = Mock()
        indexing_service.index_case.side_effect = [
            IncidentRetrievalIndexingResult(
                case_id="INC1",
                document_version="v1",
                indexed=True,
                created=True,
                embedding_dimensions=3,
                document_text_length=10,
            ),
            IncidentRetrievalIndexingResult(
                case_id="INC2",
                document_version="v1",
                indexed=True,
                created=True,
                embedding_dimensions=3,
                document_text_length=10,
            ),
        ]

        service = IncidentRetrievalBackfillService(
            db_session=Mock(),
            indexing_service=indexing_service,
            incident_case_repository=incident_case_repository,
            document_repository=document_repository,
        )

        result = service.index_missing_cases(limit=10, offset=5)

        self.assertEqual(result.succeeded, 2)
        document_repository.list_missing_case_ids.assert_called_once_with(
            document_version="v1",
            limit=10,
            offset=5,
        )

    def test_counts_delegate_to_repositories(self) -> None:
        incident_case_repository = Mock()
        incident_case_repository.count_all.return_value = 12
        document_repository = Mock()
        document_repository.count_by_version.return_value = 7

        service = IncidentRetrievalBackfillService(
            db_session=Mock(),
            indexing_service=Mock(),
            incident_case_repository=incident_case_repository,
            document_repository=document_repository,
        )

        self.assertEqual(service.count_total_cases(), 12)
        self.assertEqual(service.count_indexed_cases(), 7)


if __name__ == "__main__":
    unittest.main()
