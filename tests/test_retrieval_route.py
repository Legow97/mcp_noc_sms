import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException

from app.api.routes.retrieval import search_retrieval_documents
from app.api.schemas.retrieval_requests import RetrievalSearchRequest
from app.services.retrieval.incident_semantic_search_service import (
    IncidentSemanticSearchMatch,
    IncidentSemanticSearchResult,
)


class RetrievalRouteTests(unittest.TestCase):
    def test_search_route_returns_semantic_results(self) -> None:
        payload = RetrievalSearchRequest(
            query_text="caida de transacciones en aws",
            limit=2,
        )
        search_result = IncidentSemanticSearchResult(
            query_text="caida de transacciones en aws",
            document_version="v1",
            limit=2,
            distance_threshold=None,
            query_embedding_dimensions=3072,
            results=[
                IncidentSemanticSearchMatch(
                    case_id="INC100",
                    document_version="v1",
                    document_text="documento 1",
                    distance=0.12,
                ),
                IncidentSemanticSearchMatch(
                    case_id="INC200",
                    document_version="v1",
                    document_text="documento 2",
                    distance=0.23,
                ),
            ],
        )

        with patch(
            "app.api.routes.retrieval.IncidentSemanticSearchService"
        ) as service_class:
            service_instance = Mock()
            service_instance.search.return_value = search_result
            service_class.return_value = service_instance

            response = search_retrieval_documents(payload, db=Mock())

        self.assertEqual(response.query_text, "caida de transacciones en aws")
        self.assertEqual(response.document_version, "v1")
        self.assertEqual(response.query_embedding_dimensions, 3072)
        self.assertEqual(len(response.results), 2)

    def test_search_route_returns_422_for_service_validation_error(self) -> None:
        with patch(
            "app.api.routes.retrieval.IncidentSemanticSearchService"
        ) as service_class:
            service_instance = Mock()
            service_instance.search.side_effect = ValueError(
                "query_text no puede estar vacío."
            )
            service_class.return_value = service_instance

            with self.assertRaises(HTTPException) as exc_context:
                search_retrieval_documents(
                    RetrievalSearchRequest(query_text="aws"),
                    db=Mock(),
                )

        self.assertEqual(exc_context.exception.status_code, 422)
        self.assertEqual(
            exc_context.exception.detail,
            "query_text no puede estar vacío.",
        )


if __name__ == "__main__":
    unittest.main()
