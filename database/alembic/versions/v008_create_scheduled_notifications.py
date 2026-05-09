"""
创建定时通知表
新增 scheduled_notifications 表用于定时通知调度

Revision ID: v008
Revises: v007
Create Date: 2026-05-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v008"
down_revision: str | Sequence[str] | None = "v007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scheduled_notifications",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("title", sa.Text, nullable=False, comment="通知标题"),
        sa.Column("content", sa.Text, nullable=False, comment="通知内容"),
        sa.Column(
            "target_type",
            sa.Text,
            nullable=False,
            server_default="all",
            comment="目标类型: all/specific/realm",
        ),
        sa.Column("target_ids", sa.Text, nullable=True, comment="目标ID列表(JSON)"),
        sa.Column("template_id", sa.Text, nullable=True, comment="通知模板ID(可选)"),
        sa.Column(
            "template_variables", sa.Text, nullable=True, comment="模板变量(JSON)"
        ),
        sa.Column(
            "cron_expression",
            sa.Text,
            nullable=False,
            comment="Cron表达式(分 时 日 月 周)",
        ),
        sa.Column(
            "enabled",
            sa.Integer,
            nullable=False,
            server_default="1",
            comment="是否启用(1/0)",
        ),
        sa.Column("last_run_at", sa.TIMESTAMP, nullable=True, comment="上次执行时间"),
        sa.Column("next_run_at", sa.TIMESTAMP, nullable=True, comment="下次执行时间"),
        sa.Column("run_count", sa.Integer, server_default="0", comment="已执行次数"),
        sa.Column("created_by", sa.Text, server_default="system", comment="创建者ID"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="创建时间",
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="更新时间",
        ),
    )


def downgrade() -> None:
    op.drop_table("scheduled_notifications")
