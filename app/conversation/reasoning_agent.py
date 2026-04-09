"""Legacy compatibility wrapper for the reasoning agent."""

from app.conversation.application.reasoning.reasoning_agent import (
    ReasoningAgent,
    ReasoningAgentLLMOutput,
)

__all__ = [
    "ReasoningAgent",
    "ReasoningAgentLLMOutput",
]
