"""
数据库管理器
负责SQLite数据库连接管理和基本操作
"""

import re
from pathlib import Path
from typing import Any

import aiosqlite

from astrbot.api import logger

# PRAGMA table_name 不支持参数化，用正则白名单校验防止注入
_TABLE_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class DatabaseManager:
    """SQLite数据库管理器"""

    def __init__(self, db_path: str):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> aiosqlite.Connection:
        """
        获取数据库连接

        Returns:
            aiosqlite.Connection: 数据库连接对象
        """
        if self._connection is None:
            self._connection = await aiosqlite.connect(str(self.db_path))
            # 启用WAL模式
            await self._connection.execute("PRAGMA journal_mode=WAL")
            # 设置行工厂，返回字典格式结果
            self._connection.row_factory = aiosqlite.Row
            logger.info(f"数据库连接已建立: {self.db_path}")
        return self._connection

    async def close(self):
        """关闭数据库连接"""
        if self._connection:
            # 执行WAL检查点，确保数据写入主数据库
            await self._connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            await self._connection.close()
            self._connection = None
            logger.info("数据库连接已关闭")

    async def execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        """
        执行SQL语句

        Args:
            sql: SQL语句
            params: 参数元组

        Returns:
            aiosqlite.Cursor: 游标对象
        """
        conn = await self.connect()
        return await conn.execute(sql, params)

    async def executemany(self, sql: str, params_list: list[tuple]) -> aiosqlite.Cursor:
        """
        批量执行SQL语句

        Args:
            sql: SQL语句
            params_list: 参数列表

        Returns:
            aiosqlite.Cursor: 游标对象
        """
        conn = await self.connect()
        return await conn.executemany(sql, params_list)

    async def fetch_one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        """
        查询单条记录

        Args:
            sql: SQL语句
            params: 参数元组

        Returns:
            Optional[Dict[str, Any]]: 查询结果字典或None
        """
        conn = await self.connect()
        cursor = await conn.execute(sql, params)
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None

    async def fetch_all(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        """
        查询多条记录

        Args:
            sql: SQL语句
            params: 参数元组

        Returns:
            List[Dict[str, Any]]: 查询结果字典列表
        """
        conn = await self.connect()
        cursor = await conn.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def commit(self):
        """提交事务"""
        if self._connection:
            await self._connection.commit()

    async def rollback(self):
        """回滚事务"""
        if self._connection:
            await self._connection.rollback()

    async def table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在

        Args:
            table_name: 表名

        Returns:
            bool: 表是否存在
        """
        sql = "SELECT name FROM sqlite_master WHERE type='table' AND name=?"
        result = await self.fetch_one(sql, (table_name,))
        return result is not None

    async def column_exists(self, table_name: str, column_name: str) -> bool:
        """
        检查表中指定列是否存在

        Args:
            table_name: 表名
            column_name: 列名

        Returns:
            bool: 列是否存在
        """
        if not _TABLE_NAME_RE.match(table_name):
            raise ValueError(f"Invalid table name: {table_name}")
        sql = f"PRAGMA table_info({table_name})"
        columns = await self.fetch_all(sql)
        return any(col["name"] == column_name for col in columns)

    async def get_table_info(self, table_name: str) -> list[dict[str, Any]]:
        """
        获取表结构信息

        Args:
            table_name: 表名

        Returns:
            List[Dict[str, Any]]: 表结构信息列表
        """
        if not _TABLE_NAME_RE.match(table_name):
            raise ValueError(f"Invalid table name: {table_name}")
        sql = f"PRAGMA table_info({table_name})"
        return await self.fetch_all(sql)
