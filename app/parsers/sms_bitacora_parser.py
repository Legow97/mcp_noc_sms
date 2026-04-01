from dataclasses import dataclass
from datetime import datetime

from app.api.schemas.incident_requests import IngestSmsRequest
from app.core.temporal import extract_explicit_sms_datetime
from app.domain.enums import IncidentStatus, SourceType


@dataclass(slots=True)
class ParsedSmsBitacora:
    """
    Resultado parseado inicial de un SMS de bitácora.
    """

    source_type: str
    header: str | None
    failure_text: str
    impact_text: str | None
    start_time: datetime | None
    incident_status: str
    raw_sms: str
    parser_output_json: dict
    enrichment_json: dict


class SmsBitacoraParser:
    """
    Parser inicial con extracción mínima de secciones.

    Esta versión:
    - trata el SMS como documento plano
    - intenta extraer header
    - intenta extraer failure_text
    - intenta extraer impact_text
    - sigue dejando trazabilidad del rulebook

    Más adelante podrá evolucionar a extractor canónico más robusto
    y luego a flujo agentic con LangGraph.
    """

    RULEBOOK_PATH = "docs/incident_extraction_rules.md"
    RULEBOOK_VERSION = "v1"

    FAILURE_LABELS = (
        "FALLA",
        "INCIDENCIA",
    )
    IMPACT_LABELS = (
        "IMPACTO",
        "AFECTACIÓN",
    )
    STOP_LABELS = (
        "SOLUCIONADO",
        "ACCIONES",
        "CAUSA",
        "SOLUCIÓN",
        "TICKET",
        "FECHA/H.INICIO",
        "FECHA/H.FIN",
        "HORA DE SOLUCIÓN",
    )

    def parse(self, payload: IngestSmsRequest) -> ParsedSmsBitacora:
        raw_text = payload.raw_text.strip()

        header = self._extract_header(raw_text)
        failure_text = self._extract_failure_text(raw_text)
        impact_text = self._extract_impact_text(raw_text)
        start_time = extract_explicit_sms_datetime(
            raw_text,
            labels=("FECHA/H.INICIO", "FECHA/H. INICIO", "HORA DE INICIO"),
        )

        return ParsedSmsBitacora(
            source_type=SourceType.SMS_BITACORA.value,
            header=header,
            failure_text=failure_text,
            impact_text=impact_text,
            start_time=start_time,
            incident_status=IncidentStatus.CLOSED.value,
            raw_sms=raw_text,
            parser_output_json={
                "parser_name": "SmsBitacoraParser",
                "parser_version": "v1_min_sections",
                "parsing_mode": "document_extraction_minimal",
                "rulebook_path": self.RULEBOOK_PATH,
                "rulebook_version": self.RULEBOOK_VERSION,
                "rulebook_enabled": True,
                "header_detected": header is not None,
                "failure_detected": bool(failure_text),
                "impact_detected": impact_text is not None,
                "start_time_detected": start_time is not None,
            },
            enrichment_json={},
        )

    def _extract_header(self, raw_text: str) -> str | None:
        """
        Extrae la primera línea significativa del documento.
        """
        for line in raw_text.splitlines():
            cleaned = line.strip()
            if cleaned:
                return cleaned
        return None

    def _extract_failure_text(self, raw_text: str) -> str:
        """
        Intenta extraer el bloque de falla/incidencia.
        Si no encuentra una etiqueta clara, usa fallback controlado.
        """
        extracted = self._extract_block_by_labels(
            raw_text=raw_text,
            start_labels=self.FAILURE_LABELS,
            stop_labels=self.STOP_LABELS,
        )
        if extracted:
            return extracted

        return raw_text[:500].strip()

    def _extract_impact_text(self, raw_text: str) -> str | None:
        """
        Intenta extraer el bloque de impacto/afectación.
        """
        extracted = self._extract_block_by_labels(
            raw_text=raw_text,
            start_labels=self.IMPACT_LABELS,
            stop_labels=self.STOP_LABELS,
        )
        return extracted or None

    def _extract_block_by_labels(
        self,
        raw_text: str,
        start_labels: tuple[str, ...],
        stop_labels: tuple[str, ...],
    ) -> str | None:
        """
        Extrae un bloque textual a partir de etiquetas de inicio y fin.
        """
        lines = raw_text.splitlines()
        start_index = None

        for index, line in enumerate(lines):
            normalized_line = self._normalize_label_candidate(line)
            if any(normalized_line.startswith(label) for label in start_labels):
                start_index = index
                break

        if start_index is None:
            return None

        collected_lines: list[str] = []
        first_line = lines[start_index]

        after_colon = self._extract_inline_content(first_line)
        if after_colon:
            collected_lines.append(after_colon)

        for line in lines[start_index + 1 :]:
            normalized_line = self._normalize_label_candidate(line)

            if any(normalized_line.startswith(label) for label in stop_labels):
                break

            stripped_line = line.strip()
            if stripped_line:
                collected_lines.append(stripped_line)

        normalized_block = self._normalize_block_text(collected_lines)
        return normalized_block or None

    @staticmethod
    def _normalize_label_candidate(line: str) -> str:
        return line.strip().upper()

    @staticmethod
    def _extract_inline_content(line: str) -> str | None:
        if ":" in line:
            _, right_part = line.split(":", 1)
            value = right_part.strip()
            return value or None
        return None

    @staticmethod
    def _normalize_block_text(lines: list[str]) -> str:
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        return " ".join(cleaned_lines).strip()
