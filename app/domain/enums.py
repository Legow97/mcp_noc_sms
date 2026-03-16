from enum import StrEnum


class SourceType(StrEnum):
    """
    Tipos de fuente soportados por el sistema.

    En esta etapa inicial el foco principal será SMS de bitácora,
    pero dejamos abierto el diseño para futuras fuentes.
    """

    SMS_BITACORA = "sms_bitacora"
    MANUAL = "manual"
    BATCH_IMPORT = "batch_import"


class IncidentStatus(StrEnum):
    """
    Estados principales de un incidente dentro del sistema.
    """

    OPEN = "open"
    MONITORING = "monitoring"
    STABILIZED = "stabilized"
    CLOSED = "closed"

class IngestionStatus(StrEnum):
    ACCEPTED = "accepted"
    PROCESSED = "processed"
    FAILED = "failed"


class EventType(StrEnum):
    """
    Clasificación base de eventos del timeline de troubleshooting.
    """

    SYMPTOM = "symptom"
    OBSERVATION = "observation"
    ACTION = "action"
    ESCALATION = "escalation"
    DIAGNOSIS = "diagnosis"
    CLOSURE = "closure"
    MONITORING = "monitoring"