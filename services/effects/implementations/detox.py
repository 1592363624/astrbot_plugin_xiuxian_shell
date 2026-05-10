"""
清除丹毒效果实现
使用物品后清除玩家体内所有丹毒
"""

from typing import Any

from ..base_effect import BaseEffect, EffectResult


class DetoxEffect(BaseEffect):
    """清除丹毒效果"""

    @property
    def effect_type(self) -> str:
        return "detox"

    async def trigger(
        self,
        player_id: str,
        params: dict[str, Any],
        db_manager: Any,
        cultivation_service: Any = None,
    ) -> EffectResult:
        """
        清除玩家体内所有丹毒

        Args:
            player_id: 玩家ID
            params: 效果参数（此效果无需额外参数）
            db_manager: 数据库管理器
            cultivation_service: 修炼服务（此效果不使用）

        Returns:
            EffectResult: 触发结果
        """
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone(timedelta(hours=8)))
        result = await db_manager.fetch_one(
            "SELECT COALESCE(SUM(toxicity_value), 0) as total FROM pill_toxicity_records WHERE player_id = ? AND expires_at > ?",
            (player_id, now.replace(tzinfo=None).isoformat()),
        )
        total_toxicity = result["total"] if result else 0

        await db_manager.execute(
            "DELETE FROM pill_toxicity_records WHERE player_id = ?",
            (player_id,),
        )
        await db_manager.commit()

        if total_toxicity > 0:
            return EffectResult(
                success=True,
                effect_desc=f"清除了{total_toxicity}点丹毒",
                effect_params={"cleared_toxicity": total_toxicity},
            )
        else:
            return EffectResult(
                success=True,
                effect_desc="体内并无丹毒积聚，药力温和滋养了经脉",
                effect_params={"cleared_toxicity": 0},
            )
