"""
数据库迁移管理器
基于 Alembic 实现数据库版本管理和迁移脚本执行
"""
import asyncio
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config as AlembicConfig
from astrbot.api import logger

from ..db_manager import DatabaseManager


class MigrationManager:
    """数据库迁移管理器（基于 Alembic）"""

    # 插件根目录，用于定位 alembic 配置
    _plugin_root: Optional[Path] = None
    # Alembic 目录路径
    _alembic_dir: Optional[Path] = None

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化迁移管理器

        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
        if self._plugin_root is None:
            # 自动推导路径：此文件在 database/migrations/ 下
            # database/migrations/ -> database/ -> plugin_root
            self_dir = Path(__file__).resolve().parent  # database/migrations/
            db_dir = self_dir.parent  # database/
            self.__class__._plugin_root = db_dir.parent  # plugin_root
            self.__class__._alembic_dir = db_dir / "alembic"  # database/alembic/

    @property
    def plugin_root(self) -> Path:
        return self._plugin_root

    @property
    def alembic_ini_path(self) -> Path:
        """alembic.ini 配置文件路径"""
        return self.plugin_root / "alembic.ini"

    @property
    def alembic_dir(self) -> Path:
        """alembic 迁移脚本目录"""
        return self._alembic_dir

    async def apply_migrations(self) -> None:
        """
        应用所有待执行的迁移
        在插件启动时调用，确保数据库结构为最新版本
        """
        db_path = str(self.db_manager.db_path.resolve())
        db_url = f"sqlite:///{db_path}"

        # 构建 Alembic 配置
        alembic_cfg = self._build_alembic_config(db_url)

        # 确保数据库连接已建立
        await self.db_manager.connect()

        # 处理旧版迁移系统的兼容：如果存在旧表但没有 alembic_version，则标记为已迁移
        await self._handle_legacy_migration()

        # 在独立的线程中执行同步的 Alembic 迁移（避免阻塞异步事件循环）
        await asyncio.get_event_loop().run_in_executor(
            None, self._run_alembic_upgrade, alembic_cfg
        )

        logger.info("Alembic 数据库迁移已全部应用完成")

    def _build_alembic_config(self, db_url: str) -> AlembicConfig:
        """
        构建 Alembic 配置对象

        Args:
            db_url: SQLAlchemy 格式的数据库连接 URL

        Returns:
            AlembicConfig: 配置对象
        """
        alembic_cfg = AlembicConfig(str(self.alembic_ini_path))
        alembic_cfg.set_main_option("script_location", str(self.alembic_dir))
        alembic_cfg.set_main_option("sqlalchemy.url", db_url)
        return alembic_cfg

    @staticmethod
    def _run_alembic_upgrade(alembic_cfg: AlembicConfig) -> None:
        """
        执行 Alembic 升级到最新版本（同步方法，在 executor 中运行）

        Args:
            alembic_cfg: Alembic 配置对象
        """
        command.upgrade(alembic_cfg, "head")

    async def _handle_legacy_migration(self) -> None:
        """
        处理从旧版自定义迁移系统到 Alembic 的过渡
        如果数据库中存在旧系统的 migration_history 表但 Alembic 未初始化，
        则将 Alembic 版本标记为 v001，避免重复创建表
        """
        table_exists = await self.db_manager.table_exists("alembic_version")
        legacy_table_exists = await self.db_manager.table_exists("migration_history")

        if not table_exists and legacy_table_exists:
            logger.info("检测到旧版迁移记录表，正在迁移到 Alembic 版本管理...")
            # 检查核心表是否已存在（如 players 表）
            has_core_tables = await self.db_manager.table_exists("players")
            if has_core_tables:
                db_path = str(self.db_manager.db_path.resolve())
                db_url = f"sqlite:///{db_path}"
                alembic_cfg = self._build_alembic_config(db_url)
                # 在 executor 中标记 Alembic 版本为 v001
                await asyncio.get_event_loop().run_in_executor(
                    None, self._stamp_to_revision, alembic_cfg, "v001"
                )
                logger.info("已将 Alembic 版本标记为 v001（与现有数据库结构对应）")
            else:
                logger.warning("旧版迁移记录表存在但核心表不存在，将执行全新迁移")

    @staticmethod
    def _stamp_to_revision(alembic_cfg: AlembicConfig, revision: str) -> None:
        """
        将数据库标记为指定版本，不实际执行迁移（同步方法，在 executor 中运行）

        Args:
            alembic_cfg: Alembic 配置对象
            revision: 目标版本号
        """
        command.stamp(alembic_cfg, revision)

    async def downgrade(self, revision: str = "-1") -> None:
        """
        回滚数据库到指定版本

        Args:
            revision: 目标版本号，默认为 "-1" 表示回滚一个版本
        """
        db_path = str(self.db_manager.db_path.resolve())
        db_url = f"sqlite:///{db_path}"
        alembic_cfg = self._build_alembic_config(db_url)

        await asyncio.get_event_loop().run_in_executor(
            None, self._run_alembic_downgrade, alembic_cfg, revision
        )
        logger.info(f"Alembic 数据库已回滚至版本: {revision}")

    @staticmethod
    def _run_alembic_downgrade(alembic_cfg: AlembicConfig, revision: str) -> None:
        """
        执行 Alembic 降级（同步方法，在 executor 中运行）

        Args:
            alembic_cfg: Alembic 配置对象
            revision: 目标版本号
        """
        command.downgrade(alembic_cfg, revision)

    def create_migration(self, message: str) -> None:
        """
        创建新的迁移脚本（开发辅助方法，同步调用）

        Args:
            message: 迁移描述信息
        """
        db_path = str(self.db_manager.db_path.resolve())
        db_url = f"sqlite:///{db_path}"
        alembic_cfg = self._build_alembic_config(db_url)
        command.revision(alembic_cfg, autogenerate=False, message=message)
        logger.info(f"已创建新的迁移脚本: {message}")

    def auto_migration(self, message: str = "auto") -> None:
        """
        自动生成迁移脚本（基于 SQLAlchemy 元数据对比，同步调用）

        Args:
            message: 迁移描述信息
        """
        db_path = str(self.db_manager.db_path.resolve())
        db_url = f"sqlite:///{db_path}"
        alembic_cfg = self._build_alembic_config(db_url)
        command.revision(alembic_cfg, autogenerate=True, message=message)
        logger.info(f"已自动生成迁移脚本: {message}")
