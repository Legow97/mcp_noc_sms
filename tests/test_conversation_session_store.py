import unittest

from app.conversation.contracts.requests import ConversationMode
from app.conversation.contracts.session_models import ConversationSessionState
from app.conversation.redis_session_store import RedisSessionStore
from app.conversation.session_store import (
    InMemorySessionStore,
    ResilientSessionStore,
    SessionStore,
    SessionStoreBackendError,
)


class FakeRedisClient:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}
        self._ttl: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self._data[key] = value
        if ex is not None:
            self._ttl[key] = ex
        return True

    def delete(self, key: str) -> int:
        self._data.pop(key, None)
        self._ttl.pop(key, None)
        return 1

    def expire(self, key: str, ttl_seconds: int) -> bool:
        if key in self._data:
            self._ttl[key] = ttl_seconds
        return True


class FailingSessionStore(SessionStore):
    def get_session(self, session_id: str, mode: ConversationMode) -> ConversationSessionState:
        raise SessionStoreBackendError("backend unavailable")

    def save_session(
        self,
        session_state: ConversationSessionState,
    ) -> ConversationSessionState:
        raise SessionStoreBackendError("backend unavailable")

    def delete_session(self, session_id: str) -> None:
        raise SessionStoreBackendError("backend unavailable")

    def touch_session(self, session_id: str) -> None:
        raise SessionStoreBackendError("backend unavailable")


class ConversationSessionStoreTests(unittest.TestCase):
    def test_in_memory_store_creates_missing_session(self) -> None:
        store = InMemorySessionStore()

        session = store.get_session("conv-001", ConversationMode.GENERAL)

        self.assertEqual(session.session_id, "conv-001")
        self.assertEqual(session.current_mode, ConversationMode.GENERAL)
        self.assertEqual(session.history, [])

    def test_redis_store_persists_and_reads_session(self) -> None:
        store = RedisSessionStore(
            host="localhost",
            port=6379,
            db=0,
            password=None,
            session_ttl_seconds=120,
            key_prefix="conversation:session",
            client=FakeRedisClient(),
        )
        session = ConversationSessionState(
            session_id="conv-redis-1",
            current_mode=ConversationMode.TROUBLESHOOTING,
            last_user_message="detalle del incidente",
        )

        store.save_session(session)
        loaded = store.get_session("conv-redis-1", ConversationMode.TROUBLESHOOTING)

        self.assertEqual(loaded.session_id, "conv-redis-1")
        self.assertEqual(loaded.current_mode, ConversationMode.TROUBLESHOOTING)
        self.assertEqual(loaded.last_user_message, "detalle del incidente")

    def test_resilient_store_falls_back_when_primary_backend_fails(self) -> None:
        fallback = InMemorySessionStore()
        store = ResilientSessionStore(
            primary=FailingSessionStore(),
            fallback=fallback,
        )

        session = store.get_session("conv-fallback", ConversationMode.GENERAL)
        session.last_user_message = "mensaje en fallback"
        saved = store.save_session(session)

        loaded = fallback.get_session("conv-fallback", ConversationMode.GENERAL)
        self.assertEqual(saved.last_user_message, "mensaje en fallback")
        self.assertEqual(loaded.last_user_message, "mensaje en fallback")


if __name__ == "__main__":
    unittest.main()
