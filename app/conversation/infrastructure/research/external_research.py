from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from html import unescape
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

from pydantic import BaseModel, Field

from app.core.config import settings
from app.conversation.application.services.clarification_service import (
    ClarificationAssessment,
)
from app.conversation.application.tools.base import ToolExecutionStatus, ToolResult
from app.conversation.contracts.requests import ConversationRequest
from app.conversation.contracts.session_models import (
    ConversationContext,
    ConversationSessionState,
)
from app.conversation.infrastructure.safety.sanitization import SanitizationService


class ExternalResearchSource(BaseModel):
    title: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    domain: str = Field(..., min_length=1)
    snippet: str | None = None
    category: Literal["whitelist", "blacklist", "caution", "unlisted"] = "unlisted"


class ExternalResearchResult(BaseModel):
    """
    Resultado estructurado de una consulta externa controlada.
    """

    enabled: bool = False
    attempted: bool = False
    used: bool = False
    status: Literal["disabled", "skipped", "blocked", "completed", "failed"] = (
        "disabled"
    )
    query: str | None = None
    sanitized_query: str | None = None
    sanitized_context: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    sources: list[ExternalResearchSource] = Field(default_factory=list)
    policy_summary: str | None = None
    policy_mode: str | None = None
    blocked_reasons: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def to_tool_result(self, tool_name: str) -> ToolResult:
        status_map = {
            "completed": ToolExecutionStatus.COMPLETED,
            "disabled": ToolExecutionStatus.DISABLED,
            "skipped": ToolExecutionStatus.SKIPPED,
            "blocked": ToolExecutionStatus.BLOCKED,
            "failed": ToolExecutionStatus.FAILED,
        }
        return ToolResult(
            tool_name=tool_name,
            status=status_map[self.status],
            summary=self.policy_summary,
            data=self.model_dump(mode="json"),
            errors=list(self.errors or self.blocked_reasons),
        )


class ExternalResearchPolicy(BaseModel):
    enabled: bool = True
    allow_unlisted_domains: bool = True
    caution_mode: bool = True
    whitelist_domains: list[str] = Field(default_factory=list)
    blacklist_domains: list[str] = Field(default_factory=list)
    caution_domains: list[str] = Field(default_factory=list)
    query_domain_hints: dict[str, list[str]] = Field(default_factory=dict)
    max_results: int = 3
    max_context_items: int = 3
    max_query_length: int = 280
    timeout_seconds: int = 5


class ExternalResearchPolicyBundle(BaseModel):
    manifest: ExternalResearchPolicy
    markdown_policy: str


class ExternalSearchProvider(ABC):
    @abstractmethod
    def search(
        self,
        query: str,
        *,
        max_results: int,
        timeout_seconds: int,
    ) -> list[ExternalResearchSource]:
        raise NotImplementedError


class DuckDuckGoSearchProvider(ExternalSearchProvider):
    """
    Provider liviano sin dependencias extras, apto para búsqueda web controlada.
    """

    _RESULT_PATTERN = re.compile(
        r'<a[^>]+class="result__a"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>',
        re.IGNORECASE | re.DOTALL,
    )
    _SNIPPET_PATTERN = re.compile(
        r'<a[^>]+class="result__a"[^>]+>.*?</a>.*?<a[^>]+class="result__snippet"[^>]*>(?P<snippet>.*?)</a>|'
        r'<a[^>]+class="result__a"[^>]+>.*?</a>.*?<div[^>]+class="result__snippet"[^>]*>(?P<snippet_div>.*?)</div>',
        re.IGNORECASE | re.DOTALL,
    )

    def search(
        self,
        query: str,
        *,
        max_results: int,
        timeout_seconds: int,
    ) -> list[ExternalResearchSource]:
        request = Request(
            url=f"https://duckduckgo.com/html/?q={quote_plus(query)}",
            headers={
                "User-Agent": (
                    "IncidentOperationalMemoryService/1.0 "
                    "(external-research)"
                )
            },
        )
        with urlopen(request, timeout=timeout_seconds) as response:
            html = response.read().decode("utf-8", errors="ignore")

        sources: list[ExternalResearchSource] = []
        snippets = [
            self._clean_html_text(match.group("snippet") or match.group("snippet_div") or "")
            for match in self._SNIPPET_PATTERN.finditer(html)
        ]
        for index, match in enumerate(self._RESULT_PATTERN.finditer(html)):
            if len(sources) >= max_results:
                break

            href = self._extract_target_url(match.group("href"))
            parsed = urlparse(href)
            if not parsed.netloc:
                continue

            domain = parsed.netloc.lower()
            title = self._clean_html_text(match.group("title"))
            snippet = snippets[index] if index < len(snippets) else None
            sources.append(
                ExternalResearchSource(
                    title=title or domain,
                    url=href,
                    domain=domain,
                    snippet=snippet or None,
                )
            )

        return sources

    @staticmethod
    def _extract_target_url(href: str) -> str:
        if "duckduckgo.com/l/?" not in href:
            return unescape(href)

        parsed = urlparse(unescape(href))
        uddg = parse_qs(parsed.query).get("uddg", [])
        if uddg:
            return unquote(uddg[0])

        return unescape(href)

    @staticmethod
    def _clean_html_text(raw: str) -> str:
        without_tags = re.sub(r"<[^>]+>", "", raw)
        normalized = unescape(without_tags)
        return " ".join(normalized.split())


