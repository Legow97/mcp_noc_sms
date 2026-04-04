"""migrate retrieval embedding to pgvector

Revision ID: f2a1c9d4e5b6
Revises: 8c7d7f9a1b2c
Create Date: 2026-04-02 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f2a1c9d4e5b6"
down_revision: Union[str, Sequence[str], None] = "8c7d7f9a1b2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EMBEDDING_DIMENSIONS = 3072
EMBEDDING_INDEX_NAME = "ix_incident_retrieval_documents_embedding_halfvec_hnsw"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        f"""
        ALTER TABLE incident_retrieval_documents
        ALTER COLUMN embedding TYPE vector({EMBEDDING_DIMENSIONS})
        USING embedding::vector({EMBEDDING_DIMENSIONS})
        """
    )
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS {EMBEDDING_INDEX_NAME}
        ON incident_retrieval_documents
        USING hnsw ((embedding::halfvec({EMBEDDING_DIMENSIONS})) halfvec_cosine_ops)
        """
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {EMBEDDING_INDEX_NAME}")
    op.execute(
        """
        ALTER TABLE incident_retrieval_documents
        ALTER COLUMN embedding TYPE double precision[]
        USING embedding::double precision[]
        """
    )
