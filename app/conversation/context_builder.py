from __future__ import annotations

from app.conversation.contracts.historical_context import ConversationHistoricalContext
from app.conversation.contracts.requests import ConversationRequest
from app.conversation.contracts.session_models import (
    ConversationContext,
    ConversationSessionState,
)
from app.conversation.historical_context_service import HistoricalContextService


class ContextBuilder:
    """
    Construye contexto conversacional con estado de sesión y evidencia histórica.
    """

    def __init__(
        self,
        historical_context_service: HistoricalContextService | None = None,
    ) -> None:
        self._historical_context_service = historical_context_service

    def build(
        self,
        request: ConversationRequest,
        session_state: ConversationSessionState,
    ) -> ConversationContext:
        summary: list[str] = []
        historical_context = (
            self._historical_context_service.build_for_request(
                request,
                session_state=session_state,
            )
            if self._historical_context_service is not None
            else ConversationHistoricalContext()
        )

        if session_state.history:
            summary.append(
                f"session_history_messages={len(session_state.history)}"
            )
        else:
            summary.append("session_history_messages=0")

        if session_state.awaiting_more_info:
            summary.append("awaiting_more_info=true")

        if session_state.active_issue_summary:
            summary.append(
                "active_issue_summary=" + session_state.active_issue_summary
            )

        if session_state.active_incident_ids:
            summary.append(
                "active_incident_ids=" + ",".join(session_state.active_incident_ids)
            )

        if session_state.active_entities:
            summary.append(
                "active_entities=" + ",".join(session_state.active_entities)
            )

        if session_state.missing_information:
            summary.append(
                "missing_information=" + ",".join(session_state.missing_information)
            )

        if session_state.latest_historical_matches:
            summary.append(
                "latest_historical_matches="
                + ",".join(session_state.latest_historical_matches[:5])
            )

        if request.requested_capabilities:
            summary.append(
                "requested_capabilities="
                + ",".join(request.requested_capabilities)
            )

        if historical_context.primary_incident is not None:
            summary.append(
                "historical_exact_lookup="
                + historical_context.primary_incident.case_id
            )
        if historical_context.timeline_entries:
            summary.append(
                f"timeline_entries={len(historical_context.timeline_entries)}"
            )
        if historical_context.semantic_matches:
            summary.append(
                f"semantic_matches={len(historical_context.semantic_matches)}"
            )
            if historical_context.semantic_query_source:
                summary.append(
                    "semantic_query_source="
                    + historical_context.semantic_query_source
                )
            summary.extend(
                "semantic_match="
                + f"{match.case_id}:distance={match.distance:.4f}"
                for match in historical_context.semantic_matches[:5]
            )
        if historical_context.retrieval_notes:
            summary.extend(
                "historical_note=" + note
                for note in historical_context.retrieval_notes
            )
        if historical_context.errors:
            summary.extend(
                "historical_error=" + error
                for error in historical_context.errors
            )

        return ConversationContext(
            session_id=session_state.session_id,
            mode=request.mode,
            latest_user_message=request.message,
            history=list(session_state.history),
            summary=summary,
            historical_context=historical_context,
        )
