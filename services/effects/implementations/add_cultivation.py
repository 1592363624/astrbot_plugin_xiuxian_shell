"""
增加修为效果实现
使用物品后为玩家增加修为值
"""

from typing import Any

from ..base_effect import BaseEffect, EffectResult


class AddCultivationEffect(BaseEffect):
    """增加修为效果"""

    @property
    def effect_type(self) -> str:
        return "add_cultivation"

    async def trigger(
        self,
        player_id: str,
        params: dict[str, Any],
        db_manager: Any,
        cultivation_service: Any = None,
    ) -> EffectResult:
        """
        为玩家增加修为

        Args:
            player_id: 玩家ID
            params: 效果参数，需包含 cultivation_value（修为值）
            db_manager: 数据库管理器
            cultivation_service: 修炼服务（此效果不使用）

        Returns:
            EffectResult: 触发结果
        """
        cultivation_value = params.get("cultivation_value", 0)
        if cultivation_value <= 0:
            return EffectResult(
                success=False,
                error_msg="修为增加数值配置错误",
            )

        if cultivation_service:
            exp_result = await cultivation_service.add_experience(player_id, cultivation_value)
            actual = exp_result["actual_change"]
        else:
            await db_manager.execute(
                "UPDATE players SET experience = experience + ? WHERE id = ?",
                (cultivation_value, player_id),
            )
            await db_manager.commit()
            actual = cultivation_value

        return EffectResult(
            success=True,
            effect_desc=f"获得{actual}点修为",
            effect_params={"cultivation_value": actual},
        )
