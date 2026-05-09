"""
新增深度闭关、避世入世、死亡惩罚相关表结构

- deep_seclusion_records: 深度闭关记录表
- player_states: 玩家状态表（道心破碎、避世等）
- death_penalty_configs: 死亡惩罚配置表

Revision ID: v012
Revises: v011
Create Date: 2026-05-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v012"
down_revision: str | Sequence[str] | None = "v011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """新增深度闭关、玩家状态、死亡惩罚配置表"""

    # 深度闭关记录表
    op.create_table(
        "deep_seclusion_records",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("player_id", sa.Text, nullable=False, comment="玩家ID"),
        sa.Column(
            "status",
            sa.Text,
            nullable=False,
            server_default="ongoing",
            comment="状态: ongoing进行中/completed已完成/early_ended强行出关",
        ),
        sa.Column("started_at", sa.TIMESTAMP, nullable=False, comment="闭关开始时间"),
        sa.Column("ended_at", sa.TIMESTAMP, nullable=True, comment="闭关结束时间"),
        sa.Column(
            "planned_duration_hours",
            sa.Integer,
            nullable=False,
            server_default="8",
            comment="计划闭关时长(小时)",
        ),
        sa.Column(
            "total_cycles",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="神魂吐纳总次数",
        ),
        sa.Column(
            "success_count",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="修行有成次数",
        ),
        sa.Column(
            "failure_count",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="心神不宁次数",
        ),
        sa.Column(
            "possession_count",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="走火入魔次数",
        ),
        sa.Column(
            "total_exp_change",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="修为总变化",
        ),
        sa.Column(
            "is_settled",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="是否已结算: 0未结算/1已结算",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="创建时间",
        ),
    )

    # 玩家状态表（道心破碎、避世等）
    op.create_table(
        "player_states",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("player_id", sa.Text, nullable=False, comment="玩家ID"),
        sa.Column(
            "state_type",
            sa.Text,
            nullable=False,
            comment="状态类型: dao_heart_broken道心破碎/peace_mode避世等",
        ),
        sa.Column("started_at", sa.TIMESTAMP, nullable=False, comment="状态开始时间"),
        sa.Column("expires_at", sa.TIMESTAMP, nullable=True, comment="状态过期时间"),
        sa.Column(
            "is_active",
            sa.Integer,
            nullable=False,
            server_default="1",
            comment="是否生效: 0失效/1生效",
        ),
        sa.Column("metadata", sa.Text, nullable=True, comment="额外元数据(JSON格式)"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="创建时间",
        ),
    )

    # 死亡惩罚配置表
    op.create_table(
        "death_penalty_configs",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column(
            "config_key", sa.Text, nullable=False, unique=True, comment="配置键名"
        ),
        sa.Column("config_value", sa.Text, nullable=False, comment="配置值"),
        sa.Column("description", sa.Text, nullable=True, comment="配置说明"),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="更新时间",
        ),
    )

    # 插入默认死亡惩罚配置
    op.bulk_insert(
        sa.table(
            "death_penalty_configs",
            sa.column("id", sa.Text),
            sa.column("config_key", sa.Text),
            sa.column("config_value", sa.Text),
            sa.column("description", sa.Text),
        ),
        [
            {
                "id": "dpc_001",
                "config_key": "material_drop_rate",
                "config_value": "0.5",
                "description": "死亡时材料掉落比例(50%)",
            },
            {
                "id": "dpc_002",
                "config_key": "equipment_drop_count",
                "config_value": "1",
                "description": "死亡时随机掉落装备数量",
            },
            {
                "id": "dpc_003",
                "config_key": "dao_heart_broken_duration_hours",
                "config_value": "24",
                "description": "道心破碎状态持续时间(小时)",
            },
            {
                "id": "dpc_004",
                "config_key": "dao_heart_exp_penalty_rate",
                "config_value": "0.5",
                "description": "道心破碎期间闭关收益减半比例",
            },
            {
                "id": "dpc_005",
                "config_key": "deep_seclusion_cooldown_hours",
                "config_value": "22",
                "description": "深度闭关冷却时间(小时)",
            },
            {
                "id": "dpc_006",
                "config_key": "deep_seclusion_duration_hours",
                "config_value": "8",
                "description": "深度闭关持续时长(小时)",
            },
            {
                "id": "dpc_007",
                "config_key": "deep_seclusion_early_end_penalty_rate",
                "config_value": "0.5",
                "description": "强行出关收益折扣比例",
            },
        ],
    )

    # 创建索引
    op.create_index(
        "idx_deep_seclusion_player", "deep_seclusion_records", ["player_id"]
    )
    op.create_index("idx_deep_seclusion_status", "deep_seclusion_records", ["status"])
    op.create_index("idx_player_states_player", "player_states", ["player_id"])
    op.create_index("idx_player_states_type", "player_states", ["state_type"])


def downgrade() -> None:
    """回滚：删除新增表"""
    op.drop_index("idx_player_states_type", table_name="player_states")
    op.drop_index("idx_player_states_player", table_name="player_states")
    op.drop_index("idx_deep_seclusion_status", table_name="deep_seclusion_records")
    op.drop_index("idx_deep_seclusion_player", table_name="deep_seclusion_records")

    op.drop_table("death_penalty_configs")
    op.drop_table("player_states")
    op.drop_table("deep_seclusion_records")
