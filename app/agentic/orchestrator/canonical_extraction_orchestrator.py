from __future__ import annotations

from app.agentic.contracts.response_schemas import (
    build_canonical_extraction_response_schema,
)
from app.agentic.fallback import FallbackExtractor
from app.agentic.judge import ExtractionJudge
from app.agentic.orchestrator.orchestration_models import (
    CanonicalExtractionOrchestrationResult,
    JudgeDecision,
    OrchestrationTrace,
)
from app.agentic.orchestrator.response_parsers import parse_extraction_response
from app.agentic.prompts import (
    PromptSettings,
    build_primary_extractor_system_prompt,
    build_primary_extractor_user_prompt,
)
from app.agentic.providers import (
    BaseModelGateway,
    ModelInvocationContext,
    ModelRawResponse,
)
from app.core.config import settings


class CanonicalExtractionOrchestrator:
    def __init__(
        self,
        model_gateway: BaseModelGateway,
        prompt_settings: PromptSettings | None = None,
    ) -> None:
        self._model_gateway = model_gateway
        self._prompt_settings = prompt_settings or PromptSettings()
        self._judge = ExtractionJudge(
            model_gateway=model_gateway,
            prompt_settings=self._prompt_settings,
        )
        self._fallback = FallbackExtractor(
            model_gateway=model_gateway,
            prompt_settings=self._prompt_settings,
        )

    def extract(self, raw_sms: str) -> CanonicalExtractionOrchestrationResult:
        trace = OrchestrationTrace()
        print("[ORCHESTRATOR] extract() raw_sms recibido:", raw_sms)

        try:
            primary_response = self._invoke_primary_extractor(raw_sms)
        except Exception as exc:
            print("[ERROR] [ORCHESTRATOR] Falló _invoke_primary_extractor:", str(exc))
            raise
        trace.primary_model_used = primary_response.model_name
        print(
            "[ORCHESTRATOR] primary_response:",
            {
                "model_name": primary_response.model_name,
                "output_text": primary_response.output_text,
                "usage": primary_response.usage.model_dump(mode="json")
                if getattr(primary_response, "usage", None) is not None
                and hasattr(primary_response.usage, "model_dump")
                else getattr(primary_response, "usage", None),
                "provider_response_id": getattr(
                    primary_response, "provider_response_id", None
                ),
            },
        )

        primary_result = parse_extraction_response(primary_response)
        print(
            "[ORCHESTRATOR] primary_result parseado:",
            primary_result.model_dump(mode="json"),
        )

        primary_judge_evaluation = self._judge.evaluate(
            raw_sms=raw_sms,
            candidate_extraction_text=primary_response.output_text,
        )
        trace.judge_model_used = settings.agentic_models.semantic_judge_model
        print(
            "[ORCHESTRATOR] primary_judge_evaluation:",
            primary_judge_evaluation.model_dump(mode="json"),
        )

        if self._is_accepted(primary_judge_evaluation):
            trace.final_decision = primary_judge_evaluation.decision
            trace.final_score = primary_judge_evaluation.score
            result = CanonicalExtractionOrchestrationResult(
                accepted_result=primary_result,
                judge_evaluation=primary_judge_evaluation,
                trace=trace,
            )
            print(
                "[ORCHESTRATOR] resultado final aceptado en primary:",
                result.model_dump(mode="json"),
            )
            return result

        trace.fallback_triggered = True
        print("[ORCHESTRATOR] Fallback activado")

        fallback_result = self._fallback.rebuild(
            raw_sms=raw_sms,
            previous_extraction_text=primary_response.output_text,
            judge_feedback_text=primary_judge_evaluation.feedback,
        )
        trace.fallback_model_used = settings.agentic_models.fallback_extractor_model
        print(
            "[ORCHESTRATOR] fallback_result:",
            fallback_result.model_dump(mode="json"),
        )

        fallback_judge_evaluation = self._judge.evaluate(
            raw_sms=raw_sms,
            candidate_extraction_text=fallback_result.model_dump_json(indent=2),
        )
        trace.final_decision = fallback_judge_evaluation.decision
        trace.final_score = fallback_judge_evaluation.score
        print(
            "[ORCHESTRATOR] fallback_judge_evaluation:",
            fallback_judge_evaluation.model_dump(mode="json"),
        )

        if self._is_accepted(fallback_judge_evaluation):
            result = CanonicalExtractionOrchestrationResult(
                accepted_result=fallback_result,
                judge_evaluation=fallback_judge_evaluation,
                trace=trace,
            )
            print(
                "[ORCHESTRATOR] resultado final aceptado en fallback:",
                result.model_dump(mode="json"),
            )
            return result

        result = CanonicalExtractionOrchestrationResult(
            accepted_result=None,
            judge_evaluation=fallback_judge_evaluation,
            trace=trace,
        )
        print(
            "[ORCHESTRATOR] resultado final rechazado:",
            result.model_dump(mode="json"),
        )
        return result

    def _invoke_primary_extractor(self, raw_sms: str) -> ModelRawResponse:
        context = ModelInvocationContext(
            system_instruction=build_primary_extractor_system_prompt(
                self._prompt_settings
            ),
            user_input=build_primary_extractor_user_prompt(raw_sms),
            task_name="primary_canonical_extraction",
            model_name=settings.agentic_models.primary_extractor_model,
            temperature=0.2,
            extra_config={
                "response_mime_type": "application/json",
                "response_schema": build_canonical_extraction_response_schema(),
            },
        )
        return self._model_gateway.invoke(context)

    @staticmethod
    def _is_accepted(judge_evaluation: JudgeDecision) -> bool:
        if judge_evaluation.decision not in {
            "accepted",
            "accepted_with_observations",
        }:
            return False

        if judge_evaluation.score < 8:
            return False

        if judge_evaluation.critical_issues:
            return False

        return True
