"""
创建通知和玩家会话表
新增 notifications 表用于通知记录管理
新增 player_sessions 表用于存储玩家会话信息，支持主动消息推送

Revision ID: v007
Revises: v006
Create Date: 2026-05-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v007"
down_revision: str | Sequence[str] | None = "v006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notifications",
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
        sa.Column(
            "sender_id",
            sa.Text,
            nullable=True,
            server_default="system",
            comment="发送者ID",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="创建时间",
        ),
        sa.Column("sent_count", sa.Integer, server_default="0", comment="已发送数量"),
        sa.Column("fail_count", sa.Integer, server_default="0", comment="发送失败数量"),
        sa.Column(
            "status",
            sa.Text,
            server_default="pending",
            comment="状态: pending/sending/completed/failed",
        ),
    )

    op.create_table(
        "player_sessions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id", sa.Text, nullable=False, unique=True, comment="玩家用户ID"
        ),
        sa.Column(
            "unified_msg_origin",
            sa.Text,
            nullable=False,
            comment="统一消息来源标识(platform_id:message_type:session_id)",
        ),
        sa.Column("platform_name", sa.Text, nullable=True, comment="平台名称"),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="最后更新时间",
        ),
    )

    op.create_index(
        "ix_player_sessions_user_id", "player_sessions", ["user_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_player_sessions_user_id", table_name="player_sessions")
    op.drop_table("player_sessions")
    op.drop_table("notifications")
