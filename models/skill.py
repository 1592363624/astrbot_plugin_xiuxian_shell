"""
功法数据模型
定义游戏中功法技能的数据结构
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Skill:
    """功法数据模型"""

    id: str
    name: str
    description: str
    skill_type: str  # cultivation, combat, passive
    realm_requirement: str | None = None
    experience_gain: int = 10
    damage: int = 0
    cooldown: int = 0
    created_at: datetime | None = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "skill_type": self.skill_type,
            "realm_requirement": self.realm_requirement,
            "experience_gain": self.experience_gain,
            "damage": self.damage,
            "cooldown": self.cooldown,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Skill":
        """从字典创建实例"""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            description=data.get("description"),
            skill_type=data.get("skill_type"),
            realm_requirement=data.get("realm_requirement"),
            experience_gain=data.get("experience_gain", 10),
            damage=data.get("damage", 0),
            cooldown=data.get("cooldown", 0),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
        )


@dataclass
class PlayerSkill:
    """玩家功法数据模型"""

    id: str
    player_id: str
    skill_id: str
    level: int = 1
    experience: int = 0
    created_at: datetime | None = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "player_id": self.player_id,
            "skill_id": self.skill_id,
            "level": self.level,
            "experience": self.experience,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
