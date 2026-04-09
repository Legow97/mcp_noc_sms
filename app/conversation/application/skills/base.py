from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.conversation.application.reasoning.execution_context import (
    ConversationExecutionContext,
)


class SkillExecutionStatus(str, Enum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    DISABLED = "disabled"
    FAILED = "failed"


class SkillResult(BaseModel):
    """Resultado estándar para skills intercambiables futuras."""

    skill_name: str = Field(..., min_length=1)
    status: SkillExecutionStatus = Field(default=SkillExecutionStatus.COMPLETED)
    summary: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class ConversationSkill(ABC):
    """Contrato mínimo para skills intercambiables del flujo conversacional."""

    name: str
    description: str = ""

    @abstractmethod
    def is_enabled(self, context: ConversationExecutionContext) -> bool:
        raise NotImplementedError

    @abstractmethod
    def execute(self, context: ConversationExecutionContext) -> SkillResult:
        raise NotImplementedError
