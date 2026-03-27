from __future__ import annotations

from app.agentic.contracts import CanonicalExtractionResult
from app.agentic.contracts.response_schemas import (
    build_canonical_extraction_response_schema,
)
from app.agentic.orchestrator.response_parsers import parse_extraction_response
from app.agentic.prompts import (
    PromptSettings,
    build_fallback_extractor_system_prompt,
    build_fallback_extractor_user_prompt,
)
from app.agentic.providers import (
    BaseModelGateway,
    ModelInvocationContext,
    ModelRawResponse,
)
from app.core.config import settings


class FallbackExtractor:
    def __init__(
        self,
        model_gateway: BaseModelGateway,
        prompt_settings: PromptSettings | None = None,
    ) -> None:
        self._model_gateway = model_gateway
        self._prompt_settings = prompt_settings or PromptSettings()

    def rebuild(
        self,
        raw_sms: str,
        previous_extraction_text: str,
        judge_feedback_text: str,
    ) -> CanonicalExtractionResult:
        response = self._invoke_fallback(
            raw_sms=raw_sms,
            previous_extraction_text=previous_extraction_text,
            judge_feedback_text=judge_feedback_text,
        )
        return self._parse_extraction_response(response)

    def _invoke_fallback(
        self,
        raw_sms: str,
        previous_extraction_text: str,
        judge_feedback_text: str,
    ) -> ModelRawResponse:
        context = ModelInvocationContext(
            system_instruction=build_fallback_extractor_system_prompt(
                self._prompt_settings
            ),
            user_input=build_fallback_extractor_user_prompt(
                raw_sms=raw_sms,
                previous_extraction_text=previous_extraction_text,
                judge_feedback_text=judge_feedback_text,
            ),
            task_name="fallback_canonical_extraction",
            model_name=settings.agentic_models.fallback_extractor_model,
            temperature=0.2,
            extra_config={
                "response_mime_type": "application/json",
                "response_schema": build_canonical_extraction_response_schema(),
            },
        )
        return self._model_gateway.invoke(context)

    def _parse_extraction_response(
        self,
        response: ModelRawResponse,
    ) -> CanonicalExtractionResult:
        return parse_extraction_response(response)