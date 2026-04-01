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
from app.agentic.orchestrator.factory import build_sms_orchestrator
from app.core.ingestion_trace import (
    bind_case_id,
    finalize_ingestion_summary,
    log_ingestion_event,
    start_ingestion_trace,
)
from app.db.repositories.incident_case_repository import IncidentCaseRepository
from app.db.repositories.incident_timeline_entry_repository import (
    IncidentTimelineEntryRepository,
)
from app.db.repositories.troubleshooting_action_repository import (
    TroubleshootingActionRepository,
)
from app.domain.enums import IngestionStatus, IncidentStatus
from app.services.agentic_incident_ingestion_service import (
    AgenticIncidentIngestionService,
)

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
    Endpoint de ingesta de SMS usando el subsistema agentic
    y persistencia canónica.
    """
    print(
        "[INGEST ENDPOINT] Payload recibido:",
        payload.model_dump(mode="json"),
    )
    start_ingestion_trace(
        source_channel=payload.source_channel,
        raw_text=payload.raw_text,
    )
    log_ingestion_event(
        layer="api",
        event="payload_received",
        payload={
            "source_channel": payload.source_channel,
            "received_at": payload.received_at.isoformat(),
        },
    )

    orchestrator = build_sms_orchestrator()
    ingestion_service = AgenticIncidentIngestionService(
        db_session=db,
        orchestrator=orchestrator,
    )

    try:
        result = ingestion_service.ingest_sms(payload)
    except ValueError as exc:
        log_ingestion_event(
            layer="api",
            event="request_failed",
            status="error",
            error=str(exc),
        )
        finalize_ingestion_summary(
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            persisted_ok=False,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        print("[ERROR] [INGEST ENDPOINT] ValueError:", str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        log_ingestion_event(
            layer="api",
            event="request_failed",
            status="error",
            error=str(exc),
        )
        finalize_ingestion_summary(
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            persisted_ok=False,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        print("[ERROR] [INGEST ENDPOINT] Unexpected exception:", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error during agentic incident ingestion.",
        )

    bind_case_id(result.case_id)
    log_ingestion_event(
        layer="api",
        event="request_completed",
        payload={
            "case_id": result.case_id,
            "judge_decision": result.judge_decision,
            "timeline_entries_saved": result.timeline_entries_saved,
            "troubleshooting_actions_saved": result.troubleshooting_actions_saved,
        },
    )
    finalize_ingestion_summary(
        http_status=status.HTTP_202_ACCEPTED,
        persisted_ok=True,
    )

    return IngestSmsResponse(
        ingestion_status=IngestionStatus.ACCEPTED,
        incident_status=IncidentStatus(result.incident_status),
        case_id=result.case_id,
        parsed_ok=result.parsed_ok,
        indexed=result.indexed,
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
        start_time=incident_case.start_time,
        incident_status=IncidentStatus(incident_case.status),
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
            start_time=incident.start_time,
            incident_status=IncidentStatus(incident.status),
        )
        for incident in incident_cases
    ]
