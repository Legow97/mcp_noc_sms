import unittest
from unittest.mock import Mock

from app.db.repositories.incident_retrieval_document_repository import (
    IncidentRetrievalDocumentSimilarityResult,
)
from app.services.retrieval.incident_semantic_search_service import (
    IncidentSemanticSearchService,
)


class IncidentSemanticSearchServiceTests(unittest.TestCase):
    def test_search_embeds_query_and_returns_structured_results(self) -> None:
        embedding_service = Mock()
        embedding_service.embed_text.return_value = [0.1, 0.2, 0.3]
        document_repository = Mock()
        document_repository.search_similar_by_embedding.return_value = [
            IncidentRetrievalDocumentSimilarityResult(
                case_id="INC100",
                document_version="v1",
                document_text="doc 1",
                distance=0.01,
            ),
            IncidentRetrievalDocumentSimilarityResult(
                case_id="INC200",
                document_version="v1",
                document_text="doc 2",
                distance=0.12,
            ),
        ]

        service = IncidentSemanticSearchService(
            db_session=Mock(),
            embedding_service=embedding_service,
            document_repository=document_repository,
        )

        result = service.search("caida de transacciones en aws", limit=2)

        self.assertEqual(result.query_text, "caida de transacciones en aws")
        self.assertEqual(result.query_embedding_dimensions, 3)
        self.assertEqual([item.case_id for item in result.results], ["INC100", "INC200"])
        embedding_service.embed_text.assert_called_once_with(
            "caida de transacciones en aws",
            task_type="RETRIEVAL_QUERY",
        )
        document_repository.search_similar_by_embedding.assert_called_once_with(
            [0.1, 0.2, 0.3],
            limit=2,
            distance_threshold=None,
            document_version="v1",
        )

    def test_search_rejects_empty_query(self) -> None:
        service = IncidentSemanticSearchService(
            db_session=Mock(),
            embedding_service=Mock(),
            document_repository=Mock(),
        )

        with self.assertRaisesRegex(ValueError, "query_text no puede estar vacío"):
            service.search("   ")

    def test_search_rejects_invalid_limit(self) -> None:
        service = IncidentSemanticSearchService(
            db_session=Mock(),
            embedding_service=Mock(),
            document_repository=Mock(),
        )

        with self.assertRaisesRegex(ValueError, "limit debe ser mayor que cero"):
            service.search("aws", limit=0)

    def test_search_rejects_negative_distance_threshold(self) -> None:
        service = IncidentSemanticSearchService(
            db_session=Mock(),
            embedding_service=Mock(),
            document_repository=Mock(),
        )

        with self.assertRaisesRegex(ValueError, "distance_threshold no puede ser negativo"):
            service.search("aws", distance_threshold=-0.1)


if __name__ == "__main__":
    unittest.main()
