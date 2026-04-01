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

    def add_many(
        self,
        entries: list[IncidentTimelineEntryModel],
    ) -> list[IncidentTimelineEntryModel]:
        """
        Agrega múltiples entradas de timeline a la sesión activa sin cerrar la transacción.
        """
        print(
            "[REPOSITORY] Agregando timeline entries:",
            {
                "count": len(entries),
                "items": [
                    {
                        "case_id": entry.case_id,
                        "sequence_order": entry.sequence_order,
                        "event_time": entry.event_time,
                        "event_text": entry.event_text[:160],
                    }
                    for entry in entries
                ],
            },
        )
        self._db.add_all(entries)
        self._db.flush()
        print(
            "[REPOSITORY] flush() exitoso para timeline entries:",
            {"count": len(entries)},
        )

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
