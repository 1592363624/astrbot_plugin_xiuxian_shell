"""
检查数据库中是否有需要迁移的数据
"""

import sqlite3
from pathlib import Path


def check_database():
    """检查数据库内容"""
    db_path = Path(__file__).parent.parent.parent / "plugin_data" / "astrbot_plugin_xiuxian_shell" / "xiuxian.db"

    if not db_path.exists():
        print(f"数据库不存在: {db_path}")
        return

    print(f"检查数据库: {db_path}\n")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    tables = ["realms", "items", "skills", "game_events"]

    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"表 {table}: {count} 条记录")
        except Exception as e:
            print(f"表 {table}: 检查失败 - {e}")

    conn.close()


if __name__ == "__main__":
    check_database()
