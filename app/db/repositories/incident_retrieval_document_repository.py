from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import cast
from sqlalchemy.orm import Query, Session
from pgvector.sqlalchemy import HALFVEC

from app.db.models import IncidentCaseModel
from app.db.models import IncidentRetrievalDocumentModel


@dataclass(slots=True)
class IncidentRetrievalDocumentUpsertPayload:
    case_id: str
    document_version: str
    document_text: str
    embedding: list[float]


@dataclass(slots=True)
class IncidentRetrievalDocumentSimilarityResult:
    case_id: str
    document_version: str
    document_text: str
    distance: float


class IncidentRetrievalDocumentRepository:
    """
    Repositorio de persistencia para documentos indexables de retrieval.

    No construye texto ni embeddings; solo guarda y consulta el índice.
    """

    def __init__(self, db_session: Session) -> None:
        self._db = db_session

    def upsert(
        self,
        payload: IncidentRetrievalDocumentUpsertPayload,
    ) -> IncidentRetrievalDocumentModel:
        normalized_case_id = payload.case_id.strip()
        normalized_version = payload.document_version.strip()
        normalized_document_text = payload.document_text.strip()

        if not normalized_case_id:
            raise ValueError("case_id no puede estar vacío.")
        if not normalized_version:
            raise ValueError("document_version no puede estar vacío.")
        if not normalized_document_text:
            raise ValueError("document_text no puede estar vacío.")

        document = self.get_by_case_id_and_version(
            normalized_case_id,
            normalized_version,
        )

        if document is None:
            document = IncidentRetrievalDocumentModel(
                case_id=normalized_case_id,
                document_version=normalized_version,
                document_text=normalized_document_text,
                embedding=list(payload.embedding),
            )
            self._db.add(document)
        else:
            document.document_text = normalized_document_text
            document.embedding = list(payload.embedding)

        self._db.flush()
        self._db.refresh(document)
        return document

    def get_by_case_id(
        self,
        case_id: str,
        *,
        document_version: str | None = None,
    ) -> IncidentRetrievalDocumentModel | None:
        normalized_case_id = case_id.strip()
        if not normalized_case_id:
            return None

        query = self._db.query(IncidentRetrievalDocumentModel).filter(
            IncidentRetrievalDocumentModel.case_id == normalized_case_id
        )

        if document_version is not None:
            normalized_version = document_version.strip()
            if not normalized_version:
                return None
            query = query.filter(
                IncidentRetrievalDocumentModel.document_version == normalized_version
            )
            return query.first()

        return (
            query.order_by(
                IncidentRetrievalDocumentModel.updated_at.desc(),
                IncidentRetrievalDocumentModel.document_version.desc(),
            )
            .first()
        )

    def get_by_case_id_and_version(
        self,
        case_id: str,
        document_version: str,
    ) -> IncidentRetrievalDocumentModel | None:
        return self.get_by_case_id(
            case_id,
            document_version=document_version,
        )

    def count_by_version(self, document_version: str) -> int:
        normalized_version = document_version.strip()
        if not normalized_version:
            return 0

        return (
            self._db.query(IncidentRetrievalDocumentModel)
            .filter(IncidentRetrievalDocumentModel.document_version == normalized_version)
            .count()
        )

    def list_missing_case_ids(
        self,
        *,
        document_version: str,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[str]:
        normalized_version = document_version.strip()
        if not normalized_version:
            return []

        query = (
            self._db.query(IncidentCaseModel.case_id)
            .outerjoin(
                IncidentRetrievalDocumentModel,
                (
                    IncidentCaseModel.case_id
                    == IncidentRetrievalDocumentModel.case_id
                )
                & (
                    IncidentRetrievalDocumentModel.document_version
                    == normalized_version
                ),
            )
            .filter(IncidentRetrievalDocumentModel.case_id.is_(None))
            .order_by(
                IncidentCaseModel.created_at.asc(),
                IncidentCaseModel.case_id.asc(),
            )
        )

        if offset > 0:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return [row[0] for row in query.all()]

    def find_similar(
        self,
        embedding: list[float],
        *,
        limit: int = 5,
        distance_threshold: float | None = None,
        document_version: str | None = None,
    ) -> list[IncidentRetrievalDocumentSimilarityResult]:
        return self.search_similar_by_embedding(
            embedding,
            limit=limit,
            distance_threshold=distance_threshold,
            document_version=document_version,
        )

    def search_similar_by_embedding(
        self,
        embedding: list[float],
        *,
        limit: int = 5,
        distance_threshold: float | None = None,
        document_version: str | None = None,
    ) -> list[IncidentRetrievalDocumentSimilarityResult]:
        normalized_embedding = self._normalize_embedding(embedding)
        if len(normalized_embedding) == 0:
            raise ValueError("embedding no puede estar vacío.")
        if limit <= 0:
            raise ValueError("limit debe ser mayor que cero.")
        if distance_threshold is not None and distance_threshold < 0:
            raise ValueError("distance_threshold no puede ser negativo.")

        halfvec_embedding = cast(
            IncidentRetrievalDocumentModel.embedding,
            HALFVEC(IncidentRetrievalDocumentModel.EMBEDDING_DIMENSIONS),
        )
        distance = halfvec_embedding.cosine_distance(normalized_embedding)
        query: Query = self._db.query(
            IncidentRetrievalDocumentModel,
            distance.label("distance"),
        )

        if document_version is not None:
            normalized_version = document_version.strip()
            if not normalized_version:
                return []
            query = query.filter(
                IncidentRetrievalDocumentModel.document_version == normalized_version
            )

        if distance_threshold is not None:
            query = query.filter(distance <= distance_threshold)

        rows = query.order_by(distance.asc()).limit(limit).all()
        return [
            IncidentRetrievalDocumentSimilarityResult(
                case_id=document.case_id,
                document_version=document.document_version,
                document_text=document.document_text,
                distance=float(row_distance),
            )
            for document, row_distance in rows
        ]

    def _normalize_embedding(self, embedding: list[float] | object) -> list[float]:
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()

        return [float(value) for value in embedding]  # type: ignore[arg-type]
