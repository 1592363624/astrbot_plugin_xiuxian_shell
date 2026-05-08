"""
创建签到记录表
支持每日签到、连续签到天数追踪和修为奖励记录

Revision ID: v003
Revises: v002
Create Date: 2026-05-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v003"
down_revision: Union[str, Sequence[str], None] = "v002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建签到记录表"""
    op.create_table(
        "checkin_records",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("player_id", sa.Text, nullable=False),
        sa.Column("checkin_date", sa.Text, nullable=False),
        sa.Column("consecutive_days", sa.Integer, server_default="1"),
        sa.Column("exp_reward", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP, server_default=sa.func.current_timestamp()),
        sa.UniqueConstraint("player_id", "checkin_date"),
    )
    # 为按玩家查询签到记录创建索引
    op.create_index("ix_checkin_player_date", "checkin_records", ["player_id", "checkin_date"])


def downgrade() -> None:
    """回滚签到记录表"""
    op.drop_index("ix_checkin_player_date", table_name="checkin_records")
    op.drop_table("checkin_records")
