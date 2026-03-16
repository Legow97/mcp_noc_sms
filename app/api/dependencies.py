from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.database import get_db


def db_session_dependency() -> Generator[Session, None, None]:
    """
    Dependencia explícita para exponer la sesión de base de datos
    a la capa API.
    """
    yield from get_db()