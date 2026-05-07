"""
迁移基类
所有迁移脚本都需要继承此基类
"""
from abc import ABC, abstractmethod
from ..db_manager import DatabaseManager


class BaseMigration(ABC):
    """迁移基类"""

    version: str = ""
    description: str = ""

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化迁移
        
        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager

    @abstractmethod
    async def up(self):
        """执行迁移"""
        pass

    @abstractmethod
    async def down(self):
        """回滚迁移"""
        pass
