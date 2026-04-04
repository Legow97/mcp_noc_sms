import unittest
from unittest.mock import Mock

from app.db.models import IncidentRetrievalDocumentModel
from app.db.repositories.incident_retrieval_document_repository import (
    IncidentRetrievalDocumentRepository,
    IncidentRetrievalDocumentUpsertPayload,
)


class IncidentRetrievalDocumentRepositoryTests(unittest.TestCase):
    def test_upsert_creates_document_when_not_exists(self) -> None:
        db = Mock()
        repository = IncidentRetrievalDocumentRepository(db)
        repository.get_by_case_id_and_version = Mock(return_value=None)

        document = repository.upsert(
            IncidentRetrievalDocumentUpsertPayload(
                case_id="INC0001",
                document_version="v1",
                document_text="document text",
                embedding=[0.1, 0.2],
            )
        )

        self.assertIsInstance(document, IncidentRetrievalDocumentModel)
        self.assertEqual(document.case_id, "INC0001")
        self.assertEqual(document.document_version, "v1")
        self.assertEqual(document.document_text, "document text")
        self.assertEqual(document.embedding, [0.1, 0.2])
        db.add.assert_called_once()
        db.flush.assert_called_once()
        db.refresh.assert_called_once_with(document)

    def test_upsert_updates_existing_document(self) -> None:
        db = Mock()
        repository = IncidentRetrievalDocumentRepository(db)
        existing = IncidentRetrievalDocumentModel(
            case_id="INC0001",
            document_version="v1",
            document_text="old",
            embedding=[0.1],
        )
        repository.get_by_case_id_and_version = Mock(return_value=existing)

        document = repository.upsert(
            IncidentRetrievalDocumentUpsertPayload(
                case_id=" INC0001 ",
                document_version=" v1 ",
                document_text=" updated text ",
                embedding=[0.3, 0.4],
            )
        )

        self.assertIs(document, existing)
        self.assertEqual(document.document_text, "updated text")
        self.assertEqual(document.embedding, [0.3, 0.4])
        db.add.assert_not_called()
        db.flush.assert_called_once()
        db.refresh.assert_called_once_with(existing)

    def test_upsert_rejects_empty_document_text(self) -> None:
        db = Mock()
        repository = IncidentRetrievalDocumentRepository(db)

        with self.assertRaisesRegex(ValueError, "document_text no puede estar vacío"):
            repository.upsert(
                IncidentRetrievalDocumentUpsertPayload(
                    case_id="INC0001",
                    document_version="v1",
                    document_text="   ",
                    embedding=[],
                )
            )

    def test_search_similar_by_embedding_applies_threshold_and_version(self) -> None:
        db = Mock()
        query = Mock()
        filtered_query = Mock()
        ordered_query = Mock()
        limited_query = Mock()
        document = IncidentRetrievalDocumentModel(
            case_id="INC0001",
            document_version="v1",
            document_text="document text",
            embedding=[0.1, 0.2],
        )

        db.query.return_value = query
        query.filter.return_value = filtered_query
        filtered_query.filter.return_value = filtered_query
        filtered_query.order_by.return_value = ordered_query
        ordered_query.limit.return_value = limited_query
        limited_query.all.return_value = [(document, 0.1234)]

        repository = IncidentRetrievalDocumentRepository(db)

        results = repository.search_similar_by_embedding(
            [0.1, 0.2],
            limit=3,
            distance_threshold=0.2,
            document_version="v1",
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].case_id, "INC0001")
        self.assertEqual(results[0].distance, 0.1234)
        self.assertEqual(query.filter.call_count, 1)
        self.assertEqual(filtered_query.filter.call_count, 1)

    def test_search_similar_by_embedding_rejects_negative_threshold(self) -> None:
        repository = IncidentRetrievalDocumentRepository(Mock())

        with self.assertRaisesRegex(ValueError, "distance_threshold no puede ser negativo"):
            repository.search_similar_by_embedding(
                [0.1, 0.2],
                distance_threshold=-0.01,
            )


if __name__ == "__main__":
    unittest.main()
