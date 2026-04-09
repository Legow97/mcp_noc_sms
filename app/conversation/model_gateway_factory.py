"""Legacy compatibility wrapper for the LLM gateway factory."""

from app.conversation.infrastructure.llm.model_gateway_factory import (
    build_conversation_model_gateway,
)

__all__ = ["build_conversation_model_gateway"]
