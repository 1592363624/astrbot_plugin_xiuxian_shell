"""
API接口模块
提供前后端共享的API接口，用于数据查询和操作
"""
from .player_api import PlayerAPI
from .item_api import ItemAPI
from .skill_api import SkillAPI
from .admin_api import AdminAPI

__all__ = ["PlayerAPI", "ItemAPI", "SkillAPI", "AdminAPI"]
