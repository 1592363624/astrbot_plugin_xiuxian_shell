"""
恢复生命值效果实现
使用物品后为玩家恢复生命值，不超过生命值上限
"""

from typing import Any

from ..base_effect import BaseEffect, EffectResult


class HealEffect(BaseEffect):
    """恢复生命值效果"""

    @property
    def effect_type(self) -> str:
        return "heal"

    async def trigger(
        self,
        player_id: str,
        params: dict[str, Any],
        db_manager: Any,
        cultivation_service: Any = None,
    ) -> EffectResult:
        """
        为玩家恢复生命值

        Args:
            player_id: 玩家ID
            params: 效果参数，需包含 heal_value（恢复值）
            db_manager: 数据库管理器
            cultivation_service: 修炼服务（用于获取境界等级计算生命上限）

        Returns:
            EffectResult: 触发结果
        """
        heal_value = params.get("heal_value", 0)
        if heal_value <= 0:
            return EffectResult(
                success=False,
                error_msg="生命恢复数值配置错误",
            )

        player = await db_manager.fetch_one(
            "SELECT * FROM players WHERE id = ?", (player_id,)
        )
        if not player:
            return EffectResult(success=False, error_msg="玩家不存在")

        # 计算生命值上限
        max_health = 100
        if cultivation_service:
            try:
                realm = await cultivation_service.get_realm_by_id(player["realm_id"])
                realm_level = realm.level if realm else 1
            except Exception:
                realm_level = player.get("realm_level", 1)
        else:
            realm_level = player.get("realm_level", 1)

        from ....utils.attributes import calc_battle_attrs

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

        # 恢复生命值，不超过上限
        await db_manager.execute(
            "UPDATE players SET health = MIN(?, health + ?) WHERE id = ?",
            (max_health, heal_value, player_id),
        )
        await db_manager.commit()

        return EffectResult(
            success=True,
            effect_desc=f"恢复了{heal_value}点生命值",
            effect_params={"heal_value": heal_value},
        )
