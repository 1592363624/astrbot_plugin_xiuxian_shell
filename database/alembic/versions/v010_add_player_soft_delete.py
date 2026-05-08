"""
为 players 表添加软删除标记字段 is_deleted
支持封禁/解封玩家功能，不真正删除数据

Revision ID: v010
Revises: v009
Create Date: 2026-05-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v010"
down_revision: Union[str, Sequence[str], None] = "v009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为 players 表添加 is_deleted 字段"""
    conn = op.get_bind()
    result = conn.execute(sa.text("PRAGMA table_info(players)"))
    columns = [row[1] for row in result]

    if "is_deleted" not in columns:
        with op.batch_alter_table("players") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "is_deleted",
                    sa.Integer,
                    nullable=False,
                    server_default="0",
                    comment="软删除标记: 0=正常, 1=已封禁",
                )
            )


def downgrade() -> None:
    """移除 players 表的 is_deleted 字段"""
    with op.batch_alter_table("players") as batch_op:
        batch_op.drop_column("is_deleted")
