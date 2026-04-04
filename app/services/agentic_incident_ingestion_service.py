from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.agentic.orchestrator.orchestration_models import (
    CanonicalExtractionOrchestrationResult,
)
from app.api.schemas.incident_requests import IngestSmsRequest
from app.core.ingestion_trace import (
    bind_case_id,
    bind_judge_result,
    bind_persistence_counts,
    log_ingestion_event,
)
from app.services.canonical_extraction_persistence_service import (
    CanonicalExtractionPersistenceService,
)
from app.services.mappers.canonical_extraction_mapper import (
    CanonicalExtractionMapper,
)
from app.services.retrieval.incident_retrieval_indexing_service import (
    IncidentRetrievalIndexingService,
)


@dataclass(slots=True)
class AgenticIncidentIngestionResult:
    case_id: str
    incident_status: str
    parsed_ok: bool
    indexed: bool
    judge_decision: str
    timeline_entries_saved: int
    troubleshooting_actions_saved: int


class AgenticIncidentIngestionService:
    """
    Orquesta la ingesta de SMS usando el subsistema agentic y
    persiste el resultado canónico aceptado en una sola transacción.
    """

    def __init__(
        self,
        db_session: Session,
        orchestrator: Any,
        retrieval_indexing_service: IncidentRetrievalIndexingService | None = None,
    ) -> None:
        self._db = db_session
        self._orchestrator = orchestrator
        self._persistence_service = CanonicalExtractionPersistenceService(
            db_session=db_session,
            mapper=CanonicalExtractionMapper(),
        )
        self._retrieval_indexing_service = (
            retrieval_indexing_service
            or IncidentRetrievalIndexingService(db_session=db_session)
        )

    def ingest_sms(self, payload: IngestSmsRequest) -> AgenticIncidentIngestionResult:
        log_ingestion_event(
            layer="agentic_service",
            event="payload_received",
            payload={
                "source_channel": payload.source_channel,
                "received_at": payload.received_at.isoformat(),
            },
        )
        print(
            "[AGENTIC SERVICE] ingest_sms payload recibido:",
            payload.model_dump(mode="json"),
        )
        orchestration_result = self._run_orchestrator(payload)
        log_ingestion_event(
            layer="agentic_service",
            event="orchestration_completed",
            payload={
                "has_accepted_result": orchestration_result.accepted_result is not None,
                "judge_decision": getattr(
                    orchestration_result.judge_evaluation,
                    "decision",
                    None,
                ),
                "final_score": getattr(
                    orchestration_result.judge_evaluation,
                    "score",
                    None,
                ),
                "fallback_triggered": orchestration_result.trace.fallback_triggered,
            },
        )
        print(
            "[AGENTIC SERVICE] resultado del orquestador:",
            orchestration_result.model_dump(mode="json"),
        )

        accepted_result = orchestration_result.accepted_result
        judge_evaluation = orchestration_result.judge_evaluation
        trace = orchestration_result.trace

        print(
            "[AGENTIC SERVICE] accepted_result:",
            self._to_jsonable(accepted_result),
        )
        print(
            "[AGENTIC SERVICE] judge_evaluation:",
            self._to_jsonable(judge_evaluation),
        )
        print(
            "[AGENTIC SERVICE] trace:",
            self._to_jsonable(trace),
        )

        if accepted_result is None:
            bind_judge_result(
                judge_decision=getattr(judge_evaluation, "decision", None),
                final_score=getattr(judge_evaluation, "score", None),
                fallback_triggered=getattr(trace, "fallback_triggered", None),
            )
            log_ingestion_event(
                layer="agentic_service",
                event="accepted_result_missing",
                status="error",
                payload={
                    "judge_decision": getattr(judge_evaluation, "decision", None),
                    "final_score": getattr(judge_evaluation, "score", None),
                },
            )
            print(
                "[ERROR] [AGENTIC SERVICE] accepted_result es None; no hay resultado para persistir."
            )
            raise ValueError(
                "El subsistema agentic no devolvió un resultado aceptado para persistir."
            )

        judge_decision = self._extract_judge_decision(judge_evaluation)
        bind_case_id(accepted_result.incident_case.case_id)
        bind_judge_result(
            judge_decision=judge_decision,
            final_score=getattr(judge_evaluation, "score", None),
            fallback_triggered=getattr(trace, "fallback_triggered", None),
        )
        log_ingestion_event(
            layer="agentic_service",
            event="accepted_result_ready",
            payload={
                "case_id": accepted_result.incident_case.case_id,
                "judge_decision": judge_decision,
                "final_score": getattr(judge_evaluation, "score", None),
                "fallback_triggered": getattr(trace, "fallback_triggered", None),
            },
        )
        print("[AGENTIC SERVICE] judge_decision:", judge_decision)

        try:
            persistence_result = self._persistence_service.save_accepted_result(
                extraction=accepted_result,
                judge_decision=judge_decision,
                judge_evaluation=self._to_jsonable(judge_evaluation),
                trace=self._to_jsonable(trace),
            )
        except Exception as exc:
            print("[ERROR] [AGENTIC SERVICE] save_accepted_result falló:", str(exc))
            raise

        indexed = self._index_persisted_case(persistence_result.case_id)
        result = AgenticIncidentIngestionResult(
            case_id=persistence_result.case_id,
            incident_status=persistence_result.incident_status,
            parsed_ok=True,
            indexed=indexed,
            judge_decision=judge_decision,
            timeline_entries_saved=persistence_result.timeline_entries_saved,
            troubleshooting_actions_saved=persistence_result.troubleshooting_actions_saved,
        )
        bind_case_id(result.case_id)
        bind_persistence_counts(
            timeline_entries_count=result.timeline_entries_saved,
            troubleshooting_actions_count=result.troubleshooting_actions_saved,
        )
        log_ingestion_event(
            layer="agentic_service",
            event="ingestion_completed",
            payload={
                "case_id": result.case_id,
                "judge_decision": result.judge_decision,
                "timeline_entries_saved": result.timeline_entries_saved,
                "troubleshooting_actions_saved": result.troubleshooting_actions_saved,
            },
        )
        print(
            "[AGENTIC SERVICE] resultado final de ingest_sms:",
            result,
        )
        return result

    def _index_persisted_case(self, case_id: str) -> bool:
        bind_case_id(case_id)
        log_ingestion_event(
            layer="agentic_service",
            event="retrieval_indexing_started",
            payload={"case_id": case_id},
        )
        print("[AGENTIC SERVICE] retrieval indexing started:", {"case_id": case_id})

        try:
            indexing_result = self._retrieval_indexing_service.index_case(case_id)
        except Exception as exc:
            self._db.rollback()
            log_ingestion_event(
                layer="agentic_service",
                event="retrieval_indexing_failed",
                status="error",
                error=str(exc),
                payload={"case_id": case_id},
            )
            print(
                "[ERROR] [AGENTIC SERVICE] retrieval indexing failed:",
                {"case_id": case_id, "error": str(exc)},
            )
            return False

        if indexing_result is None:
            log_ingestion_event(
                layer="agentic_service",
                event="retrieval_indexing_skipped",
                status="error",
                payload={
                    "case_id": case_id,
                    "reason": "case_not_found_in_database",
                },
            )
            print(
                "[ERROR] [AGENTIC SERVICE] retrieval indexing returned no source data:",
                {"case_id": case_id},
            )
            return False

        log_ingestion_event(
            layer="agentic_service",
            event="retrieval_indexing_completed",
            payload={
                "case_id": case_id,
                "document_version": indexing_result.document_version,
                "created": indexing_result.created,
                "embedding_dimensions": indexing_result.embedding_dimensions,
                "document_text_length": indexing_result.document_text_length,
            },
        )
        print(
            "[AGENTIC SERVICE] retrieval indexing completed:",
            {
                "case_id": case_id,
                "document_version": indexing_result.document_version,
                "created": indexing_result.created,
            },
        )
        return indexing_result.indexed

    def _run_orchestrator(
        self,
        payload: IngestSmsRequest,
    ) -> CanonicalExtractionOrchestrationResult:
        """
        Ejecuta el orquestador real del proyecto.
        El contrato actual del request expone `raw_text`, que es el SMS fuente.
        """
        print("[ORCHESTRATOR] texto enviado al orquestador:", payload.raw_text)
        log_ingestion_event(
            layer="agentic_service",
            event="orchestrator_started",
            payload={"raw_sms_preview": " ".join(payload.raw_text.split())[:240]},
        )
        try:
            result = self._orchestrator.extract(payload.raw_text)
        except Exception as exc:
            log_ingestion_event(
                layer="agentic_service",
                event="orchestrator_failed",
                status="error",
                error=str(exc),
            )
            print("[ERROR] [ORCHESTRATOR] Falló extract():", str(exc))
            raise

        print(
            "[ORCHESTRATOR] resultado bruto devuelto por el orquestador:",
            result.model_dump(mode="json"),
        )
        return result

    def _extract_judge_decision(self, judge_evaluation: Any) -> str:
        """
        Resuelve la decisión del juez desde el objeto retornado por el orquestador.
        """
        decision = getattr(judge_evaluation, "decision", None)

        if isinstance(decision, str) and decision.strip():
            normalized = decision.strip().lower()

            if normalized in {"accepted", "accepted_with_observations"}:
                return normalized

            return normalized

        if isinstance(judge_evaluation, dict):
            raw_decision = judge_evaluation.get("decision")
            if isinstance(raw_decision, str) and raw_decision.strip():
                return raw_decision.strip().lower()

        print(
            "[ERROR] [AGENTIC SERVICE] No se pudo resolver judge_decision desde judge_evaluation:",
            self._to_jsonable(judge_evaluation),
        )
        raise ValueError("No se pudo resolver judge_decision desde judge_evaluation.")

    def _to_jsonable(self, value: Any) -> Any:
        """
        Convierte objetos Pydantic del subsistema agentic a payload serializable.
        """
        if value is None:
            return None

        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")

        return value
