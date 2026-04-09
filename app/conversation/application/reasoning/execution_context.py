from __future__ import annotations

from pydantic import BaseModel, Field

from app.conversation.contracts.requests import ConversationRequest
from app.conversation.contracts.session_models import (
    ConversationContext,
    ConversationSessionState,
)


class ConversationExecutionContext(BaseModel):
    """
    Contenedor liviano para orquestar capacidades intercambiables sin
    acoplarlas al transporte ni a la infraestructura concreta.
    """

    request: ConversationRequest
    session_state: ConversationSessionState
    context: ConversationContext
    enabled_skills: list[str] = Field(default_factory=list)
    enabled_tools: list[str] = Field(default_factory=list)
