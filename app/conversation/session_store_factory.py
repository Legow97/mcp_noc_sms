"""Legacy compatibility wrapper for session store construction."""

from app.conversation.infrastructure.session.session_store_factory import (
    build_conversation_session_store,
)

__all__ = ["build_conversation_session_store"]
