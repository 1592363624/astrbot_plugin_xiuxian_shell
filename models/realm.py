"""
境界数据模型
定义游戏中境界的数据结构
战斗属性由基础属性 + 境界等级通过公式动态计算，不存储在境界表中
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Realm:
    """
    境界数据模型
    
    属性说明:
        id: 境界唯一标识（如 realm_001）
        name: 境界名称（如 凡人、炼气初期）
        description: 境界描述
        level: 境界等级（1-43）
        experience_required: 升级所需修为经验
        breakthrough_probability: 基础突破概率（百分比）
        event_id: 基础事件编号
    """
    
    id: str
    name: str
    description: str
    level: int
    experience_required: int
    breakthrough_probability: int = 50
    event_id: int = 1
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "level": self.level,
            "experience_required": self.experience_required,
            "breakthrough_probability": self.breakthrough_probability,
            "event_id": self.event_id,
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
            breakthrough_probability=data.get("breakthrough_probability", 50),
            event_id=data.get("event_id", 1),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
        )
