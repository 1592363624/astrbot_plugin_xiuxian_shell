"""
增加灵石效果实现
使用物品后为玩家增加灵石数量
"""

from typing import Any

from ..base_effect import BaseEffect, EffectResult


class AddSpiritStoneEffect(BaseEffect):
    """增加灵石效果"""

    @property
    def effect_type(self) -> str:
        return "add_spirit_stone"

    async def trigger(
        self,
        player_id: str,
        params: dict[str, Any],
        db_manager: Any,
        cultivation_service: Any = None,
    ) -> EffectResult:
        """
        为玩家增加灵石

        Args:
            player_id: 玩家ID
            params: 效果参数，需包含 stone_value（灵石数量）
            db_manager: 数据库管理器
            cultivation_service: 修炼服务（此效果不使用）

        Returns:
            EffectResult: 触发结果
        """
        stone_value = params.get("stone_value", 0)
        if stone_value <= 0:
            return EffectResult(
                success=False,
                error_msg="灵石增加数值配置错误",
            )

        await db_manager.execute(
            "UPDATE players SET spirit_stone = spirit_stone + ? WHERE id = ?",
            (stone_value, player_id),
        )
        await db_manager.commit()

        return EffectResult(
            success=True,
            effect_desc=f"获得{stone_value}枚灵石",
            effect_params={"stone_value": stone_value},
        )
