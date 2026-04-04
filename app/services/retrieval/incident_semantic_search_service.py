from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.repositories.incident_retrieval_document_repository import (
    IncidentRetrievalDocumentRepository,
    IncidentRetrievalDocumentSimilarityResult,
)
from app.services.retrieval.embedding_service import EmbeddingService


@dataclass(slots=True)
class IncidentSemanticSearchMatch:
    case_id: str
    document_version: str
    document_text: str
    distance: float


@dataclass(slots=True)
class IncidentSemanticSearchResult:
    query_text: str
    document_version: str
    limit: int
    distance_threshold: float | None
    query_embedding_dimensions: int
    results: list[IncidentSemanticSearchMatch]


class IncidentSemanticSearchService:
    """
    Orquesta búsqueda semántica real sobre incidentes ya indexados.
    """

    def __init__(
        self,
        db_session: Session,
        *,
        embedding_service: EmbeddingService | None = None,
        document_repository: IncidentRetrievalDocumentRepository | None = None,
        document_version: str | None = None,
    ) -> None:
        self._embedding_service = embedding_service or EmbeddingService()
        self._document_repository = document_repository or IncidentRetrievalDocumentRepository(
            db_session
        )
        self._document_version = (
            document_version or settings.retrieval.document_version
        ).strip()

        if not self._document_version:
            raise ValueError("document_version no puede estar vacío.")

    def search(
        self,
        query_text: str,
        *,
        limit: int = 5,
        distance_threshold: float | None = None,
        document_version: str | None = None,
    ) -> IncidentSemanticSearchResult:
        normalized_query_text = query_text.strip()
        if not normalized_query_text:
            raise ValueError("query_text no puede estar vacío.")
        if limit <= 0:
            raise ValueError("limit debe ser mayor que cero.")
        if distance_threshold is not None and distance_threshold < 0:
            raise ValueError("distance_threshold no puede ser negativo.")

        normalized_version = (
            document_version.strip()
            if document_version is not None
            else self._document_version
        )
        if not normalized_version:
            raise ValueError("document_version no puede estar vacío.")

        query_embedding = self._embedding_service.embed_text(
            normalized_query_text,
            task_type="RETRIEVAL_QUERY",
        )
        matches = self._document_repository.search_similar_by_embedding(
            query_embedding,
            limit=limit,
            distance_threshold=distance_threshold,
            document_version=normalized_version,
        )

        return IncidentSemanticSearchResult(
            query_text=normalized_query_text,
            document_version=normalized_version,
            limit=limit,
            distance_threshold=distance_threshold,
            query_embedding_dimensions=len(query_embedding),
            results=[
                self._to_match(match)
                for match in matches
            ],
        )

    def _to_match(
        self,
        match: IncidentRetrievalDocumentSimilarityResult,
    ) -> IncidentSemanticSearchMatch:
        return IncidentSemanticSearchMatch(
            case_id=match.case_id,
            document_version=match.document_version,
            document_text=match.document_text,
            distance=match.distance,
        )
