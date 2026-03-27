from __future__ import annotations

from pydantic import BaseModel, Field

from app.agentic.contracts import CanonicalExtractionResult


class JudgeScoreBreakdown(BaseModel):
    """
    Desglose estructurado de la puntuación del juez.
    """

    fidelity: float = Field(..., ge=0.0, le=10.0)
    coverage: float = Field(..., ge=0.0, le=10.0)
    structural_classification: float = Field(..., ge=0.0, le=10.0)
    semantic_prudence: float = Field(..., ge=0.0, le=10.0)
    metadata_quality: float = Field(..., ge=0.0, le=10.0)


class JudgeDecision(BaseModel):
    """
    Evaluación completa del juez semántico.
    """

    decision: str = Field(..., min_length=1)
    score: float = Field(..., ge=0.0, le=10.0)
    score_breakdown: JudgeScoreBreakdown
    critical_issues: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    improvement_actions: list[str] = Field(default_factory=list)
    feedback: str = Field(..., min_length=1)


class OrchestrationTrace(BaseModel):
    """
    Trazabilidad del flujo de orquestación.
    """

    primary_model_used: str | None = None
    judge_model_used: str | None = None
    fallback_model_used: str | None = None
    fallback_triggered: bool = False
    final_decision: str | None = None
    final_score: float | None = None


class CanonicalExtractionOrchestrationResult(BaseModel):
    """
    Resultado final del flujo de orquestación.
    """

    accepted_result: CanonicalExtractionResult | None = None
    judge_evaluation: JudgeDecision | None = None
    trace: OrchestrationTrace