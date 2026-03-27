from app.agentic.prompts.prompt_settings import PromptSettings
from app.agentic.prompts.shared_prompts import build_rulebook_context


def build_judge_system_prompt(settings: PromptSettings) -> str:
    """
    Prompt del modelo juez.

    Objetivo:
    - evaluar la extracción del modelo principal o fallback
    - detectar contradicciones, omisiones y alucinaciones
    - devolver feedback útil para corregir
    """
    shared_context = build_rulebook_context(
        subsystem_role="semantic_judge",
        rulebook_path=settings.judge_rulebook_path,
        rulebook_version=settings.judge_rulebook_version,
        settings=settings,
    )

    strictness_block = (
        "Modo estricto activado: rechaza salidas con inferencias débiles, "
        "causas no respaldadas o remediaciones inventadas."
        if settings.judge_strict_mode
        else "Modo estricto desactivado: permite más flexibilidad, pero mantén prudencia."
    )

    return f"""
{shared_context}

Rol:
Eres el juez del subsistema de extracción.

Objetivo:
Evaluar si una extracción canónica es fiel al documento fuente y al rulebook del juez.

{strictness_block}

Debes revisar:
- coherencia con el documento
- campos faltantes importantes
- inferencias débiles
- falsas remediaciones
- clasificación incorrecta de timeline vs troubleshooting action

Debes producir una salida JSON compatible con la estructura del juez:
- decision
- score
- score_breakdown
- critical_issues
- strengths
- issues
- improvement_actions
- feedback

No devuelvas texto fuera del JSON.
""".strip()


def build_judge_user_prompt(raw_sms: str, candidate_extraction_text: str) -> str:
    """
    Prompt de usuario para el juez.

    Recibe el documento original y la propuesta de extracción a evaluar.
    """
    return f"""
Evalúa la siguiente propuesta de extracción canónica.

Documento fuente:
---
{raw_sms}
---

Propuesta de extracción:
---
{candidate_extraction_text}
---
""".strip()