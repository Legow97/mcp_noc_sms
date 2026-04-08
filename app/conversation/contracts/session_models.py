from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.conversation.contracts.historical_context import ConversationHistoricalContext
from app.conversation.contracts.requests import ConversationMode


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ConversationMessage(BaseModel):
    """
    Mensaje persistible dentro del estado de sesión.
    """

    role: Literal["user", "assistant"] = Field(...)
    content: str = Field(..., min_length=1)
    created_at: datetime = Field(default_factory=_utc_now)


class ConversationSessionState(BaseModel):
    """
    Estado mínimo de una sesión conversacional.
    """

    session_id: str = Field(..., min_length=1)
    current_mode: ConversationMode = Field(default=ConversationMode.GENERAL)
    awaiting_more_info: bool = False
    last_user_message: str | None = None
    last_agent_response: str | None = None
    active_issue_summary: str | None = None
    active_incident_ids: list[str] = Field(default_factory=list)
    active_entities: list[str] = Field(default_factory=list)
    pending_clarifications: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    latest_historical_matches: list[str] = Field(default_factory=list)
    troubleshooting_context: dict[str, Any] = Field(default_factory=dict)
    latest_guidance_summary: str | None = None
    history: list[ConversationMessage] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)


class ConversationContext(BaseModel):
    """
    Contexto compuesto para el agente, derivado del request y la sesión.
    """

    session_id: str = Field(..., min_length=1)
    mode: ConversationMode
    latest_user_message: str = Field(..., min_length=1)
    history: list[ConversationMessage] = Field(default_factory=list)
    summary: list[str] = Field(default_factory=list)
    historical_context: ConversationHistoricalContext = Field(
        default_factory=ConversationHistoricalContext
    )
