"""prevent duplicate CAS notifications

Revision ID: 0d5c012661e2
Revises: 4466d6888f91
Create Date: 2026-10-22 05:08:58.650519

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d5c012661e2'
down_revision: Union[str, Sequence[str], None] = '4466d6888f91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_index(
        "uq_notifications_new_resource_user_resource",
        "notifications",
        ["user_id", "resource_id"],
        unique=True,
        postgresql_where=sa.text(
            "notification_type = 'new_resource' "
            "AND resource_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_notifications_new_resource_user_resource",
        table_name="notifications",
    )

