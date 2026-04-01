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
from app.core.ingestion_trace import bind_case_id, bind_judge_result, log_ingestion_event


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
        log_ingestion_event(
            layer="orchestrator",
            event="extract_started",
            payload={"raw_sms_preview": " ".join(raw_sms.split())[:240]},
        )

        try:
            primary_response = self._invoke_primary_extractor(raw_sms)
        except Exception as exc:
            log_ingestion_event(
                layer="orchestrator",
                event="primary_extractor_failed",
                status="error",
                error=str(exc),
            )
            print("[ERROR] [ORCHESTRATOR] Falló _invoke_primary_extractor:", str(exc))
            raise
        trace.primary_model_used = primary_response.model_name
        log_ingestion_event(
            layer="orchestrator",
            event="primary_extractor_completed",
            payload={
                "model_name": primary_response.model_name,
                "provider_response_id": getattr(
                    primary_response,
                    "provider_response_id",
                    None,
                ),
                "output_preview": " ".join(primary_response.output_text.split())[:320],
            },
        )
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
        bind_case_id(primary_result.incident_case.case_id)
        log_ingestion_event(
            layer="orchestrator",
            event="primary_result_parsed",
            payload={
                "case_id": primary_result.incident_case.case_id,
                "timeline_entries_count": len(primary_result.timeline_entries),
                "troubleshooting_actions_count": len(
                    primary_result.troubleshooting_actions
                ),
            },
        )
        print(
            "[ORCHESTRATOR] primary_result parseado:",
            primary_result.model_dump(mode="json"),
        )

        primary_judge_evaluation = self._judge.evaluate(
            raw_sms=raw_sms,
            candidate_extraction_text=primary_response.output_text,
        )
        trace.judge_model_used = settings.agentic_models.semantic_judge_model
        bind_judge_result(
            judge_decision=primary_judge_evaluation.decision,
            final_score=primary_judge_evaluation.score,
        )
        log_ingestion_event(
            layer="orchestrator",
            event="primary_judge_completed",
            payload={
                "decision": primary_judge_evaluation.decision,
                "score": primary_judge_evaluation.score,
                "critical_issues_count": len(primary_judge_evaluation.critical_issues),
            },
        )
        print(
            "[ORCHESTRATOR] primary_judge_evaluation:",
            primary_judge_evaluation.model_dump(mode="json"),
        )

        if self._is_accepted(primary_judge_evaluation):
            trace.final_decision = primary_judge_evaluation.decision
            trace.final_score = primary_judge_evaluation.score
            bind_judge_result(
                judge_decision=trace.final_decision,
                final_score=trace.final_score,
                fallback_triggered=False,
            )
            result = CanonicalExtractionOrchestrationResult(
                accepted_result=primary_result,
                judge_evaluation=primary_judge_evaluation,
                trace=trace,
            )
            log_ingestion_event(
                layer="orchestrator",
                event="accepted_in_primary",
                payload={
                    "decision": trace.final_decision,
                    "score": trace.final_score,
                },
            )
            print(
                "[ORCHESTRATOR] resultado final aceptado en primary:",
                result.model_dump(mode="json"),
            )
            return result

        trace.fallback_triggered = True
        bind_judge_result(fallback_triggered=True)
        log_ingestion_event(
            layer="orchestrator",
            event="fallback_triggered",
            payload={
                "decision": primary_judge_evaluation.decision,
                "score": primary_judge_evaluation.score,
            },
        )
        print("[ORCHESTRATOR] Fallback activado")

        fallback_result = self._fallback.rebuild(
            raw_sms=raw_sms,
            previous_extraction_text=primary_response.output_text,
            judge_feedback_text=primary_judge_evaluation.feedback,
        )
        trace.fallback_model_used = settings.agentic_models.fallback_extractor_model
        bind_case_id(fallback_result.incident_case.case_id)
        log_ingestion_event(
            layer="orchestrator",
            event="fallback_completed",
            payload={
                "case_id": fallback_result.incident_case.case_id,
                "timeline_entries_count": len(fallback_result.timeline_entries),
                "troubleshooting_actions_count": len(
                    fallback_result.troubleshooting_actions
                ),
            },
        )
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
        bind_judge_result(
            judge_decision=trace.final_decision,
            final_score=trace.final_score,
            fallback_triggered=True,
        )
        log_ingestion_event(
            layer="orchestrator",
            event="fallback_judge_completed",
            payload={
                "decision": fallback_judge_evaluation.decision,
                "score": fallback_judge_evaluation.score,
                "critical_issues_count": len(fallback_judge_evaluation.critical_issues),
            },
        )
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
            log_ingestion_event(
                layer="orchestrator",
                event="accepted_in_fallback",
                payload={
                    "decision": trace.final_decision,
                    "score": trace.final_score,
                },
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
        log_ingestion_event(
            layer="orchestrator",
            event="rejected_after_fallback",
            status="error",
            payload={
                "decision": trace.final_decision,
                "score": trace.final_score,
            },
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
