from sqlalchemy.orm import Session

from app.db.models import TroubleshootingActionModel


class TroubleshootingActionRepository:
    """
    Repositorio de acceso a datos para TroubleshootingActionModel.

    Encapsula las operaciones de persistencia de acciones de troubleshooting
    derivadas de la bitácora del incidente.
    """

    def __init__(self, db_session: Session) -> None:
        self._db = db_session

    def bulk_create(
        self,
        actions: list[TroubleshootingActionModel],
    ) -> list[TroubleshootingActionModel]:
        """
        Persiste múltiples acciones de troubleshooting en una sola operación.
        """
        self._db.add_all(actions)
        self._db.commit()

        for action in actions:
            self._db.refresh(action)

        return actions

    def list_by_case_id(
        self,
        case_id: str,
    ) -> list[TroubleshootingActionModel]:
        """
        Recupera todas las acciones de troubleshooting de un incidente
        ordenadas por sequence_order ascendente.
        """
        return (
            self._db.query(TroubleshootingActionModel)
            .filter(TroubleshootingActionModel.case_id == case_id)
            .order_by(TroubleshootingActionModel.sequence_order.asc())
            .all()
        )