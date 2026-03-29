from datetime import timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.api.schemas.incident_requests import IngestSmsRequest
from app.db.models import IncidentCaseModel
from app.db.repositories.incident_case_repository import IncidentCaseRepository
from app.parsers.sms_bitacora_parser import SmsBitacoraParser


class IncidentIngestionService:
    """
    Servicio de aplicación para la ingesta inicial de SMS bitácora.

    En esta etapa del POC:
    - delega el parsing a un componente especializado
    - genera un case_id temporal
    - crea un IncidentCaseModel mínimo
    - lo persiste en PostgreSQL

    Más adelante este servicio será el punto natural de orquestación para:
    - parser real del SMS
    - normalización
    - generación de timeline
    - generación de troubleshooting actions
    """

    def __init__(self, db_session: Session) -> None:
        self._db = db_session
        self._incident_case_repository = IncidentCaseRepository(db_session)
        self._sms_bitacora_parser = SmsBitacoraParser()

    def ingest_sms(self, payload: IngestSmsRequest) -> IncidentCaseModel:
        """
        Ingresa un SMS bitácora y persiste un incidente mínimo.
        """
        parsed_sms = self._sms_bitacora_parser.parse(payload)
        generated_case_id = f"INC-STUB-{uuid4().hex[:12].upper()}"

        incident_case = IncidentCaseModel(
            case_id=generated_case_id,
            source_type=parsed_sms.source_type,
            header=parsed_sms.header,
            failure_text=parsed_sms.failure_text,
            impact_text=parsed_sms.impact_text,
            start_time=parsed_sms.start_time,
            solution_time=payload.received_at.replace(tzinfo=timezone.utc),
            status=parsed_sms.incident_status,
            pending_rca=parsed_sms.pending_rca,
            raw_sms=parsed_sms.raw_sms,
            probable_cause_text=None,
            resolution_summary=None,
            component_types=[],
            components_affected=[],
            services_affected=[],
            symptoms=[],
            teams_involved=[],
            tickets=[],
            tags=[],
            parser_output_json=parsed_sms.parser_output_json,
            enrichment_json=parsed_sms.enrichment_json,
        )

        try:
            persisted_case = self._incident_case_repository.add(incident_case)
            self._db.commit()
            return persisted_case
        except Exception:
            self._db.rollback()
            raise
