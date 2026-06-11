"""
数据迁移脚本：将数据库中的 realms、items、skills、events 数据导出到 JSON 文件

运行方式：
python scripts/migrate_db_to_json_standalone.py

此脚本会：
1. 如果数据库存在，直接从数据库导出数据
2. 如果数据库不存在，使用代码中定义的默认数据创建JSON文件
3. 将数据导出到 data/game_data/ 目录下的 JSON 文件
"""

import json
import sqlite3
from pathlib import Path


DEFAULT_DATA = {
    "realms": [
        {"id": "realm_001", "name": "凡人", "description": "未踏入修仙之路的普通人", "level": 1, "experience_required": 0, "breakthrough_probability": 100, "event_id": 1},
        {"id": "realm_002", "name": "炼气初期", "description": "开始感应天地灵气，踏入修仙之门", "level": 2, "experience_required": 100, "breakthrough_probability": 90, "event_id": 1},
        {"id": "realm_003", "name": "炼气中期", "description": "灵气运转更加纯熟，实力稳步提升", "level": 3, "experience_required": 500, "breakthrough_probability": 80, "event_id": 1},
        {"id": "realm_004", "name": "炼气后期", "description": "灵气充沛，实力大增", "level": 4, "experience_required": 1000, "breakthrough_probability": 70, "event_id": 1},
        {"id": "realm_005", "name": "炼气圆满", "description": "炼气期巅峰，准备冲击筑基", "level": 5, "experience_required": 3000, "breakthrough_probability": 60, "event_id": 1},
        {"id": "realm_006", "name": "筑基初期", "description": "成功筑基，修仙之路正式开始", "level": 6, "experience_required": 4000, "breakthrough_probability": 50, "event_id": 1},
        {"id": "realm_007", "name": "筑基中期", "description": "根基稳固，实力显著提升", "level": 7, "experience_required": 6000, "breakthrough_probability": 40, "event_id": 1},
        {"id": "realm_008", "name": "筑基后期", "description": "筑基圆满在望", "level": 8, "experience_required": 8000, "breakthrough_probability": 30, "event_id": 1},
        {"id": "realm_009", "name": "筑基圆满", "description": "筑基期巅峰，准备凝聚金丹", "level": 9, "experience_required": 10000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_010", "name": "金丹初期", "description": "成功凝聚金丹，寿元大增", "level": 10, "experience_required": 12000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_011", "name": "金丹中期", "description": "金丹稳固，实力倍增", "level": 11, "experience_required": 14000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_012", "name": "金丹后期", "description": "金丹圆满在即", "level": 12, "experience_required": 16000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_013", "name": "金丹圆满", "description": "金丹期巅峰，准备化婴", "level": 13, "experience_required": 18000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_014", "name": "元婴初期", "description": "成功化婴，实力飞跃", "level": 14, "experience_required": 20000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_015", "name": "元婴中期", "description": "元婴稳固，神通初显", "level": 15, "experience_required": 22000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_016", "name": "元婴后期", "description": "元婴圆满在望", "level": 16, "experience_required": 24000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_017", "name": "元婴圆满", "description": "元婴期巅峰，准备化神", "level": 17, "experience_required": 26000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_018", "name": "化神初期", "description": "成功化神，掌握天地法则", "level": 18, "experience_required": 28000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_019", "name": "化神中期", "description": "化神稳固，法则初悟", "level": 19, "experience_required": 30000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_020", "name": "化神后期", "description": "化神圆满在即", "level": 20, "experience_required": 32000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_021", "name": "化神圆满", "description": "化神期巅峰，准备炼虚", "level": 21, "experience_required": 34000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_022", "name": "炼虚初期", "description": "开始炼虚合道", "level": 22, "experience_required": 36000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_023", "name": "炼虚中期", "description": "炼虚稳固", "level": 23, "experience_required": 38000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_024", "name": "炼虚后期", "description": "炼虚圆满在望", "level": 24, "experience_required": 40000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_025", "name": "炼虚圆满", "description": "炼虚期巅峰，准备合体", "level": 25, "experience_required": 42000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_026", "name": "合体初期", "description": "天人合一，实力大增", "level": 26, "experience_required": 44000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_027", "name": "合体中期", "description": "合体稳固", "level": 27, "experience_required": 46000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_028", "name": "合体后期", "description": "合体圆满在即", "level": 28, "experience_required": 48000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_029", "name": "合体圆满", "description": "合体期巅峰，准备大乘", "level": 29, "experience_required": 50000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_030", "name": "大乘初期", "description": "大乘之境，天地共鸣", "level": 30, "experience_required": 52000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_031", "name": "大乘中期", "description": "大乘稳固", "level": 31, "experience_required": 54000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_032", "name": "大乘后期", "description": "大乘圆满在望", "level": 32, "experience_required": 56000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_033", "name": "大乘圆满", "description": "大乘期巅峰，准备渡劫", "level": 33, "experience_required": 58000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_034", "name": "渡劫初期", "description": "天劫降临，渡劫飞升", "level": 34, "experience_required": 60000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_035", "name": "渡劫中期", "description": "渡劫稳固", "level": 35, "experience_required": 62000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_036", "name": "渡劫后期", "description": "渡劫圆满在即", "level": 36, "experience_required": 64000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_037", "name": "渡劫圆满", "description": "渡劫期巅峰，准备飞升成仙", "level": 37, "experience_required": 66000, "breakthrough_probability": 20, "event_id": 1},
        {"id": "realm_038", "name": "真仙", "description": "渡劫成功，成就真仙之体", "level": 38, "experience_required": 68000, "breakthrough_probability": 10, "event_id": 1},
        {"id": "realm_039", "name": "金仙", "description": "金身不坏，寿与天齐", "level": 39, "experience_required": 70000, "breakthrough_probability": 10, "event_id": 1},
        {"id": "realm_040", "name": "太乙金仙", "description": "太乙道果，神通广大", "level": 40, "experience_required": 72000, "breakthrough_probability": 10, "event_id": 1},
        {"id": "realm_041", "name": "大罗金仙", "description": "大罗道果，万法不侵", "level": 41, "experience_required": 74000, "breakthrough_probability": 10, "event_id": 1},
        {"id": "realm_042", "name": "仙王", "description": "仙界王者，执掌一方", "level": 42, "experience_required": 76000, "breakthrough_probability": 10, "event_id": 1},
        {"id": "realm_043", "name": "仙帝", "description": "仙界至尊，俯瞰众生", "level": 43, "experience_required": 78000, "breakthrough_probability": 10, "event_id": 1},
    ],
    "items": [
        {"id": "item_001", "name": "回春丹", "description": "恢复50点生命值", "item_type": "consumable", "effect_type": "heal", "effect_value": 50, "price": 50, "is_usable": True, "realm_requirement": None},
        {"id": "item_002", "name": "聚灵丹", "description": "增加100点修为", "item_type": "consumable", "effect_type": "exp", "effect_value": 100, "price": 200, "is_usable": True, "realm_requirement": None},
        {"id": "item_003", "name": "灵石", "description": "修仙界通用货币", "item_type": "currency", "effect_type": "spirit_stone", "effect_value": 1, "price": 1, "is_usable": False, "realm_requirement": None},
        {"id": "item_004", "name": "清灵丹", "description": "清除体内丹毒", "item_type": "consumable", "effect_type": "detox", "effect_value": 0, "price": 300, "is_usable": True, "realm_requirement": "realm_006"},
        {"id": "item_005", "name": "筑基丹", "description": "增加突破筑基成功率", "item_type": "consumable", "effect_type": "breakthrough", "effect_value": 20, "price": 1000, "is_usable": True, "realm_requirement": "realm_005"},
        {"id": "item_006", "name": "破境丹", "description": "增加突破境界概率", "item_type": "consumable", "effect_type": "breakthrough", "effect_value": 30, "price": 5000, "is_usable": True, "realm_requirement": "realm_010"},
        {"id": "item_007", "name": "灵草", "description": "炼制丹药的原料", "item_type": "material", "effect_type": None, "effect_value": 0, "price": 20, "is_usable": False, "realm_requirement": None},
        {"id": "item_008", "name": "百年灵芝", "description": "珍贵的炼丹药材", "item_type": "material", "effect_type": None, "effect_value": 0, "price": 500, "is_usable": False, "realm_requirement": None},
    ],
    "skills": [
        {"id": "skill_001", "name": "基础吐纳术", "description": "最基础的修炼功法", "skill_type": "cultivation", "realm_requirement": "realm_001", "experience_gain": 10, "damage": 0, "cooldown": 0, "defense_bonus": 0},
        {"id": "skill_002", "name": "劈空掌", "description": "基础攻击技能", "skill_type": "combat", "realm_requirement": "realm_001", "experience_gain": 0, "damage": 15, "cooldown": 3, "defense_bonus": 0},
        {"id": "skill_003", "name": "护体灵光", "description": "基础防御技能", "skill_type": "combat", "realm_requirement": "realm_001", "experience_gain": 0, "damage": 0, "cooldown": 5, "defense_bonus": 10},
        {"id": "skill_004", "name": "引气入体", "description": "引导灵气入体，加速修炼", "skill_type": "cultivation", "realm_requirement": "realm_002", "experience_gain": 20, "damage": 0, "cooldown": 0, "defense_bonus": 0},
        {"id": "skill_005", "name": "灵气斩", "description": "凝聚灵气斩击敌人", "skill_type": "combat", "realm_requirement": "realm_003", "experience_gain": 0, "damage": 30, "cooldown": 4, "defense_bonus": 0},
        {"id": "skill_006", "name": "聚灵诀", "description": "聚集灵气，提升修炼效率", "skill_type": "cultivation", "realm_requirement": "realm_005", "experience_gain": 50, "damage": 0, "cooldown": 0, "defense_bonus": 0},
        {"id": "skill_007", "name": "金身诀", "description": "锻造金身，提升防御", "skill_type": "passive", "realm_requirement": "realm_006", "experience_gain": 0, "damage": 0, "cooldown": 0, "defense_bonus": 20},
        {"id": "skill_008", "name": "金丹真火", "description": "金丹期才能施展的真火攻击", "skill_type": "combat", "realm_requirement": "realm_010", "experience_gain": 0, "damage": 80, "cooldown": 6, "defense_bonus": 0},
        {"id": "skill_009", "name": "元婴出窍", "description": "元婴期神通，神识攻击", "skill_type": "combat", "realm_requirement": "realm_014", "experience_gain": 0, "damage": 120, "cooldown": 8, "defense_bonus": 0},
        {"id": "skill_010", "name": "化神诀", "description": "化神期修炼功法", "skill_type": "cultivation", "realm_requirement": "realm_018", "experience_gain": 200, "damage": 0, "cooldown": 0, "defense_bonus": 0},
    ],
    "events": [
        {"id": "event_001", "name": "灵草奇遇", "description": "你在山间发现了一株灵草", "event_type": "explore", "trigger_condition": "explore", "reward_type": "item", "reward_value": "item_007", "probability": 0.3, "is_active": True},
        {"id": "event_002", "name": "妖兽袭击", "description": "一只妖兽突然出现", "event_type": "combat", "trigger_condition": "explore", "reward_type": "spirit_stone", "reward_value": 50, "probability": 0.2, "is_active": True},
        {"id": "event_003", "name": "顿悟", "description": "灵光一闪，你对修炼有了新的领悟", "event_type": "cultivation", "trigger_condition": "cultivate", "reward_type": "experience", "reward_value": 100, "probability": 0.15, "is_active": True},
        {"id": "event_004", "name": "奇遇：前辈遗物", "description": "你发现了一位前辈的洞府遗迹", "event_type": "explore", "trigger_condition": "seclusion", "reward_type": "item", "reward_value": "item_008", "probability": 0.1, "is_active": True},
        {"id": "event_005", "name": "天降横财", "description": "天上掉下了一块灵石", "event_type": "random", "trigger_condition": "random", "reward_type": "spirit_stone", "reward_value": 200, "probability": 0.05, "is_active": True},
        {"id": "event_006", "name": "福缘深厚", "description": "你感觉今日运气极佳", "event_type": "random", "trigger_condition": "random", "reward_type": "experience", "reward_value": 500, "probability": 0.08, "is_active": True},
        {"id": "event_007", "name": "闭关奇遇：灵气潮汐", "description": "闭关时遭遇灵气潮汐", "event_type": "cultivation", "trigger_condition": "seclusion", "reward_type": "experience", "reward_value": 1000, "probability": 0.12, "is_active": True},
        {"id": "event_008", "name": "探险发现", "description": "在山洞深处发现了一块蕴含灵气的矿石", "event_type": "explore", "trigger_condition": "explore", "reward_type": "spirit_stone", "reward_value": 150, "probability": 0.25, "is_active": True},
    ]
}


