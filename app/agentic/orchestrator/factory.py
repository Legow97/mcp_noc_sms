from app.agentic.orchestrator.canonical_extraction_orchestrator import (
    CanonicalExtractionOrchestrator,
)
from app.agentic.providers.gemini_model_gateway import GeminiModelGateway


def build_sms_orchestrator() -> CanonicalExtractionOrchestrator:
    """
    Construye el orquestador principal del subsistema agentic
    para extracción canónica de SMS.
    """
    model_gateway = GeminiModelGateway()
    return CanonicalExtractionOrchestrator(model_gateway=model_gateway)