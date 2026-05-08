"""
签到数据模型
定义签到记录相关的数据结构
"""
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional


@dataclass
class CheckinRecord:
    """
    签到记录数据模型

    属性说明:
        id: 记录唯一标识
        player_id: 玩家ID
        checkin_date: 签到日期 (YYYY-MM-DD)
        consecutive_days: 连续签到天数
        exp_reward: 本次签到获得的修为奖励
        created_at: 记录创建时间
    """

    id: str
    player_id: str
    checkin_date: str
    consecutive_days: int = 1
    exp_reward: int = 0
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "player_id": self.player_id,
            "checkin_date": self.checkin_date,
            "consecutive_days": self.consecutive_days,
            "exp_reward": self.exp_reward,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CheckinRecord":
        """从字典创建实例"""
        return cls(
            id=data.get("id"),
            player_id=data.get("player_id"),
            checkin_date=data.get("checkin_date"),
            consecutive_days=data.get("consecutive_days", 1),
            exp_reward=data.get("exp_reward", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
        )
