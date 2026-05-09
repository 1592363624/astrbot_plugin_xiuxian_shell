"""
临时增益效果表

创建 temp_buffs 表用于存储玩家的临时增益效果
支持突破成功率加成、临时属性加成等

Revision ID: v016
Revises: v015
Create Date: 2026-05-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v016"
down_revision: str | Sequence[str] | None = "v015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建临时增益效果表"""
    op.create_table(
        "temp_buffs",
        sa.Column("id", sa.Text, primary_key=True, comment="记录ID"),
        sa.Column(
            "player_id",
            sa.Text,
            nullable=False,
            index=True,
            comment="玩家ID",
        ),
        sa.Column(
            "buff_type",
            sa.Text,
            nullable=False,
            comment="增益类型: breakthrough_rate/temp_attack/temp_defense等",
        ),
        sa.Column(
            "buff_value",
            sa.Integer,
            nullable=False,
            comment="增益数值",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="创建时间",
        ),
        sa.Column(
            "expires_at",
            sa.TIMESTAMP,
            nullable=False,
            comment="过期时间",
        ),
    )

    op.create_index("idx_temp_buffs_player", "temp_buffs", ["player_id"])
    op.create_index("idx_temp_buffs_type", "temp_buffs", ["buff_type"])
    op.create_index("idx_temp_buffs_expires", "temp_buffs", ["expires_at"])


def downgrade() -> None:
    """删除临时增益效果表"""
    op.drop_table("temp_buffs")
