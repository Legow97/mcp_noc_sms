from pydantic import BaseModel, Field


class ApiMessage(BaseModel):
    """Schema simple para mensajes de respuesta genéricos."""

    message: str = Field(..., min_length=1)