from typing import Any

from sqlalchemy.orm import Session

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

    def create(self, incident_case: IncidentCaseModel) -> IncidentCaseModel:
        """
        Persiste un nuevo incidente.
        """
        self._db.add(incident_case)
        self._db.commit()
        self._db.refresh(incident_case)
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

        self._db.commit()
        self._db.refresh(incident_case)
        return incident_case