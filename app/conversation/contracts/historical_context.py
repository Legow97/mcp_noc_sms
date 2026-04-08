from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class IncidentSnapshot(BaseModel):
    """
    Vista conversacional de un incidente persistido.
    """

    case_id: str = Field(..., min_length=1)
    source_type: str
    status: str
    header: str | None = None
    failure_text: str | None = None
    impact_text: str | None = None
    start_time: datetime | None = None
    solution_time: datetime | None = None
    raw_sms: str | None = None
    probable_cause_text: str | None = None
    resolution_summary: str | None = None
    services_affected: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    teams_involved: list[str] = Field(default_factory=list)
    tickets: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class TimelineEntrySnapshot(BaseModel):
    """
    Evento real del timeline persistido de un incidente.
    """

    event_time: str | None = None
    event_text: str
    sequence_order: int


class TroubleshootingActionSnapshot(BaseModel):
    """
    Acción operativa persistida asociada a un incidente.
    """

    action_text: str
    action_type: str | None = None
    action_role: str | None = None
    target_component: str | None = None
    sequence_order: int


class SemanticSearchMatchSnapshot(BaseModel):
    """
    Resultado conversacional de búsqueda semántica histórica.
    """

    case_id: str
    document_version: str
    document_text: str
    distance: float


class ConversationHistoricalContext(BaseModel):
    """
    Evidencia histórica recuperada para un turno conversacional.
    """

    incident_ids: list[str] = Field(default_factory=list)
    primary_incident: IncidentSnapshot | None = None
    timeline_entries: list[TimelineEntrySnapshot] = Field(default_factory=list)
    troubleshooting_actions: list[TroubleshootingActionSnapshot] = Field(
        default_factory=list
    )
    semantic_matches: list[SemanticSearchMatchSnapshot] = Field(default_factory=list)
    semantic_query_text: str | None = None
    semantic_query_source: str | None = None
    semantic_limit: int | None = None
    retrieval_notes: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @property
    def has_evidence(self) -> bool:
        return any(
            [
                self.primary_incident is not None,
                self.timeline_entries,
                self.troubleshooting_actions,
                self.semantic_matches,
            ]
        )
