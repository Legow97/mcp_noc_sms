from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.conversation.contracts.historical_context import (
    ConversationHistoricalContext,
    IncidentSnapshot,
    SemanticSearchMatchSnapshot,
    TimelineEntrySnapshot,
    TroubleshootingActionSnapshot,
)
from app.conversation.contracts.requests import ConversationRequest
from app.conversation.contracts.session_models import ConversationSessionState
from app.db.models import (
    IncidentCaseModel,
    IncidentTimelineEntryModel,
    TroubleshootingActionModel,
)
from app.db.repositories.incident_case_repository import IncidentCaseRepository
from app.db.repositories.incident_timeline_entry_repository import (
    IncidentTimelineEntryRepository,
)
from app.db.repositories.troubleshooting_action_repository import (
    TroubleshootingActionRepository,
)
from app.services.retrieval.incident_semantic_search_service import (
    IncidentSemanticSearchService,
)


class HistoricalContextService:
    """
    Capa interna de recuperación histórica para el flujo conversacional.

    Centraliza acceso a lookup exacto, timeline y búsqueda semántica sin
    acoplar el agente a repositorios ni endpoints HTTP internos.
    """

    _INCIDENT_ID_PATTERN = re.compile(
        r"\bINC(?=[0-9A-Z-]*\d)[0-9A-Z-]+\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        db_session: Session,
        *,
        incident_repository: IncidentCaseRepository | None = None,
        timeline_repository: IncidentTimelineEntryRepository | None = None,
        troubleshooting_repository: TroubleshootingActionRepository | None = None,
        semantic_search_service: IncidentSemanticSearchService | None = None,
        semantic_limit: int = 3,
        semantic_max_limit: int = 10,
    ) -> None:
        self._db_session = db_session
        self._incident_repository = incident_repository or IncidentCaseRepository(
            db_session
        )
        self._timeline_repository = (
            timeline_repository or IncidentTimelineEntryRepository(db_session)
        )
        self._troubleshooting_repository = (
            troubleshooting_repository or TroubleshootingActionRepository(db_session)
        )
        self._semantic_search_service = semantic_search_service
        self._semantic_limit = semantic_limit
        self._semantic_max_limit = semantic_max_limit

    def build_for_request(
        self,
        request: ConversationRequest,
        session_state: ConversationSessionState | None = None,
    ) -> ConversationHistoricalContext:
        message = request.message.strip()
        incident_ids = self.extract_incident_ids(message)
        context = ConversationHistoricalContext(incident_ids=incident_ids)
        wants_semantic_search = self._looks_like_semantic_search_request(message)
        requested_limit = self._extract_requested_limit(message)
        active_incident_id = self._resolve_active_incident_id(session_state)

        if incident_ids:
            self._apply_exact_lookup(context, incident_ids[0])

            if self._looks_like_timeline_request(message):
                self._apply_timeline_lookup(context, incident_ids[0])

            if wants_semantic_search:
                self._apply_semantic_search_for_incident(
                    context,
                    incident_ids[0],
                    limit=requested_limit,
                )

            return context

        if wants_semantic_search and active_incident_id and self._references_active_case(message):
            context.incident_ids = [active_incident_id]
            self._apply_exact_lookup(context, active_incident_id)
            self._apply_semantic_search_for_incident(
                context,
                active_incident_id,
                limit=requested_limit,
            )
            return context

        if wants_semantic_search:
            self._apply_semantic_search_text(
                context,
                message,
                limit=requested_limit,
                query_source="user_message",
            )

        return context

    @classmethod
    def extract_incident_ids(cls, text: str) -> list[str]:
        return list(
            dict.fromkeys(
                match.upper()
                for match in cls._INCIDENT_ID_PATTERN.findall(text)
            )
        )

    def _apply_exact_lookup(
        self,
        context: ConversationHistoricalContext,
        incident_id: str,
    ) -> None:
        incident = self._incident_repository.get_by_case_id(incident_id)

        if incident is None:
            context.retrieval_notes.append(
                f"No se encontró un incidente persistido con case_id={incident_id}."
            )
            return

        context.primary_incident = self._to_incident_snapshot(incident)
        context.troubleshooting_actions = [
            self._to_action_snapshot(action)
            for action in self._troubleshooting_repository.list_by_case_id(incident_id)
        ]
        context.retrieval_notes.append(
            f"Exact lookup recuperó el incidente {incident_id}."
        )

    def _apply_timeline_lookup(
        self,
        context: ConversationHistoricalContext,
        incident_id: str,
    ) -> None:
        context.timeline_entries = [
            self._to_timeline_snapshot(entry)
            for entry in self._timeline_repository.list_by_case_id(incident_id)
        ]

        if context.timeline_entries:
            context.retrieval_notes.append(
                f"Timeline recuperado con {len(context.timeline_entries)} eventos."
            )
        else:
            context.retrieval_notes.append(
                f"No hay timeline persistido para {incident_id}."
            )

    def _apply_semantic_search_text(
        self,
        context: ConversationHistoricalContext,
        query_text: str,
        *,
        limit: int | None = None,
        query_source: str,
    ) -> None:
        effective_limit = self._resolve_semantic_limit(limit)
        try:
            semantic_search_service = (
                self._semantic_search_service
                or IncidentSemanticSearchService(self._db_session)
            )
            result = semantic_search_service.search(
                query_text,
                limit=effective_limit,
            )
        except Exception as exc:
            context.errors.append(f"semantic_search_failed: {exc}")
            return

        self._apply_semantic_search_result(
            context,
            result.results,
            query_text=result.query_text,
            query_source=query_source,
            limit=effective_limit,
        )

    def _apply_semantic_search_for_incident(
        self,
        context: ConversationHistoricalContext,
        incident_id: str,
        *,
        limit: int | None = None,
    ) -> None:
        if context.primary_incident is None:
            context.retrieval_notes.append(
                f"No se ejecutó semantic search porque {incident_id} no existe en persistencia."
            )
            return

        effective_limit = self._resolve_semantic_limit(limit)
        try:
            semantic_search_service = (
                self._semantic_search_service
                or IncidentSemanticSearchService(self._db_session)
            )
            result = semantic_search_service.search_similar_to_case(
                incident_id,
                limit=effective_limit,
            )
        except Exception as exc:
            context.errors.append(f"semantic_search_failed: {exc}")
            return

        if not result.results:
            fallback_query_text = self._build_incident_query_text(context.primary_incident)
            self._apply_semantic_search_text(
                context,
                fallback_query_text,
                limit=effective_limit,
                query_source=f"incident_snapshot:{incident_id}",
            )
            return

        self._apply_semantic_search_result(
            context,
            result.results,
            query_text=f"case_id:{incident_id}",
            query_source=f"retrieval_document:{incident_id}",
            limit=effective_limit,
        )

    def _apply_semantic_search_result(
        self,
        context: ConversationHistoricalContext,
        matches: list,
        *,
        query_text: str,
        query_source: str,
        limit: int,
    ) -> None:
        context.semantic_matches = [
            SemanticSearchMatchSnapshot(
                case_id=match.case_id,
                document_version=match.document_version,
                document_text=match.document_text,
                distance=match.distance,
            )
            for match in matches
        ]
        context.semantic_query_text = query_text
        context.semantic_query_source = query_source
        context.semantic_limit = limit
        context.retrieval_notes.append(
            f"Semantic search recuperó {len(context.semantic_matches)} resultados."
        )

    @staticmethod
    def _looks_like_timeline_request(message: str) -> bool:
        normalized = message.lower()
        return any(
            token in normalized
            for token in [
                "línea de tiempo",
                "linea de tiempo",
                "timeline",
                "evolución",
                "evolucion",
                "cronología",
                "cronologia",
            ]
        )

    @staticmethod
    def _looks_like_semantic_search_request(message: str) -> bool:
        normalized = message.lower()
        return any(
            token in normalized
            for token in [
                "busca",
                "buscar",
                "casos similares",
                "casos parecidos",
                "incidentes parecidos",
                "connection refused",
                "timeout",
                "error",
                "apim",
                "no funciona",
                "no responde",
                "latencia",
                "network",
                "se está cargando",
                "se esta cargando",
                "cómo se resolvió",
                "como se resolvio",
                "incidentes similares",
                "problema similar",
                "problemas similares",
                "parecido",
                "parecidos",
                "similar",
                "similares",
                "se resolvió antes",
                "se resolvio antes",
                "este tipo de problema",
            ]
        )

    @staticmethod
    def _references_active_case(message: str) -> bool:
        normalized = message.lower()
        return any(
            token in normalized
            for token in [
                "este",
                "esta",
                "este caso",
                "este incidente",
                "este problema",
                "tipo de problema",
                "antes",
                "similar",
                "similares",
                "parecido",
                "parecidos",
            ]
        )

    def _extract_requested_limit(self, message: str) -> int | None:
        normalized = message.lower()
        patterns = [
            r"\b(?:busca|buscar|muestra|mu[eé]strame|top)\s+(\d{1,2})\b",
            r"\b(\d{1,2})\s+(?:casos|incidentes|resultados)\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, normalized)
            if match:
                return self._resolve_semantic_limit(int(match.group(1)))
        return None

    def _resolve_semantic_limit(self, limit: int | None) -> int:
        requested_limit = limit or self._semantic_limit
        return max(1, min(requested_limit, self._semantic_max_limit))

    @staticmethod
    def _resolve_active_incident_id(
        session_state: ConversationSessionState | None,
    ) -> str | None:
        if session_state is None or not session_state.active_incident_ids:
            return None
        return session_state.active_incident_ids[-1].strip().upper() or None

    @staticmethod
    def _build_incident_query_text(incident: IncidentSnapshot) -> str:
        parts = [
            incident.header,
            incident.failure_text,
            incident.impact_text,
            incident.probable_cause_text,
            incident.resolution_summary,
            " ".join(incident.services_affected),
            " ".join(incident.symptoms),
            " ".join(incident.tags),
        ]
        return " ".join(part.strip() for part in parts if part and part.strip())

    @staticmethod
    def _to_incident_snapshot(incident: IncidentCaseModel) -> IncidentSnapshot:
        return IncidentSnapshot(
            case_id=incident.case_id,
            source_type=incident.source_type,
            status=incident.status,
            header=incident.header,
            failure_text=incident.failure_text,
            impact_text=incident.impact_text,
            start_time=incident.start_time,
            solution_time=incident.solution_time,
            raw_sms=incident.raw_sms,
            probable_cause_text=incident.probable_cause_text,
            resolution_summary=incident.resolution_summary,
            services_affected=incident.services_affected or [],
            symptoms=incident.symptoms or [],
            teams_involved=incident.teams_involved or [],
            tickets=incident.tickets or [],
            tags=incident.tags or [],
        )

    @staticmethod
    def _to_timeline_snapshot(
        entry: IncidentTimelineEntryModel,
    ) -> TimelineEntrySnapshot:
        return TimelineEntrySnapshot(
            event_time=entry.event_time,
            event_text=entry.event_text,
            sequence_order=entry.sequence_order,
        )

    @staticmethod
    def _to_action_snapshot(
        action: TroubleshootingActionModel,
    ) -> TroubleshootingActionSnapshot:
        return TroubleshootingActionSnapshot(
            action_text=action.action_text,
            action_type=action.action_type,
            action_role=action.action_role,
            target_component=action.target_component,
            sequence_order=action.sequence_order,
        )
