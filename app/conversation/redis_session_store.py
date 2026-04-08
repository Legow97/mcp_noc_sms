from __future__ import annotations

from typing import Any

from app.conversation.contracts.requests import ConversationMode
from app.conversation.contracts.session_models import ConversationSessionState
from app.conversation.session_store import SessionStore, SessionStoreBackendError


class RedisSessionStore(SessionStore):
    """
    Persistencia de sesión conversacional sobre Redis usando JSON.
    """

    def __init__(
        self,
        host: str,
        port: int,
        db: int,
        password: str | None,
        session_ttl_seconds: int,
        key_prefix: str,
        client: Any | None = None,
    ) -> None:
        self._session_ttl_seconds = session_ttl_seconds
        self._key_prefix = key_prefix.strip(":")
        self._client = client or self._build_client(
            host=host,
            port=port,
            db=db,
            password=password,
        )

    @staticmethod
    def _build_client(
        host: str,
        port: int,
        db: int,
        password: str | None,
    ) -> Any:
        try:
            from redis import Redis
        except ImportError as exc:
            raise RuntimeError("redis package is not installed.") from exc

        return Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=True,
        )

    def get_session(
        self,
        session_id: str,
        mode: ConversationMode,
    ) -> ConversationSessionState:
        try:
            payload = self._client.get(self._build_key(session_id))
        except Exception as exc:
            raise SessionStoreBackendError(str(exc)) from exc

        if not payload:
            return ConversationSessionState(
                session_id=session_id,
                current_mode=mode,
            )

        try:
            session_state = ConversationSessionState.model_validate_json(payload)
        except Exception:
            return ConversationSessionState(
                session_id=session_id,
                current_mode=mode,
            )

        if session_state.current_mode != mode:
            session_state.current_mode = mode

        return session_state

    def save_session(self, session_state: ConversationSessionState) -> ConversationSessionState:
        try:
            self._client.set(
                self._build_key(session_state.session_id),
                session_state.model_dump_json(),
                ex=self._session_ttl_seconds,
            )
        except Exception as exc:
            raise SessionStoreBackendError(str(exc)) from exc

        return session_state.model_copy(deep=True)

    def delete_session(self, session_id: str) -> None:
        try:
            self._client.delete(self._build_key(session_id))
        except Exception as exc:
            raise SessionStoreBackendError(str(exc)) from exc

    def touch_session(self, session_id: str) -> None:
        try:
            self._client.expire(
                self._build_key(session_id),
                self._session_ttl_seconds,
            )
        except Exception as exc:
            raise SessionStoreBackendError(str(exc)) from exc

    def _build_key(self, session_id: str) -> str:
        return f"{self._key_prefix}:{session_id}"
