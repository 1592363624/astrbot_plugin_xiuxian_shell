"""
检查数据库并迁移到JSON文件

此脚本将数据库中的 realms, items, skills, game_events 表数据导出到JSON文件
"""

import sqlite3
from pathlib import Path

ASTRBOT_DATA_DIR = Path(r"d:\WorkSpace\PyCharmWorkspace\AstrBot\data")
PLUGIN_DATA_DIR = ASTRBOT_DATA_DIR / "plugin_data" / "astrbot_plugin_xiuxian_shell"
DB_PATH = PLUGIN_DATA_DIR / "xiuxian.db"
JSON_DIR = PLUGIN_DATA_DIR / "game_data"

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
    ],
    "items": [
        {"id": "item_001", "name": "回春丹", "description": "恢复50点生命值", "item_type": "consumable", "rarity": "common", "effect_type": "heal", "effect_value": 50, "price": 50, "is_usable": True, "realm_requirement": None},
        {"id": "item_002", "name": "聚灵丹", "description": "增加100点修为", "item_type": "consumable", "rarity": "uncommon", "effect_type": "exp", "effect_value": 100, "price": 200, "is_usable": True, "realm_requirement": None},
        {"id": "item_003", "name": "灵石", "description": "修仙界通用货币", "item_type": "currency", "rarity": "common", "effect_type": "spirit_stone", "effect_value": 1, "price": 1, "is_usable": False, "realm_requirement": None},
    ],
    "skills": [
        {"id": "skill_001", "name": "基础吐纳术", "description": "最基础的修炼功法", "skill_type": "cultivation", "realm_requirement": "realm_001", "experience_gain": 10, "damage": 0, "cooldown": 0, "defense_bonus": 0},
        {"id": "skill_002", "name": "劈空掌", "description": "基础攻击技能", "skill_type": "combat", "realm_requirement": "realm_001", "experience_gain": 0, "damage": 15, "cooldown": 3, "defense_bonus": 0},
    ],
    "events": [
        {"id": "event_001", "name": "灵草奇遇", "description": "你在山间发现了一株灵草", "event_type": "explore", "trigger_condition": "explore", "reward_type": "item", "reward_value": "item_007", "probability": 0.3, "is_active": True},
    ]
}


def main():
    print("=" * 60)
    print("数据迁移工具")
    print("=" * 60)

    print(f"\n数据库路径: {DB_PATH}")
    print(f"JSON目录: {JSON_DIR}")

    JSON_DIR.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        print("\n数据库不存在，使用默认数据创建JSON文件...")
        for name, data in DEFAULT_DATA.items():
            path = JSON_DIR / f"{name}.json"
            import json
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  创建 {name}.json: {len(data)} 条")
    else:
        print("\n发现数据库，导出数据到JSON...")

        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        for table, json_name in [("realms", "realms"), ("items", "items"), ("skills", "skills"), ("game_events", "events")]:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} 条")

            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            data = []
            for row in rows:
                item = dict(zip(columns, row))
                if "_sa_instance_state" in item:
                    del item["_sa_instance_state"]
                data.append(item)

            path = JSON_DIR / f"{json_name}.json"
            import json
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  导出到 {json_name}.json: {len(data)} 条")

        conn.close()

    print("\n" + "=" * 60)
    print("完成！")
    print(f"JSON文件位置: {JSON_DIR}")
    print("\n后续步骤:")
    print("1. 重启插件加载新数据")
    print("2. 确认数据正确后可删除数据库中的 realms, items, skills, game_events 表")


if __name__ == "__main__":
    main()
