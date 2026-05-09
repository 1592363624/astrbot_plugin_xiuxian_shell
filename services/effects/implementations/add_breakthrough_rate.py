"""
增加突破成功率效果实现
使用物品后临时提升玩家的突破成功率
"""

from datetime import datetime, timedelta
from typing import Any
import uuid

from astrbot.api import logger

from ..base_effect import BaseEffect, EffectResult


class AddBreakthroughRateEffect(BaseEffect):
    """增加突破成功率效果"""

    @property
    def effect_type(self) -> str:
        return "add_breakthrough_rate"

    async def trigger(
        self,
        player_id: str,
        params: dict[str, Any],
        db_manager: Any,
        cultivation_service: Any = None,
    ) -> EffectResult:
        """
        为玩家临时增加突破成功率

        通过在数据库中记录临时加成，突破时读取加成值实现
        加成默认持续24小时，过期自动失效

        Args:
            player_id: 玩家ID
            params: 效果参数，需包含 rate_value（成功率加成百分比）
            db_manager: 数据库管理器
            cultivation_service: 修炼服务（此效果不使用）

        Returns:
            EffectResult: 触发结果
        """
        rate_value = params.get("rate_value", 0)
        if rate_value <= 0:
            return EffectResult(
                success=False,
                error_msg="突破成功率加成数值配置错误",
            )

        # 持续时间默认24小时
        duration_hours = params.get("duration_hours", 24)
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=duration_hours)

        record_id = str(uuid.uuid4())
        await db_manager.execute(
            """INSERT INTO temp_buffs (id, player_id, buff_type, buff_value, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                record_id,
                player_id,
                "breakthrough_rate",
                rate_value,
                now.isoformat(),
                expires_at.isoformat(),
            ),
        )
        await db_manager.commit()

        logger.info(
            f"玩家 {player_id} 获得突破成功率加成 +{rate_value}%，持续 {duration_hours} 小时"
        )

        return EffectResult(
            success=True,
            effect_desc=f"突破成功率提升{rate_value}%（持续{duration_hours}小时）",
            effect_params={"rate_value": rate_value, "duration_hours": duration_hours},
        )
