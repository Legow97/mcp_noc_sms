"""Legacy compatibility wrapper for the Redis-backed session store."""

from app.conversation.infrastructure.session.redis_session_store import RedisSessionStore

__all__ = ["RedisSessionStore"]
