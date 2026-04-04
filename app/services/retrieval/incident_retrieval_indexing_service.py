from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.repositories.incident_retrieval_document_repository import (
    IncidentRetrievalDocumentRepository,
    IncidentRetrievalDocumentUpsertPayload,
)
from app.services.retrieval.embedding_service import EmbeddingService
from app.services.retrieval.incident_retrieval_document_builder import (
    IncidentRetrievalDocumentBuilder,
)
from app.services.retrieval.incident_retrieval_source_reader import (
    IncidentRetrievalSourceReader,
)


@dataclass(slots=True)
class IncidentRetrievalIndexingResult:
    case_id: str
    document_version: str
    indexed: bool
    created: bool
    embedding_dimensions: int
    document_text_length: int


class IncidentRetrievalIndexingService:
    """
    Orquesta la indexación inicial/reindexación de incidentes persistidos.
    """

    def __init__(
        self,
        db_session: Session,
        *,
        source_reader: IncidentRetrievalSourceReader | None = None,
        document_builder: IncidentRetrievalDocumentBuilder | None = None,
        embedding_service: EmbeddingService | None = None,
        document_repository: IncidentRetrievalDocumentRepository | None = None,
        document_version: str | None = None,
    ) -> None:
        self._db = db_session
        self._source_reader = source_reader or IncidentRetrievalSourceReader(db_session)
        self._document_builder = document_builder or IncidentRetrievalDocumentBuilder()
        self._embedding_service = embedding_service or EmbeddingService()
        self._document_repository = document_repository or IncidentRetrievalDocumentRepository(
            db_session
        )
        self._document_version = (
            document_version or settings.retrieval.document_version
        ).strip()

        if not self._document_version:
            raise ValueError("document_version no puede estar vacío.")

    def index_case(self, case_id: str) -> IncidentRetrievalIndexingResult | None:
        normalized_case_id = case_id.strip()
        if not normalized_case_id:
            return None

        source_data = self._source_reader.read(normalized_case_id)
        if source_data is None:
            return None

        existing_document = self._document_repository.get_by_case_id_and_version(
            normalized_case_id,
            self._document_version,
        )
        document_payload = self._document_builder.build(source_data)
        embedding = self._embedding_service.embed_text(
            document_payload["document_text"]
        )

        try:
            self._document_repository.upsert(
                IncidentRetrievalDocumentUpsertPayload(
                    case_id=normalized_case_id,
                    document_version=self._document_version,
                    document_text=document_payload["document_text"],
                    embedding=embedding,
                )
            )
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

        return IncidentRetrievalIndexingResult(
            case_id=normalized_case_id,
            document_version=self._document_version,
            indexed=True,
            created=existing_document is None,
            embedding_dimensions=len(embedding),
            document_text_length=len(document_payload["document_text"]),
        )
