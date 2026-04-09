"""Legacy compatibility wrapper for external research service types."""

from app.conversation.infrastructure.research.external_research import (
    ExternalResearchResult,
    ExternalResearchService,
)

__all__ = [
    "ExternalResearchResult",
    "ExternalResearchService",
]
