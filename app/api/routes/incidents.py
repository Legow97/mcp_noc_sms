from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import db_session_dependency
from app.api.schemas.incident_requests import IngestSmsRequest
from app.api.schemas.incident_responses import (
    IncidentCaseResponse,
    IncidentCaseSummaryResponse,
    IncidentTimelineEntryResponse,
    IngestSmsResponse,
    ParserOutputResponse,
    TroubleshootingActionResponse,
)
from app.db.repositories.incident_case_repository import IncidentCaseRepository
from app.db.repositories.incident_timeline_entry_repository import (
    IncidentTimelineEntryRepository,
)
from app.db.repositories.troubleshooting_action_repository import (
    TroubleshootingActionRepository,
)
from app.domain.enums import IngestionStatus, IncidentStatus
from app.services.incident_ingestion_service import IncidentIngestionService


router = APIRouter(
    prefix="/api/v1/incidents",
    tags=["incidents"],
)


@router.get(
    "/ping",
    status_code=status.HTTP_200_OK,
)
def ping_incidents_module() -> dict[str, str]:
    return {
        "module": "incidents",
        "status": "ready",
    }


@router.post(
    "/ingest-sms",
    response_model=IngestSmsResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def ingest_sms(
    payload: IngestSmsRequest,
    db: Session = Depends(db_session_dependency),
) -> IngestSmsResponse:
    """
    Endpoint inicial de ingesta de SMS.

    La lógica de aplicación se delega al servicio de ingesta.
    """
    ingestion_service = IncidentIngestionService(db)
    persisted_case = ingestion_service.ingest_sms(payload)

    return IngestSmsResponse(
        ingestion_status=IngestionStatus.ACCEPTED,
        incident_status=IncidentStatus.CLOSED,
        case_id=persisted_case.case_id,
        parsed_ok=False,
        indexed=False,
    )


@router.get(
    "/{case_id}",
    response_model=IncidentCaseResponse,
    status_code=status.HTTP_200_OK,
)
def get_incident_by_case_id(
    case_id: str,
    db: Session = Depends(db_session_dependency),
) -> IncidentCaseResponse:
    """
    Recupera un incidente persistido por su case_id.
    """
    repository = IncidentCaseRepository(db)
    incident_case = repository.get_by_case_id(case_id)

    if incident_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with case_id '{case_id}' was not found.",
        )

    return IncidentCaseResponse(
    case_id=incident_case.case_id,
    source_type=incident_case.source_type,
    header=incident_case.header,
    failure_text=incident_case.failure_text,
    impact_text=incident_case.impact_text,
    incident_status=IncidentStatus(incident_case.status),
    pending_rca=incident_case.pending_rca,
    raw_sms=incident_case.raw_sms,
    parser_output=ParserOutputResponse(**incident_case.parser_output_json)
    if incident_case.parser_output_json
    else None,
)


@router.get(
    "/{case_id}/timeline",
    response_model=list[IncidentTimelineEntryResponse],
    status_code=status.HTTP_200_OK,
)
def get_incident_timeline(
    case_id: str,
    db: Session = Depends(db_session_dependency),
) -> list[IncidentTimelineEntryResponse]:
    """
    Recupera la cronología (timeline) asociada a un incidente.
    """
    incident_repository = IncidentCaseRepository(db)
    incident_case = incident_repository.get_by_case_id(case_id)

    if incident_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with case_id '{case_id}' was not found.",
        )

    timeline_repository = IncidentTimelineEntryRepository(db)
    timeline_entries = timeline_repository.list_by_case_id(case_id)

    return [
        IncidentTimelineEntryResponse(
            event_id=str(entry.event_id),
            case_id=entry.case_id,
            event_time=entry.event_time,
            event_text=entry.event_text,
            event_type=entry.event_type,
            team=entry.team,
            action_detected=entry.action_detected,
            observation_detected=entry.observation_detected,
            sequence_order=entry.sequence_order,
        )
        for entry in timeline_entries
    ]


@router.get(
    "/{case_id}/actions",
    response_model=list[TroubleshootingActionResponse],
    status_code=status.HTTP_200_OK,
)
def get_incident_actions(
    case_id: str,
    db: Session = Depends(db_session_dependency),
) -> list[TroubleshootingActionResponse]:
    """
    Recupera las acciones de troubleshooting asociadas a un incidente.
    """
    incident_repository = IncidentCaseRepository(db)
    incident_case = incident_repository.get_by_case_id(case_id)

    if incident_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with case_id '{case_id}' was not found.",
        )

    action_repository = TroubleshootingActionRepository(db)
    actions = action_repository.list_by_case_id(case_id)

    return [
        TroubleshootingActionResponse(
            action_id=str(action.action_id),
            case_id=action.case_id,
            action_text=action.action_text,
            action_type=action.action_type,
            action_role=action.action_role,
            target_component=action.target_component,
            outcome=action.outcome,
            was_effective=action.was_effective,
            sequence_order=action.sequence_order,
        )
        for action in actions
    ]


@router.get(
    "",
    response_model=list[IncidentCaseSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def list_incidents_by_status(
    status_filter: IncidentStatus = Query(..., alias="status"),
    db: Session = Depends(db_session_dependency),
) -> list[IncidentCaseSummaryResponse]:
    """
    Lista incidentes por estado.
    """
    repository = IncidentCaseRepository(db)
    incident_cases = repository.list_by_status(status_filter.value)

    return [
        IncidentCaseSummaryResponse(
            case_id=incident.case_id,
            source_type=incident.source_type,
            header=incident.header,
            incident_status=IncidentStatus(incident.status),
            pending_rca=incident.pending_rca,
        )
        for incident in incident_cases
    ]