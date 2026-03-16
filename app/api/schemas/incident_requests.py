from datetime import datetime

from pydantic import BaseModel, Field


class IngestSmsRequest(BaseModel):
    """
    Request para la ingesta de un SMS de bitácora.

    En esta fase solo validamos que exista el texto base
    y algunos metadatos mínimos del canal de origen.
    """

    raw_text: str = Field(..., min_length=20)
    source_channel: str = Field(..., min_length=2, max_length=64)
    received_at: datetime