"""drop deprecated incident columns

Revision ID: 1f7d3b2c4a5e
Revises: 96d6a6bc2491
Create Date: 2026-03-30 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1f7d3b2c4a5e"
down_revision: Union[str, Sequence[str], None] = "96d6a6bc2491"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("incident_cases", "pending_rca")

    op.drop_column("incident_events", "event_type")
    op.drop_column("incident_events", "team")
    op.drop_column("incident_events", "action_detected")
    op.drop_column("incident_events", "observation_detected")

    op.drop_column("troubleshooting_actions", "outcome")
    op.drop_column("troubleshooting_actions", "was_effective")


def downgrade() -> None:
    op.add_column(
        "troubleshooting_actions",
        sa.Column("was_effective", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "troubleshooting_actions",
        sa.Column("outcome", sa.String(length=64), nullable=True),
    )

    op.add_column(
        "incident_events",
        sa.Column("observation_detected", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "incident_events",
        sa.Column("action_detected", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "incident_events",
        sa.Column("team", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "incident_events",
        sa.Column("event_type", sa.String(length=32), nullable=True),
    )

    op.add_column(
        "incident_cases",
        sa.Column(
            "pending_rca",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.alter_column("incident_cases", "pending_rca", server_default=None)
