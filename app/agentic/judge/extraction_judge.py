from __future__ import annotations

from app.agentic.contracts.response_schemas import build_judge_response_schema
from app.agentic.orchestrator.orchestration_models import JudgeDecision
from app.agentic.orchestrator.response_parsers import parse_judge_response
from app.agentic.prompts import (
    PromptSettings,
    build_judge_system_prompt,
    build_judge_user_prompt,
)
from app.agentic.providers import (
    BaseModelGateway,
    ModelInvocationContext,
    ModelRawResponse,
)
from app.core.config import settings


class ExtractionJudge:
    def __init__(
        self,
        model_gateway: BaseModelGateway,
        prompt_settings: PromptSettings | None = None,
    ) -> None:
        self._model_gateway = model_gateway
        self._prompt_settings = prompt_settings or PromptSettings()

    def evaluate(
        self,
        raw_sms: str,
        candidate_extraction_text: str,
    ) -> JudgeDecision:
        response = self._invoke_judge(
            raw_sms=raw_sms,
            candidate_extraction_text=candidate_extraction_text,
        )
        return self._parse_judge_response(response)

    def _invoke_judge(
        self,
        raw_sms: str,
        candidate_extraction_text: str,
    ) -> ModelRawResponse:
        context = ModelInvocationContext(
            system_instruction=build_judge_system_prompt(self._prompt_settings),
            user_input=build_judge_user_prompt(
                raw_sms=raw_sms,
                candidate_extraction_text=candidate_extraction_text,
            ),
            task_name="judge_canonical_extraction",
            model_name=settings.agentic_models.semantic_judge_model,
            temperature=0.1,
            extra_config={
                "response_mime_type": "application/json",
                "response_schema": build_judge_response_schema(),
            },
        )
        return self._model_gateway.invoke(context)

    def _parse_judge_response(self, response: ModelRawResponse) -> JudgeDecision:
        return parse_judge_response(response)