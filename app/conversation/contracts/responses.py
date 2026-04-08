from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.conversation.contracts.requests import ConversationMode


class ConversationResponseStatus(str, Enum):
    """
    Estado operativo del turno conversacional.
    """

    COMPLETED = "completed"
    NEEDS_CLARIFICATION = "needs_clarification"


class ConversationIntent(str, Enum):
    """
    Intención conversacional detectada para el turno.
    """

    GREETING = "greeting"
    GENERAL = "general"
    HISTORICAL_RETRIEVAL_REQUEST = "historical_retrieval_request"
    TIMELINE_REQUEST = "timeline_request"
    TROUBLESHOOTING_REQUEST = "troubleshooting_request"
    NEEDS_CLARIFICATION = "needs_clarification"


class ConversationAgentResult(BaseModel):
    """
    Resultado interno producido por el agente de razonamiento.
    """

    response_text: str = Field(..., min_length=1)
    intent: ConversationIntent = Field(default=ConversationIntent.GENERAL)
    status: ConversationResponseStatus = Field(
        default=ConversationResponseStatus.COMPLETED
    )
    missing_information: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    active_incident_ids: list[str] = Field(default_factory=list)
    active_entities: list[str] = Field(default_factory=list)
    active_issue_summary: str | None = None
    latest_historical_matches: list[str] = Field(default_factory=list)
    troubleshooting_context: dict[str, Any] = Field(default_factory=dict)
    latest_guidance_summary: str | None = None


class ConversationResponse(BaseModel):
    """
    Respuesta pública mínima del flujo conversacional.
    """

    session_id: str = Field(..., min_length=1)
    mode: ConversationMode
    status: ConversationResponseStatus
    response_text: str = Field(..., min_length=1)
    context_summary: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    active_issue_summary: str | None = None
