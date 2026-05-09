"""
新增发言日志表和临时修为字段

- chat_logs: 玩家发言日志表
- players.temp_experience: 临时存储的修为（超过境界上限部分）
- players.last_breakthrough_prompt: 上次突破提示时间

Revision ID: v013
Revises: v012
Create Date: 2026-05-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "v013"
down_revision: str | Sequence[str] | None = "v012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """新增发言日志表和玩家临时修为字段"""

    # 发言日志表
    op.create_table(
        "chat_logs",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("player_id", sa.Text, nullable=False, comment="玩家ID"),
        sa.Column("user_id", sa.Text, nullable=False, comment="用户ID"),
        sa.Column("username", sa.Text, nullable=False, comment="玩家道号"),
        sa.Column("realm_name", sa.Text, nullable=True, comment="发言时境界"),
        sa.Column("experience", sa.Integer, nullable=True, comment="发言时修为"),
        sa.Column("message_content", sa.Text, nullable=False, comment="发言内容"),
        sa.Column("group_id", sa.Text, nullable=True, comment="群组ID"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            comment="发言时间",
        ),
    )

    # 创建索引
    op.create_index("idx_chat_logs_player", "chat_logs", ["player_id"])
    op.create_index("idx_chat_logs_created", "chat_logs", ["created_at"])
    op.create_index("idx_chat_logs_user", "chat_logs", ["user_id"])

    # 玩家表添加临时修为字段
    conn = op.get_bind()
    result = conn.execute(sa.text("PRAGMA table_info(players)"))
    columns = [row[1] for row in result]

    if "temp_experience" not in columns:
        with op.batch_alter_table("players") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "temp_experience",
                    sa.Integer,
                    nullable=False,
                    server_default="0",
                    comment="临时存储的修为（超过境界上限部分）",
                )
            )

    if "last_breakthrough_prompt" not in columns:
        with op.batch_alter_table("players") as batch_op:
            batch_op.add_column(
                sa.Column(
                    "last_breakthrough_prompt",
                    sa.TIMESTAMP,
                    nullable=True,
                    comment="上次突破提示时间",
                )
            )

    # 插入被动增长修为配置
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
                "id": "dpc_008",
                "config_key": "passive_exp_per_message",
                "config_value": "10",
                "description": "每次有效发言增加的修为点数",
            },
        ],
    )


def downgrade() -> None:
    """回滚：删除新增表和字段"""
    op.drop_index("idx_chat_logs_user", table_name="chat_logs")
    op.drop_index("idx_chat_logs_created", table_name="chat_logs")
    op.drop_index("idx_chat_logs_player", table_name="chat_logs")
    op.drop_table("chat_logs")

    with op.batch_alter_table("players") as batch_op:
        batch_op.drop_column("last_breakthrough_prompt")
        batch_op.drop_column("temp_experience")

    op.execute(
        "DELETE FROM death_penalty_configs WHERE config_key = 'passive_exp_per_message'"
    )
