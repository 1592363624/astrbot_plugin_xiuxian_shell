"""
数据模型模块
定义游戏中的各种数据模型，包括玩家、物品、功法、境界等
"""
from .player import Player
from .item import Item, InventoryItem
from .skill import Skill, PlayerSkill
from .realm import Realm
from .event import GameEvent, PlayerEvent
from .checkin import CheckinRecord

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
