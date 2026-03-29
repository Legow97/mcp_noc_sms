from datetime import datetime

from pydantic import BaseModel

from app.domain.enums import IngestionStatus, IncidentStatus


class IngestSmsResponse(BaseModel):
    """
    Response base para la ingesta de SMS.
    """

    ingestion_status: IngestionStatus
    incident_status: IncidentStatus | None = None
    case_id: str | None = None
    parsed_ok: bool = False
    indexed: bool = False


class ParserOutputResponse(BaseModel):
    """
    Metadatos de trazabilidad del parser/extractor.
    """

    parser_name: str | None = None
    parser_version: str | None = None
    parsing_mode: str | None = None
    rulebook_path: str | None = None
    rulebook_version: str | None = None
    rulebook_enabled: bool | None = None
    header_detected: bool | None = None
    failure_detected: bool | None = None
    impact_detected: bool | None = None
    start_time_detected: bool | None = None


class IncidentCaseResponse(BaseModel):
    """
    Response simplificado para consultar un incidente persistido.
    """

    case_id: str
    source_type: str
    header: str | None
    failure_text: str
    impact_text: str | None
    start_time: datetime | None
    incident_status: IncidentStatus
    pending_rca: bool
    raw_sms: str | None
    parser_output: ParserOutputResponse | None = None


class IncidentCaseSummaryResponse(BaseModel):
    """
    Response resumido para listar incidentes.
    """

    case_id: str
    source_type: str
    header: str | None
    start_time: datetime | None
    incident_status: IncidentStatus
    pending_rca: bool


class IncidentTimelineEntryResponse(BaseModel):
    """
    Response para una entrada de timeline del incidente.
    """

    event_id: str
    case_id: str
    event_time: str | None
    event_text: str
    event_type: str | None
    team: str | None
    action_detected: str | None
    observation_detected: str | None
    sequence_order: int


class TroubleshootingActionResponse(BaseModel):
    """
    Response para una acción de troubleshooting asociada a un incidente.
    """

    action_id: str
    case_id: str
    action_text: str
    action_type: str | None
    action_role: str | None
    target_component: str | None
    outcome: str | None
    was_effective: bool | None
    sequence_order: int
