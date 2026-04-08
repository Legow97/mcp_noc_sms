from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ConversationMode(str, Enum):
    """
    Modos base del flujo conversacional.

    Mantiene explícito el objetivo del turno sin acoplar todavía
    implementaciones concretas para cada modo.
    """

    GENERAL = "general"
    CLARIFICATION = "clarification"
    TROUBLESHOOTING = "troubleshooting"
    HISTORICAL_RETRIEVAL = "historical_retrieval"


class ConversationRequest(BaseModel):
    """
    Contrato de entrada para el subsistema conversacional.
    """

    message: str = Field(..., min_length=1)
    session_id: str | None = Field(default=None, min_length=1)
    mode: ConversationMode = Field(default=ConversationMode.GENERAL)
    metadata: dict[str, Any] = Field(default_factory=dict)
    requested_capabilities: list[str] = Field(default_factory=list)
