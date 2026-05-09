"""
数据模型模块
定义游戏中的各种数据模型，包括玩家、物品、功法、境界等
"""

from .checkin import CheckinRecord
from .event import GameEvent, PlayerEvent
from .item import InventoryItem, Item
from .player import Player
from .realm import Realm
from .skill import PlayerSkill, Skill

__all__ = [
    "Player",
    "Item",
    "InventoryItem",
    "Skill",
    "PlayerSkill",
    "Realm",
    "GameEvent",
    "PlayerEvent",
    "CheckinRecord",
]
