from app.agentic.prompts.prompt_settings import PromptSettings
from app.agentic.prompts.shared_prompts import build_rulebook_context


def build_primary_extractor_system_prompt(settings: PromptSettings) -> str:
    """
    Prompt del modelo principal extractor.
    """
    shared_context = build_rulebook_context(
        subsystem_role="primary_extractor",
        rulebook_path=settings.extraction_rulebook_path,
        rulebook_version=settings.extraction_rulebook_version,
        settings=settings,
    )

    return f"""
{shared_context}

Rol:
Eres el extractor principal.

Objetivo:
Convertir un SMS bitácora o documento operativo semi-estructurado
en una representación canónica consistente.

Reglas clave:
- Extrae solo lo respaldado por el documento.
- Si un campo no está claro, déjalo vacío o márcalo como faltante.
- No inventes causa raíz ni solución si no están explícitas.
- Distingue entre:
  - timeline
  - troubleshooting actions
  - observaciones
  - diagnósticos
  - remediaciones
- No toda línea cronológica debe convertirse en troubleshooting action.
- Las acciones deben capturar solo acciones operativas reales y útiles.

Salida esperada:
Debes producir contenido apto para convertirse en un CanonicalExtractionResult.
""".strip()


def build_primary_extractor_user_prompt(raw_sms: str) -> str:
    """
    Prompt de usuario para el extractor principal.
    """
    return f"""
Extrae el documento siguiente al esquema canónico del servicio.

SMS / Documento:
---
{raw_sms}
---
""".strip()