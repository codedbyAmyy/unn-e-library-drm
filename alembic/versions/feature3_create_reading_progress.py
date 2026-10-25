
"""Create reading progress table."""

from alembic import op
import sqlalchemy as sa

revision = "feature3_progress"
down_revision = "976f649a5a4b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reading_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "resource_id",
            sa.Integer(),
            sa.ForeignKey("resources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("current_page", sa.Integer(), nullable=False),
        sa.Column("total_pages", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id",
            "resource_id",
            name="uq_reading_progress_user_resource",
        ),
    )

    op.create_index(
        "ix_reading_progress_user_id",
        "reading_progress",
        ["user_id"],
    )
    op.create_index(
        "ix_reading_progress_resource_id",
        "reading_progress",
        ["resource_id"],
    )


def downgrade():
    op.drop_index(
        "ix_reading_progress_resource_id",
        table_name="reading_progress",
    )
    op.drop_index(
        "ix_reading_progress_user_id",
        table_name="reading_progress",
    )
    op.drop_table("reading_progress")
