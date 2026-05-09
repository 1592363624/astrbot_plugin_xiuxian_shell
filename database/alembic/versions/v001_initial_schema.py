"""
初始数据库结构迁移
创建游戏核心表结构

Revision ID: v001
Revises:
Create Date: 2026-05-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建初始表结构"""
    # 玩家表
    op.create_table(
        "players",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("user_id", sa.Text, nullable=False, unique=True),
        sa.Column("username", sa.Text, nullable=False),
        sa.Column("realm_id", sa.Text, server_default="realm_001"),
        sa.Column("experience", sa.Integer, server_default="0"),
        sa.Column("spirit_stone", sa.Integer, server_default="100"),
        sa.Column("health", sa.Integer, server_default="100"),
        sa.Column("max_health", sa.Integer, server_default="100"),
        sa.Column("attack", sa.Integer, server_default="10"),
        sa.Column("defense", sa.Integer, server_default="5"),
        sa.Column(
            "created_at", sa.TIMESTAMP, server_default=sa.func.current_timestamp()
        ),
        sa.Column(
            "updated_at", sa.TIMESTAMP, server_default=sa.func.current_timestamp()
        ),
    )

    # 物品表
    op.create_table(
        "items",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("description", sa.Text),
        sa.Column("item_type", sa.Text, nullable=False),
        sa.Column("rarity", sa.Text, server_default="common"),
        sa.Column("effect_type", sa.Text),
        sa.Column("effect_value", sa.Integer, server_default="0"),
        sa.Column("price", sa.Integer, server_default="0"),
        sa.Column("is_usable", sa.Integer, server_default="1"),
        sa.Column(
            "created_at", sa.TIMESTAMP, server_default=sa.func.current_timestamp()
        ),
    )

    # 玩家背包表
    op.create_table(
        "player_inventory",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("player_id", sa.Text, nullable=False),
        sa.Column("item_id", sa.Text, nullable=False),
        sa.Column("quantity", sa.Integer, server_default="1"),
        sa.Column("equipped", sa.Integer, server_default="0"),
        sa.Column(
            "created_at", sa.TIMESTAMP, server_default=sa.func.current_timestamp()
        ),
        sa.UniqueConstraint("player_id", "item_id"),
    )

    # 功法表
    op.create_table(
        "skills",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("description", sa.Text),
        sa.Column("skill_type", sa.Text, nullable=False),
        sa.Column("realm_requirement", sa.Text),
        sa.Column("experience_gain", sa.Integer, server_default="10"),
        sa.Column("damage", sa.Integer, server_default="0"),
        sa.Column("cooldown", sa.Integer, server_default="0"),
        sa.Column(
            "created_at", sa.TIMESTAMP, server_default=sa.func.current_timestamp()
        ),
    )

    # 玩家功法表
    op.create_table(
        "player_skills",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("player_id", sa.Text, nullable=False),
        sa.Column("skill_id", sa.Text, nullable=False),
        sa.Column("level", sa.Integer, server_default="1"),
        sa.Column("experience", sa.Integer, server_default="0"),
        sa.Column(
            "created_at", sa.TIMESTAMP, server_default=sa.func.current_timestamp()
        ),
        sa.UniqueConstraint("player_id", "skill_id"),
    )

    # 境界表
    op.create_table(
        "realms",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False, unique=True),
        sa.Column("description", sa.Text),
        sa.Column("level", sa.Integer, nullable=False),
        sa.Column("experience_required", sa.Integer, nullable=False),
        sa.Column("health_bonus", sa.Integer, server_default="0"),
        sa.Column("attack_bonus", sa.Integer, server_default="0"),
        sa.Column("defense_bonus", sa.Integer, server_default="0"),
        sa.Column(
            "created_at", sa.TIMESTAMP, server_default=sa.func.current_timestamp()
        ),
    )

    # 游戏事件表
    op.create_table(
        "game_events",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("trigger_condition", sa.Text),
        sa.Column("reward_type", sa.Text),
        sa.Column("reward_value", sa.Integer, server_default="0"),
        sa.Column("probability", sa.REAL, server_default="0.5"),
        sa.Column("is_active", sa.Integer, server_default="1"),
        sa.Column(
            "created_at", sa.TIMESTAMP, server_default=sa.func.current_timestamp()
        ),
    )

    # 玩家事件记录表
    op.create_table(
        "player_events",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("player_id", sa.Text, nullable=False),
        sa.Column("event_id", sa.Text, nullable=False),
        sa.Column(
            "triggered_at", sa.TIMESTAMP, server_default=sa.func.current_timestamp()
        ),
    )


def downgrade() -> None:
    """回滚初始表结构"""
    tables = [
        "player_events",
        "game_events",
        "player_skills",
        "skills",
        "player_inventory",
        "items",
        "players",
        "realms",
    ]
    for table in tables:
        op.drop_table(table)
