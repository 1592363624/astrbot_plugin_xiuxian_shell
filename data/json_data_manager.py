"""
JSON数据管理器
负责游戏静态数据的JSON文件存储、加载和热重载

适用场景:
- 境界(Realm): 所有用户共享,游戏运行时不自动修改
- 物品(Item): 所有用户共享,游戏运行时不自动修改
- 功法(Skill): 所有用户共享,游戏运行时不自动修改
- 事件(Event): 所有用户共享,游戏运行时不自动修改

不符合JSON存储的数据(必须存数据库):
- 玩家背包(player_inventory): 每个用户独立的物品数量
- 玩家功法(player_skills): 每个用户独立学习的功法
- 玩家数据(players): 每个用户独立的修为、境界等
- 日志类数据: 签到记录、闭关记录等
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import aiofiles

from astrbot.api import logger


class JsonDataManager:
    """JSON数据管理器，支持热重载"""

    def __init__(self, data_dir: Path):
        """
        初始化JSON数据管理器

        Args:
            data_dir: 数据文件目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._data_cache: dict[str, list[dict[str, Any]]] = {}
        self._id_index_cache: dict[str, dict[str, dict[str, Any]]] = {}
        self._change_callbacks: dict[str, list[Callable]] = {}

    def register_change_callback(self, data_type: str, callback: Callable):
        """
        注册数据变更回调

        Args:
            data_type: 数据类型 (realms, items, skills, events)
            callback: 回调函数
        """
        if data_type not in self._change_callbacks:
            self._change_callbacks[data_type] = []
        self._change_callbacks[data_type].append(callback)

    async def _notify_change(self, data_type: str):
        """通知数据变更"""
        if data_type in self._change_callbacks:
            for callback in self._change_callbacks[data_type]:
                try:
                    await callback()
                except Exception as e:
                    logger.error(f"数据变更回调执行失败: {e}")

    async def load_data(self, data_type: str, default_data: list[dict[str, Any]] = None) -> list[dict[str, Any]]:
        """
        加载数据

        Args:
            data_type: 数据类型
            default_data: 默认数据(文件不存在时使用)

        Returns:
            List[Dict]: 数据列表
        """
        file_path = self.data_dir / f"{data_type}.json"

        if data_type in self._data_cache:
            return self._data_cache[data_type]

        if file_path.exists():
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
                    self._data_cache[data_type] = data
                    self._rebuild_index(data_type, data)
                    logger.info(f"已从文件加载{data_type}数据: {len(data)}条")
                    return data
            except Exception as e:
                logger.error(f"加载{data_type}数据失败: {e}")

        if default_data is not None:
            self._data_cache[data_type] = default_data
            self._rebuild_index(data_type, default_data)
            await self.save_data(data_type, default_data)
            logger.info(f"已使用默认数据初始化{data_type}: {len(default_data)}条")
            return default_data

        self._data_cache[data_type] = []
        return []

    async def save_data(self, data_type: str, data: list[dict[str, Any]] = None):
        """
        保存数据到文件

        Args:
            data_type: 数据类型
            data: 数据列表,None时使用缓存
        """
        if data is None:
            data = self._data_cache.get(data_type, [])

        file_path = self.data_dir / f"{data_type}.json"

        try:
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
            self._data_cache[data_type] = data
            self._rebuild_index(data_type, data)
            logger.info(f"已保存{data_type}数据到文件: {len(data)}条")
        except Exception as e:
            logger.error(f"保存{data_type}数据失败: {e}")

    def _rebuild_index(self, data_type: str, data: list[dict[str, Any]]):
        """重建ID索引"""
        self._id_index_cache[data_type] = {item["id"]: item for item in data if "id" in item}

    async def get_by_id(self, data_type: str, item_id: str) -> dict[str, Any] | None:
        """根据ID获取单条数据"""
        if data_type not in self._id_index_cache:
            await self.load_data(data_type)
        return self._id_index_cache.get(data_type, {}).get(item_id)

    async def get_all(self, data_type: str) -> list[dict[str, Any]]:
        """获取所有数据"""
        if data_type not in self._data_cache:
            await self.load_data(data_type)
        return self._data_cache.get(data_type, [])

    async def create(self, data_type: str, item_data: dict[str, Any]) -> dict[str, Any]:
        """
        创建新数据

        Args:
            data_type: 数据类型
            item_data: 数据项

        Returns:
            Dict: 创建的数据项
        """
        if "id" not in item_data:
            item_data["id"] = f"{data_type[:-1]}_{uuid.uuid4().hex[:8]}"
        item_data["created_at"] = datetime.utcnow().isoformat()

        data = await self.get_all(data_type)
        data.append(item_data)
        await self.save_data(data_type, data)
        await self._notify_change(data_type)

        return item_data

    async def update(self, data_type: str, item_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """
        更新数据

        Args:
            data_type: 数据类型
            item_id: 数据项ID
            updates: 更新字段

        Returns:
            Optional[Dict]: 更新后的数据项,不存在返回None
        """
        data = await self.get_all(data_type)
        for i, item in enumerate(data):
            if item["id"] == item_id:
                item.update(updates)
                data[i] = item
                await self.save_data(data_type, data)
                await self._notify_change(data_type)
                return item
        return None

    async def delete(self, data_type: str, item_id: str) -> bool:
        """
        删除数据

        Args:
            data_type: 数据类型
            item_id: 数据项ID

        Returns:
            bool: 是否删除成功
        """
        data = await self.get_all(data_type)
        original_len = len(data)
        data = [item for item in data if item["id"] != item_id]

        if len(data) < original_len:
            await self.save_data(data_type, data)
            await self._notify_change(data_type)
            return True
        return False

    async def reload(self, data_type: str):
        """重新加载数据(热重载)"""
        if data_type in self._data_cache:
            del self._data_cache[data_type]
        if data_type in self._id_index_cache:
            del self._id_index_cache[data_type]
        await self.load_data(data_type)
        await self._notify_change(data_type)
        logger.info(f"已热重载{data_type}数据")

    async def reload_all(self):
        """重新加载所有数据"""
        data_types = list(self._data_cache.keys())
        for data_type in data_types:
            await self.reload(data_type)
