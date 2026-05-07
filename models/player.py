"""
玩家数据模型
定义玩家相关的数据结构
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Player:
    """玩家数据模型"""
    
    id: str
    user_id: str
    username: str
    realm_id: str = "realm_001"
    experience: int = 0
    spirit_stone: int = 100
    health: int = 100
    max_health: int = 100
    attack: int = 10
    defense: int = 5
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "realm_id": self.realm_id,
            "experience": self.experience,
            "spirit_stone": self.spirit_stone,
            "health": self.health,
            "max_health": self.max_health,
            "attack": self.attack,
            "defense": self.defense,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        """从字典创建实例"""
        return cls(
            id=data.get("id"),
            user_id=data.get("user_id"),
            username=data.get("username"),
            realm_id=data.get("realm_id", "realm_001"),
            experience=data.get("experience", 0),
            spirit_stone=data.get("spirit_stone", 100),
            health=data.get("health", 100),
            max_health=data.get("max_health", 100),
            attack=data.get("attack", 10),
            defense=data.get("defense", 5),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )
