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

    def add_many(
        self,
        actions: list[TroubleshootingActionModel],
    ) -> list[TroubleshootingActionModel]:
        """
        Agrega múltiples acciones de troubleshooting a la sesión activa sin cerrar la transacción.
        """
        print(
            "[REPOSITORY] Agregando troubleshooting actions:",
            {
                "count": len(actions),
                "items": [
                    {
                        "case_id": action.case_id,
                        "sequence_order": action.sequence_order,
                        "action_type": action.action_type,
                        "action_role": action.action_role,
                        "target_component": action.target_component,
                        "action_text": action.action_text[:160],
                    }
                    for action in actions
                ],
            },
        )
        self._db.add_all(actions)
        self._db.flush()
        print(
            "[REPOSITORY] flush() exitoso para troubleshooting actions:",
            {"count": len(actions)},
        )

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
