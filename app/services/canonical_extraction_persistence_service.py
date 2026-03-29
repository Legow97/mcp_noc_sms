from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import re

from sqlalchemy.orm import Session

from app.agentic.contracts.canonical_extraction import CanonicalExtractionResult
from app.db.repositories.incident_case_repository import IncidentCaseRepository
from app.db.repositories.incident_timeline_entry_repository import (
    IncidentTimelineEntryRepository,
)
from app.db.repositories.troubleshooting_action_repository import (
    TroubleshootingActionRepository,
)
from app.services.mappers.canonical_extraction_mapper import (
    CanonicalExtractionMapper,
    CanonicalExtractionPersistenceBundle,
)


@dataclass(slots=True)
class CanonicalPersistenceResult:
    """
    Resultado resumido de la persistencia.
    """
    case_id: str
    incident_status: str
    timeline_entries_saved: int
    troubleshooting_actions_saved: int


class CanonicalExtractionPersistenceService:
    _VALID_CASE_ID_PREFIXES = ("INC", "REQ", "TAS", "CRQ")
    _VALID_CASE_ID_PATTERN = re.compile(
        r"^(INC|REQ|TAS|CRQ)(?=[A-Z0-9]*\d)[A-Z0-9]+$"
    )

    """
    Persiste un resultado canónico aceptado del subsistema agentic
    en una sola transacción.

    Responsabilidades:
    - validar si el resultado debe persistirse
    - resolver/generar case_id
    - mapear a entidades ORM
    - guardar case + timeline + actions
    - hacer commit/rollback de forma atómica
    """

    def __init__(
        self,
        db_session: Session,
        mapper: CanonicalExtractionMapper | None = None,
    ) -> None:
        self._db = db_session
        self._mapper = mapper or CanonicalExtractionMapper()

        self._incident_case_repository = IncidentCaseRepository(db_session)
        self._timeline_entry_repository = IncidentTimelineEntryRepository(db_session)
        self._troubleshooting_action_repository = TroubleshootingActionRepository(db_session)

    def save_accepted_result(
        self,
        *,
        extraction: CanonicalExtractionResult,
        judge_decision: str,
        judge_evaluation: dict[str, Any] | None = None,
        trace: Any | None = None,
        case_id: str | None = None,
    ) -> CanonicalPersistenceResult:
        """
        Persiste el resultado canónico si la decisión del juez es accepted.

        Parámetros:
        - extraction: resultado canónico aceptado/revisado
        - judge_decision: decisión lógica del juez
        - judge_evaluation: metadata opcional del juez
        - trace: traza opcional del flujo agentic
        - case_id: permite inyectar un case_id externo si ya fue resuelto antes

        Lanza:
        - ValueError si judge_decision no permite persistencia
        - Exception propagada si falla la transacción
        """
        print(
            "[PERSISTENCE SERVICE] save_accepted_result extraction recibido:",
            extraction.model_dump(mode="json"),
        )
        print(
            "[PERSISTENCE SERVICE] save_accepted_result judge_decision:",
            judge_decision,
        )
        print(
            "[PERSISTENCE SERVICE] save_accepted_result judge_evaluation:",
            judge_evaluation,
        )
        print("[PERSISTENCE SERVICE] save_accepted_result trace:", trace)

        if not self._should_persist(judge_decision):
            print(
                "[ERROR] [PERSISTENCE SERVICE] judge_decision no permite persistencia:",
                judge_decision,
            )
            raise ValueError(
                f"No se puede persistir extracción con judge_decision={judge_decision!r}"
            )

        resolved_case_id = case_id or self._resolve_case_id(extraction)
        print(
            "[PERSISTENCE SERVICE] case_id resuelto:",
            resolved_case_id,
        )

        bundle = self._mapper.to_persistence_bundle(
            extraction=extraction,
            case_id=resolved_case_id,
            judge_evaluation=judge_evaluation,
            trace=trace,
        )
        print(
            "[PERSISTENCE SERVICE] bundle generado por el mapper:",
            self._summarize_bundle(bundle),
        )

        try:
            self._persist_bundle(bundle)
            print("[TRANSACTION] Antes de commit()", {"case_id": resolved_case_id})
            self._db.commit()
            print("[TRANSACTION] Después de commit()", {"case_id": resolved_case_id})
        except Exception as exc:
            print(
                "[ERROR] [TRANSACTION] Excepción antes de rollback():",
                str(exc),
            )
            self._db.rollback()
            print("[TRANSACTION] rollback() ejecutado", {"case_id": resolved_case_id})
            raise

        return CanonicalPersistenceResult(
            case_id=resolved_case_id,
            incident_status=bundle.incident_case.status,
            timeline_entries_saved=len(bundle.timeline_entries),
            troubleshooting_actions_saved=len(bundle.troubleshooting_actions),
        )

    def _persist_bundle(
        self,
        bundle: CanonicalExtractionPersistenceBundle,
    ) -> None:
        """
        Registra las entidades ORM en la sesión actual.
        No hace commit; eso queda en save_accepted_result().
        """
        print(
            "[PERSISTENCE SERVICE] Persistiendo bundle:",
            self._summarize_bundle(bundle),
        )
        self._incident_case_repository.add(bundle.incident_case)

        if bundle.timeline_entries:
            self._timeline_entry_repository.add_many(bundle.timeline_entries)

        if bundle.troubleshooting_actions:
            self._troubleshooting_action_repository.add_many(
                bundle.troubleshooting_actions
            )

    def _should_persist(self, judge_decision: str) -> bool:
        """
        Regla prudente actual:
        solo persistir cuando el juez acepte explícitamente.
        """
        return judge_decision.strip().lower() in {
            "accepted",
            "accepted_with_observations",
        }

    def _resolve_case_id(self, extraction: CanonicalExtractionResult) -> str:
        """
        Resuelve el case_id de negocio usando únicamente data canónica
        del subsistema agentic.
        """
        incident = extraction.incident_case

        if incident.case_id:
            normalized_case_id = self._normalize_case_id_candidate(incident.case_id)
            if normalized_case_id:
                return normalized_case_id

        for prefix in self._VALID_CASE_ID_PREFIXES:
            for ticket in incident.tickets:
                normalized_ticket = self._normalize_case_id_candidate(ticket)
                if normalized_ticket and normalized_ticket.startswith(prefix):
                    return normalized_ticket

        raise ValueError(
            "No se pudo resolver case_id desde la salida canónica del agente."
        )

    def _normalize_case_id_candidate(self, value: str) -> str | None:
        """
        Normaliza candidatos tipo ticket/case_id únicamente si respetan
        prefijos válidos y contienen al menos un dígito real.
        """
        normalized = value.strip().upper()
        if not normalized:
            return None

        if self._VALID_CASE_ID_PATTERN.fullmatch(normalized):
            return normalized

        return None

    def _summarize_bundle(
        self,
        bundle: CanonicalExtractionPersistenceBundle,
    ) -> dict[str, Any]:
        return {
            "incident_case": {
                "case_id": bundle.incident_case.case_id,
                "source_type": bundle.incident_case.source_type,
                "status": bundle.incident_case.status,
                "header": bundle.incident_case.header,
                "start_time": bundle.incident_case.start_time.isoformat()
                if bundle.incident_case.start_time is not None
                else None,
                "tickets": bundle.incident_case.tickets,
            },
            "timeline_entries_count": len(bundle.timeline_entries),
            "timeline_entries": [
                {
                    "sequence_order": entry.sequence_order,
                    "event_time": entry.event_time,
                    "event_type": entry.event_type,
                    "event_text": entry.event_text[:160],
                }
                for entry in bundle.timeline_entries
            ],
            "troubleshooting_actions_count": len(bundle.troubleshooting_actions),
            "troubleshooting_actions": [
                {
                    "sequence_order": action.sequence_order,
                    "action_type": action.action_type,
                    "action_role": action.action_role,
                    "target_component": action.target_component,
                    "action_text": action.action_text[:160],
                }
                for action in bundle.troubleshooting_actions
            ],
        }
