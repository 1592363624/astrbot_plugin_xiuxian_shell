"""
后天属性默认值改为0
属性从先天随机分配改为后天积累，初始全部为0
同时将已有玩家的属性值重置为0

Revision ID: v006
Revises: v005
Create Date: 2026-05-08
"""

from collections.abc import Sequence

from alembic import op

revision: str = "v006"
down_revision: str | Sequence[str] | None = "v005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("players") as batch_op:
        batch_op.alter_column("bone", server_default="0")
        batch_op.alter_column("spirit", server_default="0")
        batch_op.alter_column("intel", server_default="0")
        batch_op.alter_column("str", server_default="0")
        batch_op.alter_column("percep", server_default="0")
        batch_op.alter_column("luck", server_default="0")

    op.execute(
        "UPDATE players SET bone = 0, spirit = 0, intel = 0, str = 0, percep = 0, luck = 0"
    )


def downgrade() -> None:
    with op.batch_alter_table("players") as batch_op:
        batch_op.alter_column("bone", server_default="5")
        batch_op.alter_column("spirit", server_default="5")
        batch_op.alter_column("intel", server_default="5")
        batch_op.alter_column("str", server_default="5")
        batch_op.alter_column("percep", server_default="5")
        batch_op.alter_column("luck", server_default="1")
