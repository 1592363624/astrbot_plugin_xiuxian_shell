"""
数据库迁移模块
基于 Alembic 管理数据库版本和迁移脚本
原有自定义迁移文件（v001_initial_schema.py、base_migration.py）保留作为历史参考
"""

from .migration_manager import MigrationManager

__all__ = ["MigrationManager"]
