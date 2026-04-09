from __future__ import annotations

from app.core.config import settings
from app.conversation.infrastructure.llm.model_gateway import ConversationModelGateway
from app.conversation.infrastructure.llm.providers.gemini_model_gateway import (
    ConversationGeminiModelGateway,
)
from app.conversation.infrastructure.llm.providers.openai_compatible_model_gateway import (
    ConversationOpenAICompatibleModelGateway,
)


def build_conversation_model_gateway() -> ConversationModelGateway:
    """
    Construye el gateway LLM conversacional desde settings.
    """

    provider = settings.conversation_reasoning.provider.strip().lower()

    if provider == "gemini":
        return ConversationGeminiModelGateway()

    if provider in {"openai_compatible", "openai-compatible"}:
        return ConversationOpenAICompatibleModelGateway()

    raise ValueError(f"Proveedor conversacional no soportado: {provider}")
