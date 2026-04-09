"""Legacy compatibility wrapper for LLM gateway contracts."""

from app.conversation.infrastructure.llm.model_gateway import (
    ConversationModelGateway,
    ConversationModelInvocation,
    ConversationModelRawResponse,
)

__all__ = [
    "ConversationModelGateway",
    "ConversationModelInvocation",
    "ConversationModelRawResponse",
]
