"""
移除境界表的三个bonus字段，为玩家表添加基础属性和扩展战斗属性
根据设计大纲，战斗属性改为通过公式动态计算，不再存储在境界表中

Revision ID: v004
Revises: v003
Create Date: 2026-05-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v004"
down_revision: Union[str, Sequence[str], None] = "v003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """移除境界bonus字段，添加玩家基础属性和扩展战斗属性"""
    # SQLite不支持直接DROP COLUMN，使用batch_alter_table重建表
    with op.batch_alter_table("realms") as batch_op:
        batch_op.drop_column("health_bonus")
        batch_op.drop_column("attack_bonus")
        batch_op.drop_column("defense_bonus")

    # 为玩家表添加基础属性（先天属性）
    with op.batch_alter_table("players") as batch_op:
        # 基础属性（先天属性）
        batch_op.add_column(sa.Column("bone", sa.Integer, server_default="5"))
        batch_op.add_column(sa.Column("spirit", sa.Integer, server_default="5"))
        batch_op.add_column(sa.Column("intel", sa.Integer, server_default="5"))
        batch_op.add_column(sa.Column("str", sa.Integer, server_default="5"))
        batch_op.add_column(sa.Column("percep", sa.Integer, server_default="5"))
        batch_op.add_column(sa.Column("luck", sa.Integer, server_default="1"))
        # 扩展战斗属性（衍生属性，由公式计算后缓存）
        batch_op.add_column(sa.Column("mp", sa.Integer, server_default="50"))
        batch_op.add_column(sa.Column("max_mp", sa.Integer, server_default="50"))
        batch_op.add_column(sa.Column("stamina", sa.Integer, server_default="50"))
        batch_op.add_column(sa.Column("max_stamina", sa.Integer, server_default="50"))
        batch_op.add_column(sa.Column("magic_attack", sa.Integer, server_default="5"))
        batch_op.add_column(sa.Column("magic_defense", sa.Integer, server_default="2"))
        batch_op.add_column(sa.Column("speed", sa.Integer, server_default="10"))
        batch_op.add_column(sa.Column("dodge", sa.REAL, server_default="0"))


def downgrade() -> None:
    """回滚：恢复境界bonus字段，移除玩家基础属性"""
    # 移除玩家表新增字段
    with op.batch_alter_table("players") as batch_op:
        batch_op.drop_column("dodge")
        batch_op.drop_column("speed")
        batch_op.drop_column("magic_defense")
        batch_op.drop_column("magic_attack")
        batch_op.drop_column("max_stamina")
        batch_op.drop_column("stamina")
        batch_op.drop_column("max_mp")
        batch_op.drop_column("mp")
        batch_op.drop_column("luck")
        batch_op.drop_column("percep")
        batch_op.drop_column("str")
        batch_op.drop_column("intel")
        batch_op.drop_column("spirit")
        batch_op.drop_column("bone")

    # 恢复境界表bonus字段
    with op.batch_alter_table("realms") as batch_op:
        batch_op.add_column(sa.Column("defense_bonus", sa.Integer, server_default="0"))
        batch_op.add_column(sa.Column("attack_bonus", sa.Integer, server_default="0"))
        batch_op.add_column(sa.Column("health_bonus", sa.Integer, server_default="0"))
