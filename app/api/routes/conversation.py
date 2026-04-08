from fastapi import APIRouter, HTTPException, status
from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.dependencies import db_session_dependency
from app.conversation.context_builder import ContextBuilder
from app.conversation.orchestrator import ConversationOrchestrator
from app.conversation.contracts.requests import ConversationRequest
from app.conversation.contracts.responses import ConversationResponse
from app.conversation.historical_context_service import HistoricalContextService
from app.conversation.session_store_factory import build_conversation_session_store


router = APIRouter(
    prefix="/api/v1/conversation",
    tags=["conversation"],
)

_conversation_session_store = build_conversation_session_store()


def build_conversation_orchestrator(
    db: Session | None = None,
) -> ConversationOrchestrator:
    """
    Punto de construcción local para el flujo conversacional.
    """

    context_builder = (
        ContextBuilder(
            historical_context_service=HistoricalContextService(db),
        )
        if db is not None
        else ContextBuilder()
    )

    return ConversationOrchestrator(
        session_store=_conversation_session_store,
        context_builder=context_builder,
    )


@router.post(
    "/message",
    response_model=ConversationResponse,
    status_code=status.HTTP_200_OK,
)
def process_conversation_message(
    payload: ConversationRequest,
    db: Session = Depends(db_session_dependency),
) -> ConversationResponse:
    """
    Endpoint base para el nuevo workflow conversacional.
    """

    orchestrator = build_conversation_orchestrator(db)

    try:
        return orchestrator.handle(payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        print("[ERROR] [CONVERSATION ENDPOINT] conversation flow failed:", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error during conversation processing.",
        ) from exc
