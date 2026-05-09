"""
检查并迁移数据库数据到JSON文件

使用方式：
1. 首次运行时确保数据库有数据
2. 运行此脚本将数据导出到JSON
3. 确认JSON文件正确后，可选择删除数据库中的 realms/items/skills/game_events 表
"""

import sqlite3
from pathlib import Path


def get_data_dir():
    """获取AstrBot data目录"""
    return Path(__file__).parent.parent.parent.parent / "data"


def migrate():
    """执行迁移"""
    data_dir = get_data_dir()
    db_path = data_dir / "plugin_data" / "astrbot_plugin_xiuxian_shell" / "xiuxian.db"
    json_dir = data_dir / "plugin_data" / "astrbot_plugin_xiuxian_shell" / "game_data"

    print(f"数据库路径: {db_path}")
    print(f"JSON目录: {json_dir}")
    print(f"数据库存在: {db_path.exists()}")

    if not db_path.exists():
        print("\n数据库不存在，请先运行插件初始化数据库")
        return

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    tables = ["realms", "items", "skills", "game_events"]
    print("\n数据库内容：")
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} 条")
        except Exception as e:
            print(f"  {table}: 错误 - {e}")

    conn.close()
    print("\n" + "=" * 50)
    print("如果数据库有数据，请运行迁移脚本导出数据")
    print("脚本位置: scripts/migrate_db_to_json.py")


if __name__ == "__main__":
    migrate()
