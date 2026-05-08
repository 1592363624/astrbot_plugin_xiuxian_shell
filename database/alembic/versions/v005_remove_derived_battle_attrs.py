"""
移除玩家表中的衍生战斗属性列
按照设计大纲，战斗属性由基础属性+境界等级动态计算，不再持久化到数据库
仅保留当前资源值（health, mp, stamina），移除 max_health, max_mp, max_stamina
以及 attack, magic_attack, defense, magic_defense, speed, dodge

Revision ID: v005
Revises: v004
Create Date: 2026-05-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v005"
down_revision: Union[str, Sequence[str], None] = "v004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("players") as batch_op:
        batch_op.drop_column("max_health")
        batch_op.drop_column("max_mp")
        batch_op.drop_column("max_stamina")
        batch_op.drop_column("attack")
        batch_op.drop_column("magic_attack")
        batch_op.drop_column("defense")
        batch_op.drop_column("magic_defense")
        batch_op.drop_column("speed")
        batch_op.drop_column("dodge")


def downgrade() -> None:
    with op.batch_alter_table("players") as batch_op:
        batch_op.add_column(sa.Column("max_health", sa.Integer, server_default="100"))
        batch_op.add_column(sa.Column("max_mp", sa.Integer, server_default="50"))
        batch_op.add_column(sa.Column("max_stamina", sa.Integer, server_default="50"))
        batch_op.add_column(sa.Column("attack", sa.Integer, server_default="10"))
        batch_op.add_column(sa.Column("magic_attack", sa.Integer, server_default="5"))
        batch_op.add_column(sa.Column("defense", sa.Integer, server_default="5"))
        batch_op.add_column(sa.Column("magic_defense", sa.Integer, server_default="2"))
        batch_op.add_column(sa.Column("speed", sa.Integer, server_default="10"))
        batch_op.add_column(sa.Column("dodge", sa.REAL, server_default="0"))
