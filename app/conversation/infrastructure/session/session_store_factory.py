from __future__ import annotations

from app.core.config import settings
from app.conversation.infrastructure.session.redis_session_store import (
    RedisSessionStore,
)
from app.conversation.infrastructure.session.session_store import (
    InMemorySessionStore,
    ResilientSessionStore,
)


def build_conversation_session_store() -> ResilientSessionStore | InMemorySessionStore:
    """
    Construye el store conversacional con degradación segura a memoria local.
    """

    fallback_store = InMemorySessionStore()
    redis_settings = settings.conversation_redis

    if not redis_settings.enabled:
        return fallback_store

    try:
        primary_store = RedisSessionStore(
            host=redis_settings.host,
            port=redis_settings.port,
            db=redis_settings.db,
            password=redis_settings.password or None,
            session_ttl_seconds=redis_settings.session_ttl_seconds,
            key_prefix=redis_settings.key_prefix,
        )
    except Exception as exc:
        print("[WARN] [CONVERSATION SESSION STORE] Redis disabled:", str(exc))
        return fallback_store

    return ResilientSessionStore(
        primary=primary_store,
        fallback=fallback_store,
    )
