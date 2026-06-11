"""
移除物品表的稀有度(rarity)列

物品稀有度属性已废弃，不再使用。
从 items 表中删除 rarity 列。

Revision ID: v018
Revises: v017
Create Date: 2026-05-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v018"
down_revision: str | Sequence[str] | None = "v017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """删除 items 表的 rarity 列"""
    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_column("rarity")


def downgrade() -> None:
    """恢复 items 表的 rarity 列"""
    with op.batch_alter_table("items") as batch_op:
        batch_op.add_column(
            sa.Column("rarity", sa.Text, server_default="common")
        )
