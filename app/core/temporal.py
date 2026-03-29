from __future__ import annotations

from datetime import datetime
import re
from zoneinfo import ZoneInfo


_SMS_DATETIME_PATTERN = re.compile(
    r"(?P<date>\d{2}/\d{2}/\d{4})\s+(?P<time>\d{1,2}:\d{2})(?:\s*hrs?\.?)?",
    re.IGNORECASE,
)

_ISO_DATETIME_SUFFIX_Z_PATTERN = re.compile(r"Z$", re.IGNORECASE)
_OPERATIONAL_TIMEZONE = ZoneInfo("America/Lima")


def parse_incident_datetime(value: str | None) -> datetime | None:
    """
    Convierte formatos temporales aceptados por el proyecto a datetime aware.

    Acepta:
    - ISO-8601
    - formato SMS: DD/MM/YYYY H:MM [hrs.]

    Regla:
    - si la entrada no trae zona horaria explícita, se interpreta como
      hora local operativa del incidente en America/Lima.
    """
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    parsed = _parse_iso_datetime(normalized)
    if parsed is not None:
        return parsed

    match = _SMS_DATETIME_PATTERN.search(normalized)
    if match is None:
        return None

    sms_value = f"{match.group('date')} {match.group('time')}"
    return datetime.strptime(sms_value, "%d/%m/%Y %H:%M").replace(
        tzinfo=_OPERATIONAL_TIMEZONE
    )


def extract_explicit_sms_datetime(
    raw_text: str,
    *,
    labels: tuple[str, ...],
) -> datetime | None:
    """
    Busca una fecha/hora explícita asociada a una etiqueta concreta del SMS.
    """
    normalized_labels = tuple(label.strip().upper() for label in labels)

    for line in raw_text.splitlines():
        normalized_line = line.strip().upper()
        if not any(normalized_line.startswith(label) for label in normalized_labels):
            continue

        if ":" not in line:
            return None

        _, right_part = line.split(":", 1)
        return parse_incident_datetime(right_part)

    return None


def _parse_iso_datetime(value: str) -> datetime | None:
    iso_candidate = _ISO_DATETIME_SUFFIX_Z_PATTERN.sub("+00:00", value)

    try:
        parsed = datetime.fromisoformat(iso_candidate)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=_OPERATIONAL_TIMEZONE)

    return parsed
