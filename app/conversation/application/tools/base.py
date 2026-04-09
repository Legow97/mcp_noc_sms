from __future__ import annotations

from abc import ABC, abstractmethod

from app.conversation.application.reasoning.execution_context import (
    ConversationExecutionContext,
)


class ConversationTool(ABC):
    """Contrato mínimo para tools habilitables sin acoplarlas al orquestador."""

    name: str

    @abstractmethod
    def is_enabled(self, context: ConversationExecutionContext) -> bool:
        raise NotImplementedError
