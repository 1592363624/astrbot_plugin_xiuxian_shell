"""
境界数据模型
定义游戏中境界的数据结构
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Realm:
    """境界数据模型"""
    
    id: str
    name: str
    description: str
    level: int
    experience_required: int
    health_bonus: int = 0
    attack_bonus: int = 0
    defense_bonus: int = 0
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "level": self.level,
            "experience_required": self.experience_required,
            "health_bonus": self.health_bonus,
            "attack_bonus": self.attack_bonus,
            "defense_bonus": self.defense_bonus,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Realm":
        """从字典创建实例"""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            description=data.get("description"),
            level=data.get("level"),
            experience_required=data.get("experience_required"),
            health_bonus=data.get("health_bonus", 0),
            attack_bonus=data.get("attack_bonus", 0),
            defense_bonus=data.get("defense_bonus", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
        )
