"""
事件服务
处理游戏事件相关的业务逻辑

数据存储规范:
- 事件模板数据(game_events): 所有用户共享,存JSON文件
- 玩家事件记录(player_events): 每个用户独立,存数据库
"""

import random
import uuid
from typing import TYPE_CHECKING, Any

from ..database import DatabaseManager
from ..models import GameEvent

if TYPE_CHECKING:
    from ..data.json_data_manager import JsonDataManager
    from .cultivation_service import CultivationService


DEFAULT_EVENTS_DATA = [
    {"id": "event_001", "name": "灵草奇遇", "description": "你在山间发现了一株灵草", "event_type": "explore", "trigger_condition": "explore", "reward_type": "item", "reward_value": "item_007", "probability": 0.3, "is_active": True},
    {"id": "event_002", "name": "妖兽袭击", "description": "一只妖兽突然出现", "event_type": "combat", "trigger_condition": "explore", "reward_type": "spirit_stone", "reward_value": 50, "probability": 0.2, "is_active": True},
    {"id": "event_003", "name": "顿悟", "description": "灵光一闪，你对修炼有了新的领悟", "event_type": "cultivation", "trigger_condition": "cultivate", "reward_type": "experience", "reward_value": 100, "probability": 0.15, "is_active": True},
    {"id": "event_004", "name": "奇遇：前辈遗物", "description": "你发现了一位前辈的洞府遗迹", "event_type": "explore", "trigger_condition": "seclusion", "reward_type": "item", "reward_value": "item_008", "probability": 0.1, "is_active": True},
    {"id": "event_005", "name": "天降横财", "description": "天上掉下了一块灵石", "event_type": "random", "trigger_condition": "random", "reward_type": "spirit_stone", "reward_value": 200, "probability": 0.05, "is_active": True},
    {"id": "event_006", "name": "福缘深厚", "description": "你感觉今日运气极佳", "event_type": "random", "trigger_condition": "random", "reward_type": "experience", "reward_value": 500, "probability": 0.08, "is_active": True},
    {"id": "event_007", "name": "闭关奇遇：灵气潮汐", "description": "闭关时遭遇灵气潮汐", "event_type": "cultivation", "trigger_condition": "seclusion", "reward_type": "experience", "reward_value": 1000, "probability": 0.12, "is_active": True},
    {"id": "event_008", "name": "探险发现", "description": "在山洞深处发现了一块蕴含灵气的矿石", "event_type": "explore", "trigger_condition": "explore", "reward_type": "spirit_stone", "reward_value": 150, "probability": 0.25, "is_active": True},
]


class EventService:
    """事件服务类"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        json_data_manager: "JsonDataManager" = None,
        cultivation_service: "CultivationService" = None,
    ):
        """
        初始化事件服务

        Args:
            db_manager: 数据库管理器实例
            json_data_manager: JSON数据管理器实例
            cultivation_service: 修炼服务实例(用于获取境界信息)
        """
        self.db = db_manager
        self.json_data_manager = json_data_manager
        self.cultivation_service = cultivation_service
        self._events_cache: dict[str, GameEvent] = {}
        self._events_loaded = False

    async def _ensure_events_loaded(self):
        """确保事件数据已加载"""
        if not self._events_loaded and self.json_data_manager:
            await self.json_data_manager.load_data("events", DEFAULT_EVENTS_DATA)
            all_events = await self.json_data_manager.get_all("events")
            self._events_cache = {event["id"]: GameEvent.from_dict(event) for event in all_events}
            self._events_loaded = True

    async def _reload_events_cache(self):
        """重新加载事件缓存"""
        if self.json_data_manager:
            await self.json_data_manager.reload("events")
            all_events = await self.json_data_manager.get_all("events")
            self._events_cache = {event["id"]: GameEvent.from_dict(event) for event in all_events}
        self._events_loaded = True

    async def trigger_event(self, player_id: str, event_type: str) -> dict[str, Any]:
        """
        触发事件

        Args:
            player_id: 玩家ID
            event_type: 事件类型

        Returns:
            Dict[str, Any]: 事件结果
        """
        await self._ensure_events_loaded()

        active_events = [
            event for event in self._events_cache.values()
            if event.is_active and event.trigger_condition == event_type
        ]

        if not active_events:
            return {
                "triggered": False,
                "message": "没有可触发的事件",
            }

        for event in active_events:
            if random.random() < event.probability:
                await self._record_event_trigger(player_id, event.id)
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
            await self.db.execute(
                "UPDATE players SET spirit_stone = spirit_stone + ? WHERE id = ?",
                (event.reward_value, player_id),
            )
            await self.db.commit()
            return f"获得 {event.reward_value} 灵石"

        elif event.reward_type == "experience":
            if self.cultivation_service:
                exp_result = await self.cultivation_service.add_experience(player_id, event.reward_value)
                actual = exp_result["actual_change"]
            else:
                await self.db.execute(
                    "UPDATE players SET experience = experience + ? WHERE id = ?",
                    (event.reward_value, player_id),
                )
                await self.db.commit()
                actual = event.reward_value
            return f"获得 {actual} 点修为"

        elif event.reward_type == "item":
            return "获得了一些物品"

        elif event.reward_type == "health":
            player = await self.db.fetch_one(
                "SELECT * FROM players WHERE id = ?",
                (player_id,),
            )
            if player and self.cultivation_service:
                realm = await self.cultivation_service.get_realm_by_id(player["realm_id"])
                realm_level = realm.level if realm else 1
            elif player:
                realm_level = player.get("realm_level", 1)
            else:
                realm_level = 1

            if player:
                from ..utils.attributes import calc_battle_attrs

                battle_attrs = calc_battle_attrs(
                    level=realm_level,
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

    async def trigger_random_event(self, player_id: str) -> dict[str, Any]:
        """触发随机事件"""
        await self._ensure_events_loaded()

        active_events = [
            event for event in self._events_cache.values()
            if event.is_active and event.trigger_condition == "random"
        ]

        if not active_events:
            return {
                "triggered": False,
                "message": "没有可触发的事件",
            }

        for event in active_events:
            if random.random() < event.probability:
                await self._record_event_trigger(player_id, event.id)
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

    async def get_active_events_by_trigger(self, trigger: str) -> list[GameEvent]:
        """根据触发条件获取激活的事件"""
        await self._ensure_events_loaded()
        return [
            event for event in self._events_cache.values()
            if event.is_active and event.trigger_condition == trigger
        ]

    # ==================== 事件管理(使用JSON存储) ====================

    async def get_event_by_id(self, event_id: str) -> GameEvent | None:
        """根据ID获取事件"""
        await self._ensure_events_loaded()
        return self._events_cache.get(event_id)

    async def get_all_events(self) -> list[GameEvent]:
        """获取所有事件"""
        await self._ensure_events_loaded()
        return list(self._events_cache.values())

    async def create_event(self, event_data: dict[str, Any]) -> GameEvent:
        """创建事件"""
        await self._ensure_events_loaded()
        new_event = await self.json_data_manager.create("events", event_data)
        event = GameEvent.from_dict(new_event)
        self._events_cache[event.id] = event
        return event

    async def update_event(self, event_id: str, **kwargs) -> GameEvent | None:
        """更新事件"""
        await self._ensure_events_loaded()
        updated = await self.json_data_manager.update("events", event_id, kwargs)
        if updated:
            event = GameEvent.from_dict(updated)
            self._events_cache[event.id] = event
            return event
        return None

    async def delete_event(self, event_id: str) -> bool:
        """删除事件"""
        await self._ensure_events_loaded()
        success = await self.json_data_manager.delete("events", event_id)
        if success and event_id in self._events_cache:
            del self._events_cache[event_id]
        return success
