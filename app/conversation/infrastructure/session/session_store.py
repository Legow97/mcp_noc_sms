from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.conversation.contracts.requests import ConversationMode
from app.conversation.contracts.session_models import (
    ConversationSessionState,
)


class SessionStoreBackendError(RuntimeError):
    """Error controlado para fallos del backend de sesión."""


class SessionStore(ABC):
    """
    Abstracción base para persistencia de estado conversacional.
    """

    @abstractmethod
    def get_session(
        self,
        session_id: str,
        mode: ConversationMode,
    ) -> ConversationSessionState:
        raise NotImplementedError

    @abstractmethod
    def save_session(
        self,
        session_state: ConversationSessionState,
    ) -> ConversationSessionState:
        raise NotImplementedError

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def touch_session(self, session_id: str) -> None:
        raise NotImplementedError


class InMemorySessionStore(SessionStore):
    """
    Implementación en memoria para desarrollo y pruebas unitarias.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ConversationSessionState] = {}

    def get_session(
        self,
        session_id: str,
        mode: ConversationMode,
    ) -> ConversationSessionState:
        session = self._sessions.get(session_id)

        if session is None:
            session = ConversationSessionState(
                session_id=session_id,
                current_mode=mode,
            )
            self._sessions[session_id] = session
            return session.model_copy(deep=True)

        if session.current_mode != mode:
            session.current_mode = mode
            session.updated_at = datetime.now(timezone.utc)

        return session.model_copy(deep=True)

    def save_session(
        self,
        session_state: ConversationSessionState,
    ) -> ConversationSessionState:
        session_state.updated_at = datetime.now(timezone.utc)
        self._sessions[session_state.session_id] = session_state.model_copy(deep=True)
        return session_state.model_copy(deep=True)

    def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def touch_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        session.updated_at = datetime.now(timezone.utc)


class ResilientSessionStore(SessionStore):
    """
    Store con degradación controlada a memoria local si el backend primario falla.
    """

    def __init__(
        self,
        primary: SessionStore,
        fallback: SessionStore,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    def get_session(
        self,
        session_id: str,
        mode: ConversationMode,
    ) -> ConversationSessionState:
        try:
            session_state = self._primary.get_session(session_id, mode)
        except SessionStoreBackendError as exc:
            print("[WARN] [CONVERSATION SESSION STORE] primary get failed:", str(exc))
            return self._fallback.get_session(session_id, mode)

        self._fallback.save_session(session_state)
        return session_state

    def save_session(
        self,
        session_state: ConversationSessionState,
    ) -> ConversationSessionState:
        fallback_state = self._fallback.save_session(session_state)

        try:
            return self._primary.save_session(session_state)
        except SessionStoreBackendError as exc:
            print("[WARN] [CONVERSATION SESSION STORE] primary save failed:", str(exc))
            return fallback_state

    def delete_session(self, session_id: str) -> None:
        self._fallback.delete_session(session_id)

        try:
            self._primary.delete_session(session_id)
        except SessionStoreBackendError as exc:
            print("[WARN] [CONVERSATION SESSION STORE] primary delete failed:", str(exc))

    def touch_session(self, session_id: str) -> None:
        self._fallback.touch_session(session_id)

        try:
            self._primary.touch_session(session_id)
        except SessionStoreBackendError as exc:
            print("[WARN] [CONVERSATION SESSION STORE] primary touch failed:", str(exc))
