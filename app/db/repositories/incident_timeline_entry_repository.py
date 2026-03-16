from sqlalchemy.orm import Session

from app.db.models import IncidentTimelineEntryModel


class IncidentTimelineEntryRepository:
    """
    Repositorio de acceso a datos para IncidentTimelineEntryModel.

    Encapsula las operaciones de persistencia de la cronología/bitácora
    temporal asociada a un incidente.
    """

    def __init__(self, db_session: Session) -> None:
        self._db = db_session

    def bulk_create(
        self,
        entries: list[IncidentTimelineEntryModel],
    ) -> list[IncidentTimelineEntryModel]:
        """
        Persiste múltiples entradas de timeline en una sola operación.
        """
        self._db.add_all(entries)
        self._db.commit()

        for entry in entries:
            self._db.refresh(entry)

        return entries

    def list_by_case_id(
        self,
        case_id: str,
    ) -> list[IncidentTimelineEntryModel]:
        """
        Recupera todas las entradas de timeline de un incidente
        ordenadas por sequence_order ascendente.
        """
        return (
            self._db.query(IncidentTimelineEntryModel)
            .filter(IncidentTimelineEntryModel.case_id == case_id)
            .order_by(IncidentTimelineEntryModel.sequence_order.asc())
            .all()
        )