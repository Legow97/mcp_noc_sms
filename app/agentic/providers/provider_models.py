from __future__ import annotations

from pydantic import BaseModel, Field


class ModelInvocationContext(BaseModel):
    """
    Contexto estándar de invocación para cualquier modelo del subsistema.

    No contiene ORM ni detalles HTTP. Solo el contenido necesario para
    invocar un proveedor de modelos de manera desacoplada.

    `extra_config` permite pasar opciones específicas del proveedor
    sin romper el contrato base. Ejemplos:
    - structured output
    - response schema
    - mime type
    - parámetros experimentales
    """

    system_instruction: str = Field(..., min_length=1)
    user_input: str = Field(..., min_length=1)
    task_name: str = Field(..., min_length=1)
    model_name: str | None = None
    temperature: float | None = None
    extra_config: dict | None = None


class ModelRawResponse(BaseModel):
    """
    Respuesta cruda del proveedor/modelo.

    Aún no representa extracción canónica. Solo encapsula la salida textual
    y metadatos básicos del proveedor.
    """

    model_name: str = Field(..., min_length=1)
    output_text: str = Field(..., min_length=1)
    provider_name: str = Field(..., min_length=1)