from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field

from app.conversation.contracts.requests import ConversationRequest
from app.conversation.contracts.responses import ConversationAgentResult


@dataclass
class SanitizationScope:
    """
    Mantiene placeholders estables dentro de una misma ejecución de sanitización.
    """

    _maps: dict[str, dict[str, str]] = field(default_factory=dict)
    _counters: dict[str, int] = field(default_factory=dict)

    def redact(self, label: str, value: str) -> str:
        normalized = value.strip()
        bucket = self._maps.setdefault(label, {})
        if normalized in bucket:
            return bucket[normalized]

        next_index = self._counters.get(label, 0) + 1
        self._counters[label] = next_index
        placeholder = f"[{label}_{next_index}]"
        bucket[normalized] = placeholder
        return placeholder


class SanitizationService:
    """
    Sanitización real para proteger contexto antes de cualquier salida externa.
    """

    _SECRET_ASSIGNMENT_PATTERN = re.compile(
        r"(?i)\b(api[_-]?key|token|secret|password|passwd|pwd)\b\s*[:=]\s*([^\s,;]+)"
    )
    _SENSITIVE_USER_PATTERN = re.compile(
        r"(?i)\b(usuario|user|login|owner|responsable|analista|ingeniero)\b\s*[:=]?\s*([A-Za-z0-9._-]{3,})"
    )
    _EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b"
    )
    _PATH_PATTERN = re.compile(
        r"(?:(?:[A-Za-z]:\\|/)(?:[^\\\s:;,]+[\\/]){1,}[^\\\s:;,]+)"
    )
    _PRIVATE_DOMAIN_PATTERN = re.compile(
        r"\b(?:[A-Za-z0-9-]+\.)+(?:internal|intra|corp|local|lan|private|svc|cluster\.local)\b",
        re.IGNORECASE,
    )
    _HOSTNAME_PATTERN = re.compile(
        r"\b[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9-]{1,63})*\b",
        re.IGNORECASE,
    )
    _PERSON_CONTEXT_PATTERN = re.compile(
        r"(?i)\b(?:contacto|persona|responsable|analista|ingeniero|owner)\b\s*[:=]?\s*"
        r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,2})"
    )
    _INTERNAL_ID_PATTERN = re.compile(
        r"(?i)\b(?:internal[_-]?id|asset|employee[_-]?id|host[_-]?id)\b\s*[:=]\s*([A-Za-z0-9._-]+)"
    )
    _IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

    def sanitize_request(self, request: ConversationRequest) -> ConversationRequest:
        return request

    def sanitize_response(
        self,
        response: ConversationAgentResult,
    ) -> ConversationAgentResult:
        return response

    def build_scope(self) -> SanitizationScope:
        return SanitizationScope()

    def sanitize_text_for_external(
        self,
        text: str,
        scope: SanitizationScope | None = None,
    ) -> str:
        scope = scope or self.build_scope()
        sanitized = text
        sanitized = self._sanitize_secrets(sanitized, scope)
        sanitized = self._sanitize_ips(sanitized, scope)
        sanitized = self._sanitize_private_domains(sanitized, scope)
        sanitized = self._sanitize_people(sanitized, scope)
        sanitized = self._sanitize_sensitive_users(sanitized, scope)
        sanitized = self._sanitize_paths(sanitized, scope)
        sanitized = self._sanitize_internal_ids(sanitized, scope)
        return sanitized

    def sanitize_texts_for_external(self, texts: list[str]) -> list[str]:
        scope = self.build_scope()
        return [self.sanitize_text_for_external(text, scope) for text in texts]

    def _sanitize_secrets(self, text: str, scope: SanitizationScope) -> str:
        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            secret_value = match.group(2)
            placeholder = scope.redact("REDACTED_SECRET", secret_value)
            return f"{key}={placeholder}"

        return self._SECRET_ASSIGNMENT_PATTERN.sub(replace, text)

    def _sanitize_ips(self, text: str, scope: SanitizationScope) -> str:
        def replace(match: re.Match[str]) -> str:
            candidate = match.group(0)
            try:
                ip = ipaddress.ip_address(candidate)
            except ValueError:
                return candidate

            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return scope.redact("INTERNAL_IP", candidate)

            return candidate

        return self._IP_PATTERN.sub(replace, text)

    def _sanitize_private_domains(self, text: str, scope: SanitizationScope) -> str:
        sanitized = self._PRIVATE_DOMAIN_PATTERN.sub(
            lambda match: scope.redact("PRIVATE_DOMAIN", match.group(0)),
            text,
        )

        def replace_host(match: re.Match[str]) -> str:
            candidate = match.group(0)
            lowered = candidate.lower()
            if lowered in {"localhost"}:
                return scope.redact("INTERNAL_HOST", candidate)
            if lowered.endswith(("-prd", "-prod", "-qa", "-dev", "-int")):
                return scope.redact("INTERNAL_HOST", candidate)
            return candidate

        return self._HOSTNAME_PATTERN.sub(replace_host, sanitized)

    def _sanitize_people(self, text: str, scope: SanitizationScope) -> str:
        return self._PERSON_CONTEXT_PATTERN.sub(
            lambda match: match.group(0).replace(
                match.group(1),
                scope.redact("PERSON", match.group(1)),
            ),
            text,
        )

    def _sanitize_sensitive_users(self, text: str, scope: SanitizationScope) -> str:
        sanitized = self._SENSITIVE_USER_PATTERN.sub(
            lambda match: match.group(0).replace(
                match.group(2),
                scope.redact("SENSITIVE_USER", match.group(2)),
            ),
            text,
        )
        return self._EMAIL_PATTERN.sub(
            lambda match: scope.redact("SENSITIVE_USER", match.group(0)),
            sanitized,
        )

    def _sanitize_paths(self, text: str, scope: SanitizationScope) -> str:
        return self._PATH_PATTERN.sub(
            lambda match: scope.redact("SENSITIVE_PATH", match.group(0)),
            text,
        )

    def _sanitize_internal_ids(self, text: str, scope: SanitizationScope) -> str:
        return self._INTERNAL_ID_PATTERN.sub(
            lambda match: match.group(0).replace(
                match.group(1),
                scope.redact("INTERNAL_ID", match.group(1)),
            ),
            text,
        )
