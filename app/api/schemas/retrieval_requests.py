from pydantic import BaseModel, Field


class RetrievalSearchRequest(BaseModel):
    """
    Request técnico para búsqueda semántica sobre incidentes indexados.
    """

    query_text: str = Field(..., min_length=1)
    limit: int = Field(default=5, ge=1)
    distance_threshold: float | None = Field(default=None, ge=0)
    document_version: str | None = Field(default=None, min_length=1)