def migrate_data():
    """执行数据迁移"""
    print("=" * 50)
    print("开始数据迁移：数据库 -> JSON文件")
    print("=" * 50)

    plugin_dir = Path(__file__).parent.parent
    db_path = plugin_dir / "data" / "xiuxian.db"
    data_dir = plugin_dir / "data" / "game_data"

    data_dir.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        print(f"\n发现数据库文件: {db_path}")
        print("从数据库导出数据...\n")

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        tables_to_migrate = ["realms", "items", "skills", "game_events"]
        migration_results = {}

        for table in tables_to_migrate:
            json_table_name = "events" if table == "game_events" else table

            print(f"正在迁移表: {table}")

            try:
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()

                if not rows:
                    print(f"  表 {table} 为空，使用默认数据")
                    data = DEFAULT_DATA.get(json_table_name, [])
                else:
                    data = []
                    for row in rows:
                        item = dict(row)
                        if "_sa_instance_state" in item:
                            del item["_sa_instance_state"]
                        data.append(item)

                json_filename = f"{json_table_name}.json"
                json_path = data_dir / json_filename

                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"  成功导出 {len(data)} 条记录到 {json_path}")
                migration_results[table] = {"status": "success", "count": len(data)}

            except Exception as e:
                print(f"  迁移表 {table} 失败: {e}")
                import traceback
                traceback.print_exc()
                migration_results[table] = {"status": "error", "error": str(e)}

        conn.close()

    else:
        print(f"\n数据库文件不存在: {db_path}")
        print("使用代码中定义的默认数据创建JSON文件...\n")

        migration_results = {}
        for table_name, data in DEFAULT_DATA.items():
            print(f"正在创建: {table_name}.json")
            json_path = data_dir / f"{table_name}.json"

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"  成功创建 {len(data)} 条记录")
            migration_results[table_name] = {"status": "success", "count": len(data)}

    print("\n" + "=" * 50)
    print("迁移完成！")
    print("=" * 50)

    print("\n迁移结果汇总：")
    for table, result in migration_results.items():
        if result["status"] == "success":
            print(f"  ✅ {table}: {result['count']} 条记录")
        else:
            print(f"  ❌ {table}: {result.get('error', '未知错误')}")

    print(f"\nJSON文件保存位置: {data_dir}")
    print("\n请重启插件以加载新的数据存储方式。")


if __name__ == "__main__":
    migrate_data()
