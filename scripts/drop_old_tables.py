"""
删除数据库中不再需要的表

这些表的数据已经迁移到JSON文件，可以安全删除：
- skills: 功法模板表（已迁移到 data/game_data/skills.json）
- game_events: 事件模板表（已迁移到 data/game_data/events.json）
"""

import sqlite3


DB_PATH = r"d:\WorkSpace\PyCharmWorkspace\AstrBot\data\plugin_data\astrbot_plugin_xiuxian_shell\xiuxian.db"


def delete_tables():
    """删除不再需要的表"""
    print(f"数据库路径: {DB_PATH}")

    import os
    if not os.path.exists(DB_PATH):
        print("数据库不存在")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    tables_to_delete = ["skills", "game_events"]
    results = {}

    for table in tables_to_delete:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
            conn.commit()
            print(f"✅ 已删除表: {table}")
            results[table] = "success"
        except Exception as e:
            print(f"❌ 删除表 {table} 失败: {e}")
            results[table] = f"error: {e}"

    conn.close()

    print("\n完成！")
    print("\n保留的表（包含用户数据）：")
    print("- players: 玩家数据")
    print("- player_inventory: 玩家背包")
    print("- player_skills: 玩家学习的功法")
    print("- realms: 境界模板（可考虑删除）")
    print("- items: 物品模板（可考虑删除）")


if __name__ == "__main__":
    delete_tables()
