"""
数据库迁移管理器
负责数据库版本管理和迁移脚本执行
"""
import importlib
import pkgutil
from pathlib import Path
from typing import List, Type
from astrbot.api import logger
from ..db_manager import DatabaseManager
from .base_migration import BaseMigration


class MigrationManager:
    """数据库迁移管理器"""

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化迁移管理器
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
        self.migrations: List[Type[BaseMigration]] = []

    async def apply_migrations(self):
        """应用所有待执行的迁移"""
        # 创建迁移记录表
        await self._create_migration_table()
        # 加载所有迁移脚本
        self._load_migrations()
        # 获取已执行的迁移版本
        applied_versions = await self._get_applied_versions()
        # 执行未应用的迁移
        for migration_class in self.migrations:
            migration = migration_class(self.db_manager)
            if migration.version not in applied_versions:
                logger.info(f"应用迁移: {migration.version} - {migration.description}")
                await migration.up()
                await self._record_migration(migration.version, migration.description)
                logger.info(f"迁移完成: {migration.version}")
        logger.info("所有迁移已应用完成")

    async def _create_migration_table(self):
        """创建迁移记录表"""
        sql = """
        CREATE TABLE IF NOT EXISTS migration_history (
            version TEXT PRIMARY KEY,
            description TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        await self.db_manager.execute(sql)
        await self.db_manager.commit()

    def _load_migrations(self):
        """加载所有迁移脚本"""
        migrations_package = Path(__file__).parent
        for importer, module_name, is_package in pkgutil.iter_modules([str(migrations_package)]):
            if module_name.startswith("v") and module_name != "base_migration":
                try:
                    module = importlib.import_module(f".{module_name}", package=__package__)
                    # 查找继承BaseMigration的类
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and 
                            issubclass(attr, BaseMigration) and 
                            attr is not BaseMigration):
                            self.migrations.append(attr)
                except Exception as e:
                    logger.error(f"加载迁移脚本失败 {module_name}: {e}")
        # 按版本号排序
        self.migrations.sort(key=lambda m: m.version)

    async def _get_applied_versions(self) -> set:
        """获取已执行的迁移版本"""
        sql = "SELECT version FROM migration_history"
        rows = await self.db_manager.fetch_all(sql)
        return {row["version"] for row in rows}

    async def _record_migration(self, version: str, description: str):
        """记录迁移执行"""
        sql = "INSERT INTO migration_history (version, description) VALUES (?, ?)"
        await self.db_manager.execute(sql, (version, description))
        await self.db_manager.commit()
