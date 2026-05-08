"""
为 players 表添加封禁理由字段 ban_reason
支持记录封禁原因，便于管理和提示被封禁玩家

Revision ID: v011
Revises: v010
Create Date: 2026-05-09
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v011"
down_revision: Union[str, Sequence[str], None] = "v010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为 players 表添加 ban_reason 字段"""
    conn = op.get_bind()
    result = conn.execute(sa.text("PRAGMA table_info(players)"))
    columns = [row[1] for row in result]

    if "ban_reason" not in columns:
        with op.batch_alter_table("players") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "ban_reason",
                    sa.Text,
                    nullable=True,
                    comment="封禁理由，记录封禁原因便于管理和提示玩家",
                )
            )


def downgrade() -> None:
    """移除 players 表的 ban_reason 字段"""
    with op.batch_alter_table("players") as batch_op:
        batch_op.drop_column("ban_reason")
