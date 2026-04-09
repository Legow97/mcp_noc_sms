from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.conversation.application.reasoning.execution_context import (
    ConversationExecutionContext,
)


class ToolExecutionStatus(str, Enum):
    COMPLETED = "completed"
    DISABLED = "disabled"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    FAILED = "failed"


class ToolResult(BaseModel):
    """Resultado estándar de una tool formal del subsistema conversacional."""

    tool_name: str = Field(..., min_length=1)
    status: ToolExecutionStatus = Field(default=ToolExecutionStatus.COMPLETED)
    summary: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class ConversationTool(ABC):
    """Contrato mínimo pero real para tools intercambiables del flujo conversacional."""

    name: str
    description: str = ""

    @abstractmethod
    def is_enabled(self, context: ConversationExecutionContext) -> bool:
        raise NotImplementedError

    @abstractmethod
    def execute(
        self,
        context: ConversationExecutionContext,
        arguments: dict[str, Any] | None = None,
    ) -> ToolResult:
        raise NotImplementedError
