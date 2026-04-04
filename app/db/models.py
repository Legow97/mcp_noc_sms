from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, Text, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pgvector.sqlalchemy import Vector


def utc_now() -> datetime:
    """
    Devuelve la fecha/hora actual en UTC.

    Se usa como factory para timestamps de creación y actualización.
    """
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """
    Clase base para todos los modelos ORM del proyecto.
    """

    pass


class IncidentCaseModel(Base):
    """
    Modelo ORM principal para incidentes.

    Mantiene una estructura híbrida:
    - columnas SQL para datos estables
    - JSONB para listas flexibles y metadatos
    - TEXT para contenido libre
    """

    __tablename__ = "incident_cases"

    case_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)

    header: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_text: Mapped[str] = mapped_column(Text, nullable=False)
    impact_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    solution_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")

    raw_sms: Mapped[str | None] = mapped_column(Text, nullable=True)
    probable_cause_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    component_types: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    components_affected: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    services_affected: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    symptoms: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    teams_involved: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    tickets: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    parser_output_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    enrichment_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )


class IncidentTimelineEntryModel(Base):
    """
    Modelo ORM para eventos del timeline de un incidente.

    Cada registro representa un hito extraído del bloque SOLUCIONADO
    o de una cronología operativa equivalente.
    """

    __tablename__ = "incident_events"

    event_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    case_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("incident_cases.case_id", ondelete="CASCADE"),
        nullable=False,
    )

    event_time: Mapped[str | None] = mapped_column(String(16), nullable=True)
    event_text: Mapped[str] = mapped_column(Text, nullable=False)

    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

class TroubleshootingActionModel(Base):
    """
    Modelo ORM para acciones de troubleshooting asociadas a un incidente.

    Cada registro representa una acción operativa identificada a partir
    de la bitácora/timeline del incidente.

    Importante:
    una acción registrada aquí no implica necesariamente que haya
    resuelto el incidente. Puede representar coordinación, monitoreo,
    derivación, remediación o cierre administrativo.
    """

    __tablename__ = "troubleshooting_actions"

    action_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    case_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("incident_cases.case_id", ondelete="CASCADE"),
        nullable=False,
    )

    action_text: Mapped[str] = mapped_column(Text, nullable=False)
    action_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_component: Mapped[str | None] = mapped_column(String(128), nullable=True)

    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )


class IncidentRetrievalDocumentModel(Base):
    """
    Índice persistente de documentos de retrieval por incidente y versión.

    Mantiene separado el dominio transaccional del material indexable
    para embeddings/reindexación futura.
    """

    __tablename__ = "incident_retrieval_documents"

    EMBEDDING_DIMENSIONS = 3072

    case_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("incident_cases.case_id", ondelete="CASCADE"),
        primary_key=True,
    )
    document_version: Mapped[str] = mapped_column(String(16), primary_key=True)

    document_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS),
        nullable=False,
        default=list,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
