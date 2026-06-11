"""
物品API
提供物品和储物袋相关的接口，包括丹药服用和新效果系统使用
"""

from typing import TYPE_CHECKING

from ..services import InventoryService, PlayerService

if TYPE_CHECKING:
    from ..services.item_effect_service import ItemEffectService


class ItemAPI:
    """物品API类"""

    def __init__(
        self,
        inventory_service: InventoryService,
        player_service: PlayerService,
        item_effect_service: "ItemEffectService" = None,
    ):
        """
        初始化物品API

        Args:
            inventory_service: 背包服务实例
            player_service: 玩家服务实例
            item_effect_service: 物品效果服务实例（新效果系统）
        """
        self.inventory_service = inventory_service
        self.player_service = player_service
        self.item_effect_service = item_effect_service

    async def get_inventory(self, user_id: str) -> str:
        """
        获取玩家储物袋

        Args:
            user_id: 用户ID

        Returns:
            储物袋信息
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        items = await self.inventory_service.get_player_inventory(player_dict["id"])

        if not items:
            return (
                f"【{player_dict['username']}的储物袋】\n空空如也，快去探索获取物品吧！"
            )

        inventory_text = f"【{player_dict['username']}的储物袋】\n"
        for item in items:
            inventory_text += f"- {item['name']} x{item['quantity']}\n"

        return inventory_text.strip()

    async def use_pill(self, user_id: str, item_name: str, quantity: int = 1) -> str:
        """
        服用丹药

        Args:
            user_id: 用户ID
            item_name: 丹药名称
            quantity: 服用数量

        Returns:
            str: 服用结果文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        try:
            result = await self.inventory_service.use_pill(
                player_dict["id"], item_name, quantity
            )
            return result.get("message", "服用异常")
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"服用失败：{str(e)}"

    async def get_toxicity_status(self, user_id: str) -> str:
        """
        获取丹毒状态

        Args:
            user_id: 用户ID

        Returns:
            str: 丹毒状态文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        status = await self.inventory_service.get_toxicity_status(player_dict["id"])

        if not status["has_toxicity"]:
            return "【丹毒状态】\n你体内并无丹毒积聚，经脉通畅。"

        lines = ["【丹毒状态】"]
        lines.append(f"当前丹毒总量：{status['total_toxicity']}点")
        lines.append("丹毒明细：")
        for record in status["active_records"]:
            lines.append(
                f"  - 【{record['item_name']}】丹毒{record['toxicity_value']}点"
            )

        lines.append("丹毒会影响闭关收益和炼制成功率，可使用【清灵丹】清除。")
        return "\n".join(lines)

    async def use_item(self, user_id: str, item_name: str, quantity: int = 1) -> str:
        """
        使用物品（新效果系统版本）
        支持条件校验、效果触发、提示生成

        Args:
            user_id: 用户ID
            item_name: 物品名称
            quantity: 使用数量

        Returns:
            str: 使用结果文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        if not self.item_effect_service:
            return "物品效果系统未初始化，请联系管理员"

        try:
            result = await self.inventory_service.use_item_with_effect_system(
                player_dict["id"],
                item_name,
                quantity,
                item_effect_service=self.item_effect_service,
            )
            return result.get("message", "使用异常")
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"使用失败：{str(e)}"
