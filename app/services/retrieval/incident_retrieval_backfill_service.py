from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.repositories.incident_case_repository import IncidentCaseRepository
from app.db.repositories.incident_retrieval_document_repository import (
    IncidentRetrievalDocumentRepository,
)
from app.services.retrieval.incident_retrieval_indexing_service import (
    IncidentRetrievalIndexingResult,
    IncidentRetrievalIndexingService,
)


@dataclass(slots=True)
class IncidentRetrievalBackfillCaseResult:
    case_id: str
    status: str
    reason: str | None = None
    indexing_result: IncidentRetrievalIndexingResult | None = None


@dataclass(slots=True)
class IncidentRetrievalBackfillSummary:
    document_version: str
    requested: int
    processed: int
    succeeded: int
    failed: int
    skipped: int
    results: list[IncidentRetrievalBackfillCaseResult]


class IncidentRetrievalBackfillService:
    """
    Orquesta backfill histórico sobre incidentes persistidos.
    """

    def __init__(
        self,
        db_session: Session,
        *,
        indexing_service: IncidentRetrievalIndexingService | None = None,
        incident_case_repository: IncidentCaseRepository | None = None,
        document_repository: IncidentRetrievalDocumentRepository | None = None,
        document_version: str | None = None,
    ) -> None:
        self._db = db_session
        self._indexing_service = indexing_service or IncidentRetrievalIndexingService(
            db_session
        )
        self._incident_case_repository = incident_case_repository or IncidentCaseRepository(
            db_session
        )
        self._document_repository = document_repository or IncidentRetrievalDocumentRepository(
            db_session
        )
        self._document_version = (
            document_version or settings.retrieval.document_version
        ).strip()

        if not self._document_version:
            raise ValueError("document_version no puede estar vacío.")

    def count_total_cases(self) -> int:
        return self._incident_case_repository.count_all()

    def count_indexed_cases(self) -> int:
        return self._document_repository.count_by_version(self._document_version)

    def list_missing_case_ids(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[str]:
        return self._document_repository.list_missing_case_ids(
            document_version=self._document_version,
            limit=limit,
            offset=offset,
        )

    def index_cases(
        self,
        case_ids: list[str],
        *,
        skip_existing: bool = False,
    ) -> IncidentRetrievalBackfillSummary:
        results: list[IncidentRetrievalBackfillCaseResult] = []

        for case_id in case_ids:
            normalized_case_id = case_id.strip()
            if not normalized_case_id:
                results.append(
                    IncidentRetrievalBackfillCaseResult(
                        case_id=case_id,
                        status="failed",
                        reason="case_id vacío.",
                    )
                )
                continue

            existing = self._document_repository.get_by_case_id_and_version(
                normalized_case_id,
                self._document_version,
            )
            if skip_existing and existing is not None:
                results.append(
                    IncidentRetrievalBackfillCaseResult(
                        case_id=normalized_case_id,
                        status="skipped",
                        reason=(
                            "Ya existe un documento indexado para "
                            f"{self._document_version}."
                        ),
                    )
                )
                continue

            try:
                indexing_result = self._indexing_service.index_case(normalized_case_id)
            except Exception as exc:
                self._db.rollback()
                results.append(
                    IncidentRetrievalBackfillCaseResult(
                        case_id=normalized_case_id,
                        status="failed",
                        reason=str(exc),
                    )
                )
                continue

            if indexing_result is None:
                results.append(
                    IncidentRetrievalBackfillCaseResult(
                        case_id=normalized_case_id,
                        status="failed",
                        reason=f"Incident with case_id '{normalized_case_id}' was not found.",
                    )
                )
                continue

            results.append(
                IncidentRetrievalBackfillCaseResult(
                    case_id=normalized_case_id,
                    status="ok",
                    indexing_result=indexing_result,
                )
            )

        return self._build_summary(results=results, requested=len(case_ids))

    def index_all_cases(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
        skip_existing: bool = False,
    ) -> IncidentRetrievalBackfillSummary:
        case_ids = self._incident_case_repository.list_case_ids(
            limit=limit,
            offset=offset,
        )
        return self.index_cases(case_ids, skip_existing=skip_existing)

    def index_missing_cases(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> IncidentRetrievalBackfillSummary:
        case_ids = self.list_missing_case_ids(limit=limit, offset=offset)
        return self.index_cases(case_ids, skip_existing=False)

    def _build_summary(
        self,
        *,
        results: list[IncidentRetrievalBackfillCaseResult],
        requested: int,
    ) -> IncidentRetrievalBackfillSummary:
        succeeded = sum(1 for item in results if item.status == "ok")
        failed = sum(1 for item in results if item.status == "failed")
        skipped = sum(1 for item in results if item.status == "skipped")

        return IncidentRetrievalBackfillSummary(
            document_version=self._document_version,
            requested=requested,
            processed=len(results),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            results=results,
        )
