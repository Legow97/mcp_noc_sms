from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import db_session_dependency
from app.api.schemas.retrieval_requests import RetrievalSearchRequest
from app.api.schemas.retrieval_responses import (
    RetrievalSearchMatchResponse,
    RetrievalSearchResponse,
)
from app.services.retrieval.incident_semantic_search_service import (
    IncidentSemanticSearchService,
)


router = APIRouter(
    prefix="/api/v1/retrieval",
    tags=["retrieval"],
)


@router.post(
    "/search",
    response_model=RetrievalSearchResponse,
    status_code=status.HTTP_200_OK,
)
def search_retrieval_documents(
    payload: RetrievalSearchRequest,
    db: Session = Depends(db_session_dependency),
) -> RetrievalSearchResponse:
    """
    Endpoint técnico para consultar semánticamente incidentes ya indexados.
    """
    service = IncidentSemanticSearchService(db)

    try:
        result = service.search(
            payload.query_text,
            limit=payload.limit,
            distance_threshold=payload.distance_threshold,
            document_version=payload.document_version,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        print("[ERROR] [RETRIEVAL ENDPOINT] semantic search failed:", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected error during semantic retrieval search.",
        ) from exc

    return RetrievalSearchResponse(
        query_text=result.query_text,
        document_version=result.document_version,
        limit=result.limit,
        distance_threshold=result.distance_threshold,
        query_embedding_dimensions=result.query_embedding_dimensions,
        results=[
            RetrievalSearchMatchResponse(
                case_id=item.case_id,
                document_version=item.document_version,
                document_text=item.document_text,
                distance=item.distance,
            )
            for item in result.results
        ],
    )