class ExternalResearchPolicyLoader:
    def __init__(
        self,
        markdown_path: str | None = None,
        manifest_path: str | None = None,
    ) -> None:
        conversation_root = Path(__file__).resolve().parents[2]
        self._markdown_path = Path(markdown_path) if markdown_path else (
            conversation_root / "config" / "prompts" / "external_research_policy.md"
        )
        self._manifest_path = Path(manifest_path) if manifest_path else (
            conversation_root / "config" / "manifests" / "external_research_policy.json"
        )

    def load(self) -> ExternalResearchPolicyBundle:
        markdown_policy = self._markdown_path.read_text(encoding="utf-8").strip()
        manifest_payload = json.loads(
            self._manifest_path.read_text(encoding="utf-8")
        )
        return ExternalResearchPolicyBundle(
            manifest=ExternalResearchPolicy.model_validate(manifest_payload),
            markdown_policy=markdown_policy,
        )


class ExternalResearchService:
    """
    Investigación externa controlada por feature flag, policy y sanitización.
    """

    _EXPLICIT_RESEARCH_PHRASES = (
        "fuente oficial",
        "fuentes oficiales",
        "documentación oficial",
        "documentacion oficial",
        "consulta fuentes",
        "consulta documentación",
        "consulta documentacion",
        "revisa documentación",
        "revisa documentacion",
        "documentación de",
        "documentacion de",
        "según",
        "segun",
        "docs oficiales",
    )

    def __init__(
        self,
        policy_loader: ExternalResearchPolicyLoader | None = None,
        search_provider: ExternalSearchProvider | None = None,
        sanitization_service: SanitizationService | None = None,
    ) -> None:
        self._policy_loader = policy_loader or ExternalResearchPolicyLoader()
        self._search_provider = search_provider or DuckDuckGoSearchProvider()
        self._sanitization_service = sanitization_service or SanitizationService()

    def gather(
        self,
        request: ConversationRequest,
        context: ConversationContext,
    ) -> ExternalResearchResult:
        return self.research(
            request=request,
            context=context,
            session_state=ConversationSessionState(session_id=context.session_id),
            clarification=None,
            arguments={},
        )

    def research(
        self,
        *,
        request: ConversationRequest,
        context: ConversationContext,
        session_state: ConversationSessionState,
        clarification: ClarificationAssessment | None,
        arguments: dict[str, object],
    ) -> ExternalResearchResult:
        if not settings.features.allow_external_sources:
            return ExternalResearchResult(
                enabled=False,
                status="disabled",
                policy_summary="External research disabled by feature flag.",
            )

        policy_bundle = self._policy_loader.load()
        policy = policy_bundle.manifest
        if not policy.enabled:
            return ExternalResearchResult(
                enabled=False,
                status="disabled",
                policy_summary="External research disabled by manifest policy.",
            )

        query = self._build_external_query(
            request=request,
            context=context,
            session_state=session_state,
            clarification=clarification,
            max_context_items=policy.max_context_items,
            max_query_length=policy.max_query_length,
        )
        if not query:
            return ExternalResearchResult(
                enabled=True,
                attempted=False,
                status="skipped",
                policy_summary="No useful query built for external research.",
            )

        requested_domains = self._resolve_requested_domains(query, policy)
        blacklisted = [
            domain
            for domain in requested_domains
            if self._classify_domain(domain, policy) == "blacklist"
        ]
        if blacklisted:
            return ExternalResearchResult(
                enabled=True,
                attempted=False,
                status="blocked",
                query=query,
                blocked_reasons=[
                    f"Blocked by policy blacklist: {', '.join(sorted(blacklisted))}"
                ],
                policy_summary=self._build_policy_summary(policy_bundle, "blocked"),
                policy_mode="blocked",
            )

        scope = self._sanitization_service.build_scope()
        sanitized_query = self._sanitization_service.sanitize_text_for_external(
            query,
            scope,
        )
        sanitized_context = [
            self._sanitization_service.sanitize_text_for_external(item, scope)
            for item in self._build_context_fragments(
                context=context,
                session_state=session_state,
                clarification=clarification,
                max_items=policy.max_context_items,
            )
        ]

        effective_query = sanitized_query
        if sanitized_context:
            effective_query = (
                sanitized_query + " " + " ".join(sanitized_context[: policy.max_context_items])
            ).strip()
        effective_query = effective_query[: policy.max_query_length]

        try:
            raw_sources = self._search_provider.search(
                effective_query,
                max_results=max(policy.max_results * 2, policy.max_results),
                timeout_seconds=policy.timeout_seconds,
            )
        except Exception as exc:
            return ExternalResearchResult(
                enabled=True,
                attempted=True,
                status="failed",
                query=query,
                sanitized_query=sanitized_query,
                sanitized_context=sanitized_context,
                errors=[str(exc)],
                policy_summary=self._build_policy_summary(policy_bundle, "failed"),
                policy_mode=self._resolve_policy_mode(policy, requested_domains),
            )

        filtered_sources = self._filter_sources(
            raw_sources,
            policy=policy,
            max_results=policy.max_results,
        )
        if not filtered_sources:
            return ExternalResearchResult(
                enabled=True,
                attempted=True,
                status="blocked" if raw_sources else "failed",
                query=query,
                sanitized_query=sanitized_query,
                sanitized_context=sanitized_context,
                blocked_reasons=(
                    ["All external results were filtered by policy."]
                    if raw_sources
                    else []
                ),
                policy_summary=self._build_policy_summary(policy_bundle, "empty"),
                policy_mode=self._resolve_policy_mode(policy, requested_domains),
            )

        findings = [
            self._format_finding(source)
            for source in filtered_sources
        ]
        return ExternalResearchResult(
            enabled=True,
            attempted=True,
            used=True,
            status="completed",
            query=query,
            sanitized_query=sanitized_query,
            sanitized_context=sanitized_context,
            findings=findings,
            sources=filtered_sources,
            policy_summary=self._build_policy_summary(policy_bundle, "completed"),
            policy_mode=self._resolve_policy_mode(policy, requested_domains),
        )

    def should_research(
        self,
        request: ConversationRequest,
        context: ConversationContext,
        clarification: ClarificationAssessment | None,
    ) -> bool:
        if not settings.features.allow_external_sources:
            return False

        message = request.message.strip().lower()
        requested_capabilities = {
            capability.strip().lower()
            for capability in request.requested_capabilities
        }
        explicit_capability = bool(
            requested_capabilities
            & {
                "external_research",
                "official_docs",
                "official_documentation",
                "documentation_lookup",
            }
        )
        explicit_language = any(
            phrase in message for phrase in self._EXPLICIT_RESEARCH_PHRASES
        )
        mentions_vendor = bool(self._resolve_requested_domains(message, self._policy_loader.load().manifest))
        internal_history_insufficient = not context.historical_context.has_evidence
        clarification_allows = clarification is None or clarification.sufficiency_level != "insufficient"

        return explicit_capability or explicit_language or (
            internal_history_insufficient and mentions_vendor and clarification_allows
        )

    def _build_external_query(
        self,
        *,
        request: ConversationRequest,
        context: ConversationContext,
        session_state: ConversationSessionState,
        clarification: ClarificationAssessment | None,
        max_context_items: int,
        max_query_length: int,
    ) -> str:
        pieces = [request.message.strip()]
        for item in self._build_context_fragments(
            context=context,
            session_state=session_state,
            clarification=clarification,
            max_items=max_context_items,
        ):
            if item and item not in pieces:
                pieces.append(item)
        return " | ".join(pieces)[:max_query_length].strip()

    def _build_context_fragments(
        self,
        *,
        context: ConversationContext,
        session_state: ConversationSessionState,
        clarification: ClarificationAssessment | None,
        max_items: int,
    ) -> list[str]:
        fragments: list[str] = []
        if session_state.active_issue_summary:
            fragments.append(session_state.active_issue_summary)
        if session_state.active_entities:
            fragments.append(
                "Entidades activas: " + ", ".join(session_state.active_entities[:3])
            )
        if clarification and clarification.known_information:
            fragments.append(
                "Información conocida: "
                + ", ".join(
                    f"{key}={value}"
                    for key, value in list(clarification.known_information.items())[:4]
                )
            )
        historical = context.historical_context
        if historical.primary_incident is not None:
            fragments.extend(
                item
                for item in [
                    historical.primary_incident.header,
                    historical.primary_incident.failure_text,
                    historical.primary_incident.resolution_summary,
                ]
                if item
            )
        if historical.semantic_matches:
            fragments.append(historical.semantic_matches[0].document_text)
        return fragments[:max_items]

    def _resolve_requested_domains(
        self,
        query_text: str,
        policy: ExternalResearchPolicy,
    ) -> list[str]:
        lowered = query_text.lower()
        domains: list[str] = []
        for hint, hint_domains in policy.query_domain_hints.items():
            if hint.lower() in lowered:
                domains.extend(hint_domains)
        return list(dict.fromkeys(domains))

    @staticmethod
    def _classify_domain(
        domain: str,
        policy: ExternalResearchPolicy,
    ) -> Literal["whitelist", "blacklist", "caution", "unlisted"]:
        normalized = domain.lower()
        for candidate in policy.blacklist_domains:
            if normalized == candidate.lower() or normalized.endswith("." + candidate.lower()):
                return "blacklist"
        for candidate in policy.whitelist_domains:
            if normalized == candidate.lower() or normalized.endswith("." + candidate.lower()):
                return "whitelist"
        for candidate in policy.caution_domains:
            if normalized == candidate.lower() or normalized.endswith("." + candidate.lower()):
                return "caution"
        return "unlisted"

    def _filter_sources(
        self,
        sources: list[ExternalResearchSource],
        *,
        policy: ExternalResearchPolicy,
        max_results: int,
    ) -> list[ExternalResearchSource]:
        accepted: list[ExternalResearchSource] = []
        for source in sources:
            category = self._classify_domain(source.domain, policy)
            if category == "blacklist":
                continue
            if category == "unlisted" and not policy.allow_unlisted_domains:
                continue
            if category == "unlisted" and not policy.caution_mode:
                continue
            accepted.append(source.model_copy(update={"category": category}))
            if len(accepted) >= max_results:
                break
        return accepted

    def _resolve_policy_mode(
        self,
        policy: ExternalResearchPolicy,
        requested_domains: list[str],
    ) -> str:
        if requested_domains:
            categories = {
                self._classify_domain(domain, policy)
                for domain in requested_domains
            }
            if "blacklist" in categories:
                return "blocked"
            if "caution" in categories or "unlisted" in categories:
                return "caution"
            return "whitelist"
        return "caution" if policy.caution_mode else "whitelist"

    @staticmethod
    def _format_finding(source: ExternalResearchSource) -> str:
        detail = source.snippet or "resultado externo relevante"
        return f"{source.title} ({source.domain}): {detail}"

    def _build_policy_summary(
        self,
        policy_bundle: ExternalResearchPolicyBundle,
        mode: str,
    ) -> str:
        headline = policy_bundle.markdown_policy.splitlines()[0].lstrip("# ").strip()
        return f"{headline} [{mode}]"
