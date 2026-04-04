from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.repositories.incident_case_repository import IncidentCaseRepository
from app.db.repositories.incident_timeline_entry_repository import (
    IncidentTimelineEntryRepository,
)
from app.db.repositories.troubleshooting_action_repository import (
    TroubleshootingActionRepository,
)


@dataclass(slots=True)
class IncidentRetrievalCaseData:
    case_id: str
    start_time: datetime | None
    header: str | None
    failure_text: str | None
    impact_text: str | None
    services_affected: list[str]
    components_affected: list[str]
    solution_time: datetime | None
    probable_cause_text: str | None
    resolution_summary: str | None
    tags: list[str]


@dataclass(slots=True)
class IncidentRetrievalTimelineEntryData:
    event_time: str | None
    event_text: str | None
    sequence_order: int


@dataclass(slots=True)
class IncidentRetrievalTroubleshootingActionData:
    sequence_order: int
    action_text: str | None
    action_type: str | None


@dataclass(slots=True)
class IncidentRetrievalSourceData:
    incident_case: IncidentRetrievalCaseData
    timeline_entries: list[IncidentRetrievalTimelineEntryData]
    troubleshooting_actions: list[IncidentRetrievalTroubleshootingActionData]


class IncidentRetrievalSourceReader:
    """
    Lee desde la base de datos la data persistida mínima necesaria
    para construir document_text_v1.
    """

    def __init__(
        self,
        db_session: Session,
        incident_case_repository: IncidentCaseRepository | None = None,
        timeline_entry_repository: IncidentTimelineEntryRepository | None = None,
        troubleshooting_action_repository: TroubleshootingActionRepository | None = None,
    ) -> None:
        self._db = db_session
        self._incident_case_repository = (
            incident_case_repository or IncidentCaseRepository(db_session)
        )
        self._timeline_entry_repository = (
            timeline_entry_repository or IncidentTimelineEntryRepository(db_session)
        )
        self._troubleshooting_action_repository = (
            troubleshooting_action_repository
            or TroubleshootingActionRepository(db_session)
        )

    def read(self, case_id: str) -> IncidentRetrievalSourceData | None:
        """
        Recupera el incidente y sus colecciones relacionadas desde la BD.

        Devuelve None si el case_id no existe o si llega vacío.
        """
        normalized_case_id = case_id.strip()
        if not normalized_case_id:
            return None

        incident_case = self._incident_case_repository.get_by_case_id(normalized_case_id)
        if incident_case is None:
            return None

        timeline_entries = self._timeline_entry_repository.list_by_case_id(
            normalized_case_id
        )
        troubleshooting_actions = (
            self._troubleshooting_action_repository.list_by_case_id(normalized_case_id)
        )

        return IncidentRetrievalSourceData(
            incident_case=IncidentRetrievalCaseData(
                case_id=incident_case.case_id,
                start_time=incident_case.start_time,
                header=incident_case.header,
                failure_text=incident_case.failure_text,
                impact_text=incident_case.impact_text,
                services_affected=list(incident_case.services_affected or []),
                components_affected=list(incident_case.components_affected or []),
                solution_time=incident_case.solution_time,
                probable_cause_text=incident_case.probable_cause_text,
                resolution_summary=incident_case.resolution_summary,
                tags=list(incident_case.tags or []),
            ),
            timeline_entries=[
                IncidentRetrievalTimelineEntryData(
                    event_time=entry.event_time,
                    event_text=entry.event_text,
                    sequence_order=entry.sequence_order,
                )
                for entry in timeline_entries
            ],
            troubleshooting_actions=[
                IncidentRetrievalTroubleshootingActionData(
                    sequence_order=action.sequence_order,
                    action_text=action.action_text,
                    action_type=action.action_type,
                )
                for action in troubleshooting_actions
            ],
        )
