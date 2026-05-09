"""
万宝楼系统 - 市场挂单表

创建 market_listings 表用于存储所有挂单商品
支持按件出售和捆绑出售两种模式

Revision ID: v015
Revises: v014
Create Date: 2026-05-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v015"
down_revision: str | Sequence[str] | None = "v014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建万宝楼挂单表"""
    op.create_table(
        "market_listings",
        sa.Column("id", sa.Text, primary_key=True, comment="挂单ID"),
        sa.Column(
            "seller_id",
            sa.Text,
            nullable=False,
            index=True,
            comment="卖家玩家ID",
        ),
        sa.Column(
            "seller_name",
            sa.Text,
            nullable=False,
            comment="卖家道号(冗余便于展示)",
        ),
        sa.Column(
            "item_id",
            sa.Text,
            nullable=False,
            comment="上架物品ID",
        ),
        sa.Column(
            "item_name",
            sa.Text,
            nullable=False,
            comment="物品名称(冗余便于展示)",
        ),
        sa.Column(
            "item_type",
            sa.Text,
            nullable=False,
            comment="物品类型: 丹药/法宝/材料/图纸/种子",
        ),
        sa.Column(
            "quantity",
            sa.Integer,
            nullable=False,
            comment="上架数量",
        ),
        sa.Column(
            "remaining_quantity",
            sa.Integer,
            nullable=False,
            comment="剩余数量",
        ),
        sa.Column(
            "total_price",
            sa.Text,
            nullable=False,
            comment="总价(JSON格式: [{item_id, item_name, quantity}])",
        ),
        sa.Column(
            "is_bundled",
            sa.Boolean,
            nullable=False,
            server_default="0",
            comment="是否为捆绑出售(0否,1是)",
        ),
        sa.Column(
            "unit_price",
            sa.Text,
            nullable=True,
            comment="单价JSON(仅按件出售时有): [{item_id, item_name, unit_quantity}]",
        ),
        sa.Column(
            "status",
            sa.Text,
            nullable=False,
            server_default="active",
            comment="挂单状态: active进行中/completed已完成/cancelled已取消",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="创建时间/上架时间",
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP,
            nullable=True,
            comment="更新时间",
        ),
    )

    op.create_index("idx_market_status", "market_listings", ["status"])
    op.create_index("idx_market_item_type", "market_listings", ["item_type"])
    op.create_index("idx_market_item_name", "market_listings", ["item_name"])
    op.create_index("idx_market_seller", "market_listings", ["seller_id"])


def downgrade() -> None:
    """删除万宝楼挂单表"""
    op.drop_table("market_listings")
