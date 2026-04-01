from __future__ import annotations

from pydantic import BaseModel, Field


class CanonicalTimelineEntryData(BaseModel):
    """
    Entrada cronológica canónica del incidente.

    No es ORM ni DTO HTTP. Es un contrato intermedio del subsistema agentic.
    """

    event_time: str | None = None
    event_text: str = Field(..., min_length=1)
    sequence_order: int = Field(..., ge=1)


class CanonicalTroubleshootingActionData(BaseModel):
    """
    Acción operativa canónica derivada del incidente.
    """

    action_text: str = Field(..., min_length=1)
    action_type: str | None = None
    action_role: str | None = None
    target_component: str | None = None
    sequence_order: int = Field(..., ge=1)


class CanonicalIncidentCaseData(BaseModel):
    """
    Núcleo canónico del incidente extraído desde el SMS/documento.
    """

    case_id: str | None = None
    source_type: str = Field(..., min_length=1)
    header: str | None = None
    failure_text: str = Field(..., min_length=1)
    impact_text: str | None = None
    start_time: str | None = None
    solution_time: str | None = None
    incident_status: str = Field(..., min_length=1)
    raw_sms: str = Field(..., min_length=1)

    probable_cause_text: str | None = None
    resolution_summary: str | None = None

    component_types: list[str] = Field(default_factory=list)
    components_affected: list[str] = Field(default_factory=list)
    services_affected: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)
    teams_involved: list[str] = Field(default_factory=list)
    tickets: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class CanonicalExtractionMetadata(BaseModel):
    """
    Metadatos de la extracción producida por el subsistema agentic.

    Esta metadata debe representar:
    - quién produjo la extracción (rol lógico)
    - qué versión lógica del extractor/prompt se usó
    - qué modelo LLM participó
    - notas de confianza y advertencias
    - campos faltantes o inferidos

    No debe exponer rutas internas ni detalles innecesarios del rulebook.
    """

    extractor_name: str = Field(..., min_length=1)
    extractor_version: str = Field(..., min_length=1)
    model_name: str | None = None
    confidence_notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    inferred_fields: list[str] = Field(default_factory=list)


class CanonicalExtractionResult(BaseModel):
    """
    Resultado canónico completo del proceso de extracción.

    Este es el contrato raíz que debe producir el extractor principal,
    revisar el juez y reconstruir el fallback.
    """

    incident_case: CanonicalIncidentCaseData
    timeline_entries: list[CanonicalTimelineEntryData] = Field(default_factory=list)
    troubleshooting_actions: list[CanonicalTroubleshootingActionData] = Field(
        default_factory=list
    )
    extraction_metadata: CanonicalExtractionMetadata
