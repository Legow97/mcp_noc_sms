from app.agentic.prompts.prompt_settings import PromptSettings
from app.agentic.prompts.shared_prompts import build_rulebook_context


def build_fallback_extractor_system_prompt(settings: PromptSettings) -> str:
    """
    Prompt del extractor secundario/fallback.
    """
    shared_context = build_rulebook_context(
        subsystem_role="fallback_extractor",
        rulebook_path=settings.fallback_rulebook_path,
        rulebook_version=settings.fallback_rulebook_version,
        settings=settings,
    )

    return f"""
{shared_context}

Rol:
Eres el extractor secundario (fallback).

Objetivo:
Reconstruir la extracción canónica corrigiendo los errores detectados
por el juez en una propuesta previa.

Reglas clave:
- Usa el feedback del juez como guía obligatoria.
- No copies ciegamente la extracción previa si fue rechazada.
- No inventes información faltante.
- Corrige especialmente:
  - campos inconsistentes
  - causas no respaldadas
  - remediaciones mal inferidas
  - timeline/actions mal clasificados
  - omisiones relevantes

Salida esperada:
Debes producir una nueva propuesta apta para convertirse
en un CanonicalExtractionResult.
""".strip()


def build_fallback_extractor_user_prompt(
    raw_sms: str,
    previous_extraction_text: str,
    judge_feedback_text: str,
) -> str:
    """
    Prompt de usuario para el extractor fallback.
    """
    return f"""
Reconstruye la extracción canónica usando el feedback del juez.

Documento fuente:
---
{raw_sms}
---

Extracción previa rechazada:
---
{previous_extraction_text}
---

Feedback del juez:
---
{judge_feedback_text}
---
""".strip()