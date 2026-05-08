"""
物品API
提供物品和背包相关的接口
"""
from typing import Dict, Any

from ..services import InventoryService, PlayerService


class ItemAPI:
    """物品API类"""

    def __init__(self, inventory_service: InventoryService, player_service: PlayerService):
        """
        初始化物品API

        Args:
            inventory_service: 背包服务实例
            player_service: 玩家服务实例
        """
        self.inventory_service = inventory_service
        self.player_service = player_service

    async def get_inventory(self, user_id: str) -> str:
        """
        获取玩家背包

        Args:
            user_id: 用户ID

        Returns:
            背包信息
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        items = await self.inventory_service.get_player_inventory(player_dict["id"])

        if not items:
            return f"【{player_dict['username']}的背包】\n空空如也，快去探索获取物品吧！"

        inventory_text = f"【{player_dict['username']}的背包】\n"
        for item in items:
            rarity_map = {
                "common": "普通",
                "uncommon": "优秀",
                "rare": "稀有",
                "epic": "史诗",
                "legendary": "传说",
            }
            rarity = rarity_map.get(item.get("rarity", "common"), "普通")
            inventory_text += f"- {item['name']} x{item['quantity']} [{rarity}]\n"

        return inventory_text.strip()

    async def use_item(self, user_id: str, item_name: str) -> str:
        """
        使用物品

        Args:
            user_id: 用户ID
            item_name: 物品名称

        Returns:
            使用结果
        """
        if not item_name:
            return "请指定要使用的物品名称，格式：使用物品 <名称>"

        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        item = await self.inventory_service.get_item_by_name(item_name)
        if not item:
            return f"找不到物品【{item_name}】"

        try:
            result = await self.inventory_service.use_item(player_dict["id"], item.id)
            return result["message"]
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"使用物品失败：{str(e)}"
