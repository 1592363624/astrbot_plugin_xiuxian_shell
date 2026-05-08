"""
玩家数据模型
定义玩家相关的数据结构
包含先天基础属性（根骨、神识、悟性、体魄、灵觉、机缘）

注意：Python字段名 str_ 对应数据库列名 str 和API键名 str，
避免与Python内置类型 str 冲突
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Player:
    """
    玩家数据模型
    
    基础属性（先天属性）:
        bone: 根骨 - 决定气血上限、气血回复速度、物理防御，范围 3~15
        spirit: 神识 - 决定法力上限、法力回复速度、法术伤害、施法成功率，范围 3~15
        intel: 悟性 - 决定修炼速度、功法领悟成功率、炼丹炼器成功率，范围 3~15
        str_: 体魄 - 决定体力上限、近战伤害、负重，范围 3~15
        percep: 灵觉 - 决定闪避率、暴击率、探测隐藏/阵法发现率，范围 3~15
        luck: 机缘 - 影响随机事件触发率、掉落品质、奇遇概率，范围 1~10（独立）
    """
    
    id: str
    user_id: str
    username: str
    realm_id: str = "realm_001"
    experience: int = 0
    spirit_stone: int = 100
    health: int = 100
    max_health: int = 100
    mp: int = 50
    max_mp: int = 50
    stamina: int = 50
    max_stamina: int = 50
    attack: int = 10
    magic_attack: int = 5
    defense: int = 5
    magic_defense: int = 2
    speed: int = 10
    dodge: float = 0.0
    bone: int = 5
    spirit: int = 5
    intel: int = 5
    str_: int = 5
    percep: int = 5
    luck: int = 1
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
            "mp": self.mp,
            "max_mp": self.max_mp,
            "stamina": self.stamina,
            "max_stamina": self.max_stamina,
            "attack": self.attack,
            "magic_attack": self.magic_attack,
            "defense": self.defense,
            "magic_defense": self.magic_defense,
            "speed": self.speed,
            "dodge": self.dodge,
            "bone": self.bone,
            "spirit": self.spirit,
            "intel": self.intel,
            "str": self.str_,
            "percep": self.percep,
            "luck": self.luck,
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
            mp=data.get("mp", 50),
            max_mp=data.get("max_mp", 50),
            stamina=data.get("stamina", 50),
            max_stamina=data.get("max_stamina", 50),
            attack=data.get("attack", 10),
            magic_attack=data.get("magic_attack", 5),
            defense=data.get("defense", 5),
            magic_defense=data.get("magic_defense", 2),
            speed=data.get("speed", 10),
            dodge=data.get("dodge", 0.0),
            bone=data.get("bone", 5),
            spirit=data.get("spirit", 5),
            intel=data.get("intel", 5),
            str_=data.get("str", 5),
            percep=data.get("percep", 5),
            luck=data.get("luck", 1),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )
