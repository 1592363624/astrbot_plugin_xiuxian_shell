"""
API接口模块
提供前后端共享的API接口，用于数据查询和操作
"""

from .admin_api import AdminAPI
from .checkin_api import CheckinAPI
from .cultivation_api import CultivationAPI
from .deep_seclusion_api import DeepSeclusionAPI
from .item_api import ItemAPI
from .notification_api import NotificationAPI
from .player_api import PlayerAPI

__all__ = [
    "PlayerAPI",
    "ItemAPI",
    "CultivationAPI",
    "AdminAPI",
    "CheckinAPI",
    "NotificationAPI",
    "DeepSeclusionAPI",
]
