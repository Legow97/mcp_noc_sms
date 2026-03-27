from __future__ import annotations

import json

from app.agentic.contracts import CanonicalExtractionResult
from app.agentic.orchestrator.orchestration_models import JudgeDecision
from app.agentic.providers import ModelRawResponse


def parse_extraction_response(response: ModelRawResponse) -> CanonicalExtractionResult:
    """
    Convierte la salida textual del extractor/fallback a CanonicalExtractionResult.
    """
    try:
        payload = json.loads(response.output_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "La salida del extractor no es JSON válido."
        ) from exc

    try:
        return CanonicalExtractionResult.model_validate(payload)
    except Exception as exc:
        raise ValueError(
            "La salida del extractor no coincide con CanonicalExtractionResult."
        ) from exc


def parse_judge_response(response: ModelRawResponse) -> JudgeDecision:
    """
    Convierte la salida textual del juez a JudgeDecision.
    """
    try:
        payload = json.loads(response.output_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "La salida del juez no es JSON válido."
        ) from exc

    try:
        return JudgeDecision.model_validate(payload)
    except Exception as exc:
        raise ValueError(
            "La salida del juez no coincide con JudgeDecision."
        ) from exc