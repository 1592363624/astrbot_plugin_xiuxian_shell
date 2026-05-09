"""
玩家数据模型
定义玩家相关的数据结构

按照设计大纲，玩家表仅存储：
- 身份信息：id, user_id, username
- 游戏状态：realm_id, experience, spirit_stone
- 后天属性：bone, spirit, intel, str, percep, luck（初始为0，通过修炼/装备/机遇增长）
- 当前资源值：health, mp, stamina（战斗中会变化，需持久化）

战斗属性（衍生属性）由后天属性 + 境界等级通过公式动态计算，不存入数据库。
详见 utils/attributes.py 中的 calc_battle_attrs() 函数。

注意：Python字段名 str_ 对应数据库列名 str 和API键名 str，
避免与Python内置类型 str 冲突
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Player:
    """
    玩家数据模型

    后天属性（初始为0，通过修炼/装备/机遇增长）:
        bone: 根骨 - 决定气血上限、气血回复速度、物理防御
        spirit: 神识 - 决定法力上限、法力回复速度、法术伤害、施法成功率
        intel: 悟性 - 决定修炼速度、功法领悟成功率、炼丹炼器成功率
        str_: 体魄 - 决定体力上限、近战伤害、负重
        percep: 灵觉 - 决定闪避率、暴击率、探测隐藏/阵法发现率
        luck: 机缘 - 影响随机事件触发率、掉落品质、奇遇概率

    当前资源值（战斗中会变化）:
        health: 当前气血
        mp: 当前法力
        stamina: 当前体力

    战斗属性（衍生属性）动态计算，不存入数据库。
    """

    id: str
    user_id: str
    username: str
    realm_id: str = "realm_001"
    experience: int = 0
    spirit_stone: int = 100
    bone: int = 0
    spirit: int = 0
    intel: int = 0
    str_: int = 0
    percep: int = 0
    luck: int = 0
    health: int = 100
    mp: int = 50
    stamina: int = 50
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict:
        """转换为字典（仅包含数据库持久化字段）"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "realm_id": self.realm_id,
            "experience": self.experience,
            "spirit_stone": self.spirit_stone,
            "bone": self.bone,
            "spirit": self.spirit,
            "intel": self.intel,
            "str": self.str_,
            "percep": self.percep,
            "luck": self.luck,
            "health": self.health,
            "mp": self.mp,
            "stamina": self.stamina,
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
            bone=data.get("bone", 0),
            spirit=data.get("spirit", 0),
            intel=data.get("intel", 0),
            str_=data.get("str", 0),
            percep=data.get("percep", 0),
            luck=data.get("luck", 0),
            health=data.get("health", 100),
            mp=data.get("mp", 50),
            stamina=data.get("stamina", 50),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            updated_at=datetime.fromisoformat(data["updated_at"])
            if data.get("updated_at")
            else None,
        )
