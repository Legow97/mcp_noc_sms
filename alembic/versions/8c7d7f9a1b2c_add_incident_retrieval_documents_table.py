"""add incident retrieval documents table

Revision ID: 8c7d7f9a1b2c
Revises: 1f7d3b2c4a5e
Create Date: 2026-04-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "8c7d7f9a1b2c"
down_revision: Union[str, Sequence[str], None] = "1f7d3b2c4a5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incident_retrieval_documents",
        sa.Column("case_id", sa.String(length=32), nullable=False),
        sa.Column("document_version", sa.String(length=16), nullable=False),
        sa.Column("document_text", sa.Text(), nullable=False),
        sa.Column(
            "embedding",
            postgresql.ARRAY(sa.Float(asdecimal=False)),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["incident_cases.case_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("case_id", "document_version"),
    )
    op.create_index(
        "ix_incident_retrieval_documents_case_id",
        "incident_retrieval_documents",
        ["case_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_incident_retrieval_documents_case_id",
        table_name="incident_retrieval_documents",
    )
    op.drop_table("incident_retrieval_documents")
