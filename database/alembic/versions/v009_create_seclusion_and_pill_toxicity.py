"""
创建闭关记录表和丹毒记录表
新增 seclusion_records 表用于闭关修炼记录
新增 pill_toxicity_records 表用于丹毒累积记录
为 items 表添加 realm_requirement 字段用于丹药境界限制

Revision ID: v009
Revises: v008
Create Date: 2026-05-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v009"
down_revision: Union[str, Sequence[str], None] = "v008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "seclusion_records",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("player_id", sa.Text, nullable=False, comment="玩家ID"),
        sa.Column("result", sa.Text, nullable=False, comment="闭关结果: success/failure/possession"),
        sa.Column("exp_change", sa.Integer, nullable=False, server_default="0", comment="修为变化(正数增加,负数减少)"),
        sa.Column("encounter_event_id", sa.Text, nullable=True, comment="触发的奇遇事件ID"),
        sa.Column("cooldown_minutes", sa.Integer, nullable=False, server_default="0", comment="本次闭关冷却时长(分钟)"),
        sa.Column("started_at", sa.TIMESTAMP, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="闭关开始时间"),
        sa.Column("cooldown_until", sa.TIMESTAMP, nullable=True, comment="冷却结束时间"),
        sa.Column("created_at", sa.TIMESTAMP, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
    )

    op.create_table(
        "pill_toxicity_records",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("player_id", sa.Text, nullable=False, comment="玩家ID"),
        sa.Column("item_id", sa.Text, nullable=False, comment="丹药物品ID"),
        sa.Column("item_name", sa.Text, nullable=False, comment="丹药名称"),
        sa.Column("toxicity_value", sa.Integer, nullable=False, server_default="1", comment="丹毒值"),
        sa.Column("taken_at", sa.TIMESTAMP, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="服用时间"),
        sa.Column("expires_at", sa.TIMESTAMP, nullable=False, comment="丹毒消解时间(24小时后)"),
        sa.Column("created_at", sa.TIMESTAMP, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
    )

    with op.batch_alter_table("items") as batch_op:
        batch_op.add_column(
            sa.Column("realm_requirement", sa.Text, nullable=True, comment="使用所需最低境界ID")
        )


def downgrade() -> None:
    op.drop_table("pill_toxicity_records")
    op.drop_table("seclusion_records")

    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_column("realm_requirement")
