"""add start_time to incident_cases

Revision ID: 96d6a6bc2491
Revises: dd2e9efc10e4
Create Date: 2026-03-29 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "96d6a6bc2491"
down_revision: Union[str, Sequence[str], None] = "dd2e9efc10e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "incident_cases",
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("incident_cases", "start_time")
