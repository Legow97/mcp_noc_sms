from typing import Any

from sqlalchemy.orm import Session

from app.core.ingestion_trace import bind_case_id, log_ingestion_event
from app.db.models import IncidentCaseModel


class IncidentCaseRepository:
    """
    Repositorio de acceso a datos para IncidentCaseModel.

    Encapsula las operaciones de persistencia del agregado principal
    de incidentes y evita dispersar lógica de base de datos en rutas
    o servicios.
    """

    def __init__(self, db_session: Session) -> None:
        self._db = db_session

    def add(self, incident_case: IncidentCaseModel) -> IncidentCaseModel:
        """
        Agrega un nuevo incidente a la sesión activa sin cerrar la transacción.
        """
        bind_case_id(incident_case.case_id)
        log_ingestion_event(
            layer="repository",
            event="incident_case_add_started",
            payload={
                "case_id": incident_case.case_id,
                "status": incident_case.status,
                "source_type": incident_case.source_type,
            },
        )
        print(
            "[REPOSITORY] Agregando IncidentCaseModel:",
            {
                "case_id": incident_case.case_id,
                "source_type": incident_case.source_type,
                "status": incident_case.status,
                "header": incident_case.header,
            },
        )
        self._db.add(incident_case)
        self._db.flush()
        log_ingestion_event(
            layer="repository",
            event="incident_case_flush_completed",
            payload={"case_id": incident_case.case_id},
        )
        print(
            "[REPOSITORY] flush() exitoso para IncidentCaseModel:",
            {"case_id": incident_case.case_id},
        )
        self._db.refresh(incident_case)
        log_ingestion_event(
            layer="repository",
            event="incident_case_refresh_completed",
            payload={"case_id": incident_case.case_id},
        )
        return incident_case

    def get_by_case_id(self, case_id: str) -> IncidentCaseModel | None:
        """
        Recupera un incidente por su case_id.
        """
        return (
            self._db.query(IncidentCaseModel)
            .filter(IncidentCaseModel.case_id == case_id)
            .first()
        )

    def list_by_status(self, status: str) -> list[IncidentCaseModel]:
        """
        Lista incidentes por estado.
        """
        return (
            self._db.query(IncidentCaseModel)
            .filter(IncidentCaseModel.status == status)
            .order_by(IncidentCaseModel.created_at.desc())
            .all()
        )

    def count_all(self) -> int:
        """
        Cuenta todos los incidentes persistidos.
        """
        return self._db.query(IncidentCaseModel).count()

    def list_case_ids(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[str]:
        """
        Lista case_id persistidos ordenados por fecha de creación ascendente.
        """
        query = self._db.query(IncidentCaseModel.case_id).order_by(
            IncidentCaseModel.created_at.asc(),
            IncidentCaseModel.case_id.asc(),
        )

        if offset > 0:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return [row[0] for row in query.all()]

    def update_fields(
        self,
        case_id: str,
        updates: dict[str, Any],
    ) -> IncidentCaseModel | None:
        """
        Actualiza campos simples del incidente y devuelve la entidad actualizada.

        Este método está pensado para cambios controlados. Más adelante,
        si el dominio crece, puede refinarse para updates específicos o
        combinarse con una capa de servicio de aplicación.
        """
        incident_case = self.get_by_case_id(case_id)
        if incident_case is None:
            return None

        for field_name, field_value in updates.items():
            if hasattr(incident_case, field_name):
                setattr(incident_case, field_name, field_value)

        self._db.flush()
        self._db.refresh(incident_case)
        return incident_case
