"""
玩家状态检查服务
统一管理所有玩家状态的检查、通知与定时清理

职责:
- 突破提示: 修为达到境界上限时提示玩家突破（每天只提示一次）
- 丹毒清理: 定时清理过期丹毒记录
- 临时增益清理: 定时清理过期buff记录
- 自动突破: 对满足自动突破条件的境界执行自动突破

设计原则:
- 所有玩家状态检查的唯一入口，避免各服务分散检查导致遗漏
- 支持两种触发方式: 玩家发言时即时检查 + 定时tick批量检查
- 数据修改（截断、清理）仍在各服务中完成，本服务只负责检查和通知
"""

from ..utils import bj_now, to_db_iso
from typing import TYPE_CHECKING, Any

from astrbot.api import logger

from ..database import DatabaseManager

if TYPE_CHECKING:
    from .breakthrough_service import BreakthroughService
    from .cultivation_service import CultivationService
    from .inventory_service import InventoryService
    from .item_effect_service import ItemEffectService


class PlayerStateChecker:
    """
    玩家状态检查器
    统一检查玩家所有需要通知或处理的状态
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        cultivation_service: "CultivationService" = None,
        breakthrough_service: "BreakthroughService" = None,
        inventory_service: "InventoryService" = None,
        item_effect_service: "ItemEffectService" = None,
    ):
        """
        初始化玩家状态检查器

        Args:
            db_manager: 数据库管理器
            cultivation_service: 修炼服务
            breakthrough_service: 突破服务
            inventory_service: 背包服务
            item_effect_service: 物品效果服务
        """
        self.db = db_manager
        self.cultivation_service = cultivation_service
        self.breakthrough_service = breakthrough_service
        self.inventory_service = inventory_service
        self.item_effect_service = item_effect_service

    async def check_player_state(self, player_id: str) -> dict[str, Any]:
        """
        检查单个玩家的所有状态，返回待通知的消息和待执行的动作

        此方法为玩家状态检查的唯一入口，在玩家发言时由 on_message 调用，
        确保无论修为通过何种途径获得，都能正确触发状态通知。

        Args:
            player_id: 玩家ID

        Returns:
            Dict[str, Any]: {
                "messages": List[str], 待发送给玩家的通知消息列表,
                "needs_breakthrough": bool, 是否需要突破,
                "needs_auto_breakthrough": bool, 是否需要自动突破
            }
        """
        messages = []
        needs_breakthrough = False
        needs_auto_breakthrough = False
        condition_type = "none"

        # 1. 突破状态检查
        if self.cultivation_service:
            try:
                breakthrough_result = await self.cultivation_service.check_breakthrough_prompt(player_id)
                if breakthrough_result.get("prompt_message"):
                    messages.append(breakthrough_result["prompt_message"])
                if breakthrough_result.get("needs_breakthrough"):
                    needs_breakthrough = True
                    condition_type = breakthrough_result.get("condition_type", "none")
                    # manual 条件不需要自动突破尝试，提示已由 check_breakthrough_prompt 生成
                    if condition_type != "manual":
                        needs_auto_breakthrough = True
            except Exception as e:
                logger.error(f"玩家 {player_id} 突破状态检查失败: {e}")

        # 2. 丹毒过期清理（静默执行，不产生通知消息）
        if self.inventory_service:
            try:
                await self.inventory_service._cleanup_expired_toxicity(player_id)
            except Exception as e:
                logger.error(f"玩家 {player_id} 丹毒清理失败: {e}")

        # 3. 临时增益过期清理（静默执行，不产生通知消息）
        if self.item_effect_service:
            try:
                await self.item_effect_service.cleanup_expired_buffs(player_id)
            except Exception as e:
                logger.error(f"玩家 {player_id} 临时增益清理失败: {e}")

        return {
            "messages": messages,
            "needs_breakthrough": needs_breakthrough,
            "needs_auto_breakthrough": needs_auto_breakthrough,
            "condition_type": condition_type,
        }

    async def tick_all_players(self) -> list[dict[str, Any]]:
        """
        定时tick：批量检查所有在线玩家的状态

        用于定时任务中，检查所有玩家的状态并返回需要通知的结果。
        复用 check_breakthrough_prompt 统一突破检查逻辑，避免重复代码。

        Returns:
            List[Dict[str, Any]]: 需要通知的玩家列表，每项包含:
                - player_id: 玩家ID
                - user_id: 用户ID
                - messages: 通知消息列表
                - needs_auto_breakthrough: 是否需要自动突破
        """
        notifications = []

        players = await self.db.fetch_all(
            "SELECT id, user_id FROM players"
        )

        for player in players:
            player_id = player["id"]
            user_id = player["user_id"]
            player_messages = []

            # 复用统一状态检查方法
            try:
                state_result = await self.check_player_state(player_id)
                player_messages.extend(state_result.get("messages", []))
            except Exception as e:
                logger.error(f"tick: 玩家 {player_id} 状态检查失败: {e}")
                state_result = {}

            if player_messages or state_result.get("needs_breakthrough"):
                # 传播 condition_type，manual 条件不触发自动突破
                condition_type = state_result.get("condition_type", "none")
                needs_auto = state_result.get("needs_auto_breakthrough", False)
                notifications.append({
                    "player_id": player_id,
                    "user_id": user_id,
                    "messages": player_messages,
                    "needs_auto_breakthrough": needs_auto,
                    "condition_type": condition_type,
                })

        return notifications

    async def cleanup_all_expired(self) -> int:
        """
        批量清理所有玩家的过期数据（丹毒、临时增益）

        用于定时tick中，对全量玩家执行静默清理。

        Returns:
            int: 清理的记录总数
        """
        cleaned = 0
        now = bj_now()

        # 批量清理过期丹毒
        try:
            cursor = await self.db.execute(
                "DELETE FROM pill_toxicity_records WHERE expires_at <= ?",
                (to_db_iso(now),),
            )
            await self.db.commit()
            if cursor and hasattr(cursor, "rowcount"):
                cleaned += cursor.rowcount
        except Exception as e:
            logger.error(f"批量清理过期丹毒失败: {e}")

        # 批量清理过期临时增益
        try:
            cursor = await self.db.execute(
                "DELETE FROM temp_buffs WHERE expires_at <= ?",
                (to_db_iso(now),),
            )
            await self.db.commit()
            if cursor and hasattr(cursor, "rowcount"):
                cleaned += cursor.rowcount
        except Exception as e:
            logger.error(f"批量清理过期临时增益失败: {e}")

        return cleaned
