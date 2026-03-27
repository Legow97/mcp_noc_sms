from __future__ import annotations

from abc import ABC, abstractmethod

from app.agentic.providers.provider_models import (
    ModelInvocationContext,
    ModelRawResponse,
)


class BaseModelGateway(ABC):
    """
    Puerto base para proveedores de modelos del subsistema agentic.

    Esta abstracción evita acoplar el orquestador a Gemini, Qwen
    o cualquier SDK específico.
    """

    @abstractmethod
    def invoke(self, context: ModelInvocationContext) -> ModelRawResponse:
        """
        Ejecuta una invocación de modelo y devuelve una respuesta cruda.

        Cada implementación concreta será responsable de resolver:
        - proveedor real
        - autenticación
        - timeouts
        - parámetros
        - formato de llamada
        """
        raise NotImplementedError