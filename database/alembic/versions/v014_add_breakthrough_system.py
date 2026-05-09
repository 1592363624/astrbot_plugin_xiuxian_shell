"""
新增防刷机制配置、突破条件系统、突破相关物品

- 防刷机制配置存入 death_penalty_configs
- realm_breakthrough_conditions: 境界突破条件表
- 插入突破相关物品（筑基丹、天火液等）

Revision ID: v014
Revises: v013
Create Date: 2026-05-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v014"
down_revision: str | Sequence[str] | None = "v013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """新增防刷配置、突破条件表、突破物品"""

    # 插入防刷机制配置
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
                "id": "dpc_009",
                "config_key": "passive_exp_cooldown_seconds",
                "config_value": "30",
                "description": "被动增长修为发言冷却时间(秒)",
            },
            {
                "id": "dpc_010",
                "config_key": "passive_exp_min_message_length",
                "config_value": "3",
                "description": "被动增长修为最小消息长度(字符)",
            },
            {
                "id": "dpc_011",
                "config_key": "passive_exp_daily_limit",
                "config_value": "200",
                "description": "被动增长修为每日上限",
            },
        ],
    )

    # 境界突破条件表
    op.create_table(
        "realm_breakthrough_conditions",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("realm_id", sa.Text, nullable=False, comment="目标境界ID"),
        sa.Column("realm_name", sa.Text, nullable=False, comment="目标境界名称"),
        sa.Column(
            "condition_type",
            sa.Text,
            nullable=False,
            comment="条件类型: auto自动/manual手动",
        ),
        sa.Column(
            "item_requirements",
            sa.Text,
            nullable=True,
            comment="物品需求(JSON格式: [{item_id, item_name, quantity}])",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="突破描述/提示",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="创建时间",
        ),
    )

    # 创建索引
    op.create_index(
        "idx_breakthrough_realm", "realm_breakthrough_conditions", ["realm_id"]
    )

    # 插入默认突破条件
    op.bulk_insert(
        sa.table(
            "realm_breakthrough_conditions",
            sa.column("id", sa.Text),
            sa.column("realm_id", sa.Text),
            sa.column("realm_name", sa.Text),
            sa.column("condition_type", sa.Text),
            sa.column("item_requirements", sa.Text),
            sa.column("description", sa.Text),
        ),
        [
            {
                "id": "btc_001",
                "realm_id": "realm_004",
                "realm_name": "筑基期",
                "condition_type": "auto",
                "item_requirements": '[{"item_id":"item_zhuji_dan","item_name":"筑基丹","quantity":1}]',
                "description": "突破筑基期需要服用筑基丹",
            },
            {
                "id": "btc_002",
                "realm_id": "realm_007",
                "realm_name": "结丹期",
                "condition_type": "manual",
                "item_requirements": '[{"item_id":"item_tianhuo_ye","item_name":"天火液","quantity":1},{"item_id":"item_ninghun_dan","item_name":"凝魂丹","quantity":1},{"item_id":"item_sanzhuan_dan","item_name":"三转重元丹","quantity":1}]',
                "description": "结丹之劫：集齐天火液、凝魂丹、三转重元丹，方可冲击结丹",
            },
            {
                "id": "btc_003",
                "realm_id": "realm_010",
                "realm_name": "元婴期",
                "condition_type": "manual",
                "item_requirements": '[{"item_id":"item_yanghun_mu","item_name":"养魂木","quantity":25},{"item_id":"item_jiuqu_dan","item_name":"九曲灵参丹","quantity":1},{"item_id":"item_qingluan_dun","item_name":"青鸾天盾","quantity":1}]',
                "description": "元婴之劫：集齐养魂木x25、九曲灵参丹、青鸾天盾，方可冲击元婴",
            },
        ],
    )

    # 插入突破相关物品
    op.bulk_insert(
        sa.table(
            "items",
            sa.column("id", sa.Text),
            sa.column("name", sa.Text),
            sa.column("description", sa.Text),
            sa.column("item_type", sa.Text),
            sa.column("rarity", sa.Text),
            sa.column("effect_type", sa.Text),
            sa.column("effect_value", sa.Integer),
            sa.column("price", sa.Integer),
            sa.column("is_usable", sa.Integer),
        ),
        [
            {
                "id": "item_zhuji_dan",
                "name": "筑基丹",
                "description": "筑基期突破必备丹药，可稳固根基，助修士突破至筑基期",
                "item_type": "material",
                "rarity": "rare",
                "effect_type": "breakthrough",
                "effect_value": 0,
                "price": 500,
                "is_usable": 0,
            },
            {
                "id": "item_tianhuo_ye",
                "name": "天火液",
                "description": "天地灵火凝聚而成的液体，结丹之劫必备至宝",
                "item_type": "material",
                "rarity": "epic",
                "effect_type": "breakthrough",
                "effect_value": 0,
                "price": 2000,
                "is_usable": 0,
            },
            {
                "id": "item_ninghun_dan",
                "name": "凝魂丹",
                "description": "凝聚神魂的丹药，可稳固神识，结丹之劫必备",
                "item_type": "material",
                "rarity": "epic",
                "effect_type": "breakthrough",
                "effect_value": 0,
                "price": 2000,
                "is_usable": 0,
            },
            {
                "id": "item_sanzhuan_dan",
                "name": "三转重元丹",
                "description": "经历三次转炼的丹药，可重塑元气，结丹之劫必备",
                "item_type": "material",
                "rarity": "epic",
                "effect_type": "breakthrough",
                "effect_value": 0,
                "price": 2000,
                "is_usable": 0,
            },
            {
                "id": "item_yanghun_mu",
                "name": "养魂木",
                "description": "滋养神魂的灵木，元婴之劫需要25根",
                "item_type": "material",
                "rarity": "epic",
                "effect_type": "breakthrough",
                "effect_value": 0,
                "price": 500,
                "is_usable": 0,
            },
            {
                "id": "item_jiuqu_dan",
                "name": "九曲灵参丹",
                "description": "以九曲灵参为主材炼制的丹药，元婴之劫必备",
                "item_type": "material",
                "rarity": "legendary",
                "effect_type": "breakthrough",
                "effect_value": 0,
                "price": 5000,
                "is_usable": 0,
            },
            {
                "id": "item_qingluan_dun",
                "name": "青鸾天盾",
                "description": "以青鸾羽毛炼制的防御法宝，可抵挡元婴雷劫",
                "item_type": "equipment",
                "rarity": "legendary",
                "effect_type": "breakthrough",
                "effect_value": 0,
                "price": 8000,
                "is_usable": 0,
            },
        ],
    )


def downgrade() -> None:
    """回滚：删除新增表、配置和物品"""
    # 删除突破条件表
    op.drop_index("idx_breakthrough_realm", table_name="realm_breakthrough_conditions")
    op.drop_table("realm_breakthrough_conditions")

    # 删除防刷配置
    op.execute(
        "DELETE FROM death_penalty_configs WHERE config_key IN ('passive_exp_cooldown_seconds', 'passive_exp_min_message_length', 'passive_exp_daily_limit')"
    )

    # 删除突破相关物品
    op.execute(
        """DELETE FROM items WHERE id IN (
            'item_zhuji_dan', 'item_tianhuo_ye', 'item_ninghun_dan',
            'item_sanzhuan_dan', 'item_yanghun_mu', 'item_jiuqu_dan', 'item_qingluan_dun'
        )"""
    )
