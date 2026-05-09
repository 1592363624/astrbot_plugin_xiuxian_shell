"""
事件服务
处理游戏事件相关的业务逻辑
"""

import random
import uuid
from typing import Any

from ..database import DatabaseManager
from ..models import GameEvent


class EventService:
    """事件服务类"""

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化事件服务

        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager

    async def trigger_event(self, player_id: str, event_type: str) -> dict[str, Any]:
        """
        触发事件

        Args:
            player_id: 玩家ID
            event_type: 事件类型

        Returns:
            Dict[str, Any]: 事件结果
        """
        # 获取所有激活的该类型事件
        sql = "SELECT * FROM game_events WHERE event_type = ? AND is_active = 1"
        events = await self.db.fetch_all(sql, (event_type,))

        if not events:
            return {
                "triggered": False,
                "message": "没有可触发的事件",
            }

        # 根据概率随机选择事件
        for event_data in events:
            if random.random() < event_data["probability"]:
                event = GameEvent.from_dict(event_data)

                # 记录事件触发
                await self._record_event_trigger(player_id, event.id)

                # 处理事件奖励
                reward_message = await self._process_event_reward(player_id, event)

                return {
                    "triggered": True,
                    "event_name": event.name,
                    "event_description": event.description,
                    "reward_message": reward_message,
                    "message": f"【{event.name}】{event.description}。{reward_message}",
                }

        return {
            "triggered": False,
            "message": "风平浪静，什么都没发生",
        }

    async def _record_event_trigger(self, player_id: str, event_id: str):
        """记录事件触发"""
        record_id = str(uuid.uuid4())
        sql = "INSERT INTO player_events (id, player_id, event_id) VALUES (?, ?, ?)"
        await self.db.execute(sql, (record_id, player_id, event_id))
        await self.db.commit()

    async def _process_event_reward(self, player_id: str, event: GameEvent) -> str:
        """
        处理事件奖励

        Args:
            player_id: 玩家ID
            event: 事件对象

        Returns:
            str: 奖励描述
        """
        if not event.reward_type:
            return ""

        if event.reward_type == "spirit_stone":
            # 灵石奖励
            await self.db.execute(
                "UPDATE players SET spirit_stone = spirit_stone + ? WHERE id = ?",
                (event.reward_value, player_id),
            )
            await self.db.commit()
            return f"获得 {event.reward_value} 灵石"

        elif event.reward_type == "experience":
            # 修为奖励
            await self.db.execute(
                "UPDATE players SET experience = experience + ? WHERE id = ?",
                (event.reward_value, player_id),
            )
            await self.db.commit()
            return f"获得 {event.reward_value} 点修为"

        elif event.reward_type == "item":
            # 物品奖励（需要在事件配置中指定item_id）
            return "获得了一些物品"

        elif event.reward_type == "health":
            player = await self.db.fetch_one(
                "SELECT p.*, r.level as realm_level FROM players p JOIN realms r ON p.realm_id = r.id WHERE p.id = ?",
                (player_id,),
            )
            if player:
                from ..utils.attributes import calc_battle_attrs

                battle_attrs = calc_battle_attrs(
                    level=player["realm_level"],
                    bone=player["bone"],
                    spirit=player["spirit"],
                    intel=player["intel"],
                    str_=player["str"],
                    percep=player["percep"],
                    luck=player["luck"],
                )
                max_health = battle_attrs["max_health"]
            else:
                max_health = 100
            await self.db.execute(
                "UPDATE players SET health = MIN(?, health + ?) WHERE id = ?",
                (max_health, event.reward_value, player_id),
            )
            await self.db.commit()
            if event.reward_value > 0:
                return f"恢复了 {event.reward_value} 点生命值"
            else:
                return f"损失了 {abs(event.reward_value)} 点生命值"

        return ""

    # ==================== 事件管理 ====================

    async def get_event_by_id(self, event_id: str) -> GameEvent | None:
        """根据ID获取事件"""
        sql = "SELECT * FROM game_events WHERE id = ?"
        row = await self.db.fetch_one(sql, (event_id,))
        if row:
            return GameEvent.from_dict(row)
        return None

    async def get_all_events(self) -> list[GameEvent]:
        """获取所有事件"""
        sql = "SELECT * FROM game_events ORDER BY id"
        rows = await self.db.fetch_all(sql)
        return [GameEvent.from_dict(row) for row in rows]

    async def create_event(self, event_data: dict[str, Any]) -> GameEvent:
        """创建事件"""
        event_id = event_data.get("id", str(uuid.uuid4()))
        sql = """
            INSERT INTO game_events (id, name, description, event_type, trigger_condition, reward_type, reward_value, probability, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        await self.db.execute(
            sql,
            (
                event_id,
                event_data["name"],
                event_data.get("description"),
                event_data["event_type"],
                event_data.get("trigger_condition"),
                event_data.get("reward_type"),
                event_data.get("reward_value", 0),
                event_data.get("probability", 0.5),
                event_data.get("is_active", 1),
            ),
        )
        await self.db.commit()
        return await self.get_event_by_id(event_id)

    async def update_event(self, event_id: str, **kwargs) -> GameEvent | None:
        """更新事件"""
        allowed_fields = [
            "name",
            "description",
            "event_type",
            "trigger_condition",
            "reward_type",
            "reward_value",
            "probability",
            "is_active",
        ]
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)

        if not updates:
            return await self.get_event_by_id(event_id)

        values.append(event_id)
        sql = f"UPDATE game_events SET {', '.join(updates)} WHERE id = ?"
        await self.db.execute(sql, tuple(values))
        await self.db.commit()
        return await self.get_event_by_id(event_id)

    async def delete_event(self, event_id: str) -> bool:
        """删除事件"""
        sql = "DELETE FROM game_events WHERE id = ?"
        cursor = await self.db.execute(sql, (event_id,))
        await self.db.commit()
        return cursor.rowcount > 0
