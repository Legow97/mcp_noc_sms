from pydantic import BaseModel


class RetrievalSearchMatchResponse(BaseModel):
    case_id: str
    document_version: str
    document_text: str
    distance: float


class RetrievalSearchResponse(BaseModel):
    query_text: str
    document_version: str
    limit: int
    distance_threshold: float | None = None
    query_embedding_dimensions: int
    results: list[RetrievalSearchMatchResponse]
