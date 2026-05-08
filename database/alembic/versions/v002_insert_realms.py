"""
添加境界扩展字段并插入境界数据
根据设计大纲创建完整的修仙境界体系

Revision ID: v002
Revises: v001
Create Date: 2026-05-07
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "v002"
down_revision: Union[str, Sequence[str], None] = "v001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加扩展字段并插入境界数据"""
    # 添加突破概率字段
    op.add_column("realms", sa.Column("breakthrough_probability", sa.Integer, server_default="50"))
    
    # 添加基础事件编号字段
    op.add_column("realms", sa.Column("event_id", sa.Integer, server_default="1"))

    # 插入43个境界数据
    realms_table = sa.table(
        "realms",
        sa.column("id", sa.Text),
        sa.column("name", sa.Text),
        sa.column("description", sa.Text),
        sa.column("level", sa.Integer),
        sa.column("experience_required", sa.Integer),
        sa.column("health_bonus", sa.Integer),
        sa.column("attack_bonus", sa.Integer),
        sa.column("defense_bonus", sa.Integer),
        sa.column("breakthrough_probability", sa.Integer),
        sa.column("event_id", sa.Integer),
    )

    realms_data = [
        {"id": "realm_001", "name": "凡人", "description": "未踏入修仙之路的普通人", "level": 1, "experience_required": 0, "health_bonus": 0, "attack_bonus": 0, "defense_bonus": 0, "breakthrough_probability": 100, "event_id": 1},
        {"id": "realm_002", "name": "炼气初期", "description": "开始感应天地灵气，踏入修仙之门", "level": 2, "experience_required": 100, "health_bonus": 10, "attack_bonus": 5, "defense_bonus": 2, "breakthrough_probability": 90, "event_id": 1},
        {"id": "realm_003", "name": "炼气中期", "description": "灵气运转更加纯熟，实力稳步提升", "level": 3, "experience_required": 500, "health_bonus": 20, "attack_bonus": 10, "defense_bonus": 4, "breakthrough_probability": 80, "event_id": 1},
        {"id": "realm_004", "name": "炼气后期", "description": "灵气充沛，实力大增", "level": 4, "experience_required": 1000, "health_bonus": 35, "attack_bonus": 15, "defense_bonus": 6, "breakthrough_probability": 70, "event_id": 1},
        {"id": "realm_005", "name": "炼气圆满", "description": "炼气期巅峰，准备冲击筑基", "level": 5, "experience_required": 3000, "health_bonus": 50, "attack_bonus": 20, "defense_bonus": 8, "breakthrough_probability": 60, "event_id": 1},
        {"id": "realm_006", "name": "筑基初期", "description": "成功筑基，修仙之路正式开始", "level": 6, "experience_required": 4000, "health_bonus": 80, "attack_bonus": 35, "defense_bonus": 15, "breakthrough_probability": 50, "event_id": 1},
        {"id": "realm_007", "name": "筑基中期", "description": "根基稳固，实力显著提升", "level": 7, "experience_required": 6000, "health_bonus": 100, "attack_bonus": 45, "defense_bonus": 20, "breakthrough_probability": 40, "event_id": 1},
        {"id": "realm_008", "name": "筑基后期", "description": "筑基圆满在望", "level": 8, "experience_required": 8000, "health_bonus": 130, "attack_bonus": 55, "defense_bonus": 25, "breakthrough_probability": 30, "event_id": 1},
        {"id": "realm_009", "name": "筑基圆满", "description": "筑基期巅峰，准备凝聚金丹", "level": 9, "experience_required": 10000, "health_bonus": 160, "attack_bonus": 70, "defense_bonus": 30, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_010", "name": "金丹初期", "description": "成功凝聚金丹，寿元大增", "level": 10, "experience_required": 12000, "health_bonus": 200, "attack_bonus": 90, "defense_bonus": 40, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_011", "name": "金丹中期", "description": "金丹稳固，实力倍增", "level": 11, "experience_required": 14000, "health_bonus": 250, "attack_bonus": 110, "defense_bonus": 50, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_012", "name": "金丹后期", "description": "金丹圆满在即", "level": 12, "experience_required": 16000, "health_bonus": 300, "attack_bonus": 130, "defense_bonus": 60, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_013", "name": "金丹圆满", "description": "金丹期巅峰，准备化婴", "level": 13, "experience_required": 18000, "health_bonus": 350, "attack_bonus": 150, "defense_bonus": 70, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_014", "name": "元婴初期", "description": "成功化婴，实力飞跃", "level": 14, "experience_required": 20000, "health_bonus": 400, "attack_bonus": 180, "defense_bonus": 80, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_015", "name": "元婴中期", "description": "元婴稳固，神通初显", "level": 15, "experience_required": 22000, "health_bonus": 450, "attack_bonus": 200, "defense_bonus": 90, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_016", "name": "元婴后期", "description": "元婴圆满在望", "level": 16, "experience_required": 24000, "health_bonus": 500, "attack_bonus": 220, "defense_bonus": 100, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_017", "name": "元婴圆满", "description": "元婴期巅峰，准备化神", "level": 17, "experience_required": 26000, "health_bonus": 550, "attack_bonus": 240, "defense_bonus": 110, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_018", "name": "化神初期", "description": "成功化神，掌握天地法则", "level": 18, "experience_required": 28000, "health_bonus": 600, "attack_bonus": 270, "defense_bonus": 120, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_019", "name": "化神中期", "description": "化神稳固，法则初悟", "level": 19, "experience_required": 30000, "health_bonus": 650, "attack_bonus": 300, "defense_bonus": 130, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_020", "name": "化神后期", "description": "化神圆满在即", "level": 20, "experience_required": 32000, "health_bonus": 700, "attack_bonus": 330, "defense_bonus": 140, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_021", "name": "化神圆满", "description": "化神期巅峰，准备炼虚", "level": 21, "experience_required": 34000, "health_bonus": 750, "attack_bonus": 360, "defense_bonus": 150, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_022", "name": "炼虚初期", "description": "开始炼虚合道", "level": 22, "experience_required": 36000, "health_bonus": 800, "attack_bonus": 400, "defense_bonus": 160, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_023", "name": "炼虚中期", "description": "炼虚稳固", "level": 23, "experience_required": 38000, "health_bonus": 850, "attack_bonus": 440, "defense_bonus": 170, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_024", "name": "炼虚后期", "description": "炼虚圆满在望", "level": 24, "experience_required": 40000, "health_bonus": 900, "attack_bonus": 480, "defense_bonus": 180, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_025", "name": "炼虚圆满", "description": "炼虚期巅峰，准备合体", "level": 25, "experience_required": 42000, "health_bonus": 950, "attack_bonus": 520, "defense_bonus": 190, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_026", "name": "合体初期", "description": "天人合一，实力大增", "level": 26, "experience_required": 44000, "health_bonus": 1000, "attack_bonus": 560, "defense_bonus": 200, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_027", "name": "合体中期", "description": "合体稳固", "level": 27, "experience_required": 46000, "health_bonus": 1050, "attack_bonus": 600, "defense_bonus": 210, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_028", "name": "合体后期", "description": "合体圆满在即", "level": 28, "experience_required": 48000, "health_bonus": 1100, "attack_bonus": 640, "defense_bonus": 220, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_029", "name": "合体圆满", "description": "合体期巅峰，准备大乘", "level": 29, "experience_required": 50000, "health_bonus": 1150, "attack_bonus": 680, "defense_bonus": 230, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_030", "name": "大乘初期", "description": "大乘之境，天地共鸣", "level": 30, "experience_required": 52000, "health_bonus": 1200, "attack_bonus": 720, "defense_bonus": 240, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_031", "name": "大乘中期", "description": "大乘稳固", "level": 31, "experience_required": 54000, "health_bonus": 1250, "attack_bonus": 760, "defense_bonus": 250, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_032", "name": "大乘后期", "description": "大乘圆满在望", "level": 32, "experience_required": 56000, "health_bonus": 1300, "attack_bonus": 800, "defense_bonus": 260, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_033", "name": "大乘圆满", "description": "大乘期巅峰，准备渡劫", "level": 33, "experience_required": 58000, "health_bonus": 1350, "attack_bonus": 840, "defense_bonus": 270, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_034", "name": "渡劫初期", "description": "天劫降临，渡劫飞升", "level": 34, "experience_required": 60000, "health_bonus": 1400, "attack_bonus": 900, "defense_bonus": 280, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_035", "name": "渡劫中期", "description": "渡劫稳固", "level": 35, "experience_required": 62000, "health_bonus": 1450, "attack_bonus": 960, "defense_bonus": 290, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_036", "name": "渡劫后期", "description": "渡劫圆满在即", "level": 36, "experience_required": 64000, "health_bonus": 1500, "attack_bonus": 1020, "defense_bonus": 300, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_037", "name": "渡劫圆满", "description": "渡劫期巅峰，准备飞升成仙", "level": 37, "experience_required": 66000, "health_bonus": 1550, "attack_bonus": 1080, "defense_bonus": 310, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_038", "name": "真仙", "description": "渡劫成功，成就真仙之体", "level": 38, "experience_required": 68000, "health_bonus": 1600, "attack_bonus": 1200, "defense_bonus": 320, "breakthrough_probability": 10, "event_id": 1},
        {"id": "realm_039", "name": "金仙", "description": "金身不坏，寿与天齐", "level": 39, "experience_required": 70000, "health_bonus": 1700, "attack_bonus": 1350, "defense_bonus": 340, "breakthrough_probability": 10, "event_id": 1},
        {"id": "realm_040", "name": "太乙金仙", "description": "太乙道果，神通广大", "level": 40, "experience_required": 72000, "health_bonus": 1800, "attack_bonus": 1500, "defense_bonus": 360, "breakthrough_probability": 10, "event_id": 1},
        {"id": "realm_041", "name": "大罗金仙", "description": "大罗道果，万法不侵", "level": 41, "experience_required": 74000, "health_bonus": 1900, "attack_bonus": 1650, "defense_bonus": 380, "breakthrough_probability": 10, "event_id": 1},
        {"id": "realm_042", "name": "仙王", "description": "仙界王者，执掌一方", "level": 42, "experience_required": 76000, "health_bonus": 2000, "attack_bonus": 1800, "defense_bonus": 400, "breakthrough_probability": 10, "event_id": 1},
        {"id": "realm_043", "name": "仙帝", "description": "仙界至尊，俯瞰众生", "level": 43, "experience_required": 78000, "health_bonus": 2200, "attack_bonus": 2000, "defense_bonus": 450, "breakthrough_probability": 10, "event_id": 1},
    ]

    op.bulk_insert(realms_table, realms_data)


def downgrade() -> None:
    """回滚境界数据和字段"""
    # 删除添加的字段
    op.drop_column("realms", "event_id")
    op.drop_column("realms", "breakthrough_probability")
    
    # 删除插入的境界数据（保留凡人）
    op.execute("DELETE FROM realms WHERE id != 'realm_001'")
