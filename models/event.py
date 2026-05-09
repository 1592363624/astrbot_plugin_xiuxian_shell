"""
事件数据模型
定义游戏中事件的数据结构
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class GameEvent:
    """游戏事件数据模型"""

    id: str
    name: str
    description: str
    event_type: str  # explore, combat, random, quest
    trigger_condition: str | None = None
    reward_type: str | None = None  # item, spirit_stone, experience
    reward_value: int = 0
    probability: float = 0.5
    is_active: bool = True
    created_at: datetime | None = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "event_type": self.event_type,
            "trigger_condition": self.trigger_condition,
            "reward_type": self.reward_type,
            "reward_value": self.reward_value,
            "probability": self.probability,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GameEvent":
        """从字典创建实例"""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            description=data.get("description"),
            event_type=data.get("event_type"),
            trigger_condition=data.get("trigger_condition"),
            reward_type=data.get("reward_type"),
            reward_value=data.get("reward_value", 0),
            probability=data.get("probability", 0.5),
            is_active=bool(data.get("is_active", 1)),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
        )


@dataclass
class PlayerEvent:
    """玩家事件记录数据模型"""

    id: str
    player_id: str
    event_id: str
    triggered_at: datetime | None = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "player_id": self.player_id,
            "event_id": self.event_id,
            "triggered_at": self.triggered_at.isoformat()
            if self.triggered_at
            else None,
        }
