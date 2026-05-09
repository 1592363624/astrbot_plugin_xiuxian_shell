"""
临时属性加成效果实现
使用物品后临时提升玩家的某项属性（攻击/防御等）
"""

from datetime import datetime, timedelta
from typing import Any
import uuid

from astrbot.api import logger

from ..base_effect import BaseEffect, EffectResult


class AddTempAttributeEffect(BaseEffect):
    """临时属性加成效果"""

    @property
    def effect_type(self) -> str:
        return "add_temp_attribute"

    async def trigger(
        self,
        player_id: str,
        params: dict[str, Any],
        db_manager: Any,
        cultivation_service: Any = None,
    ) -> EffectResult:
        """
        为玩家临时增加属性

        通过在数据库中记录临时 buff，战斗时读取 buff 值实现
        buff 过期自动失效

        Args:
            player_id: 玩家ID
            params: 效果参数，需包含：
                - attribute_type: 属性类型（attack/defense等）
                - attribute_value: 属性加成值
                - duration: 持续时间（秒）
            db_manager: 数据库管理器
            cultivation_service: 修炼服务（此效果不使用）

        Returns:
            EffectResult: 触发结果
        """
        attribute_type = params.get("attribute_type", "")
        attribute_value = params.get("attribute_value", 0)
        duration = params.get("duration", 3600)

        if not attribute_type or attribute_value <= 0:
            return EffectResult(
                success=False,
                error_msg="属性加成配置错误",
            )

        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=duration)

        record_id = str(uuid.uuid4())
        await db_manager.execute(
            """INSERT INTO temp_buffs (id, player_id, buff_type, buff_value, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                record_id,
                player_id,
                f"temp_{attribute_type}",
                attribute_value,
                now.isoformat(),
                expires_at.isoformat(),
            ),
        )
        await db_manager.commit()

        # 将持续时间转换为可读格式
        if duration >= 3600:
            time_desc = f"{duration // 3600}小时"
        elif duration >= 60:
            time_desc = f"{duration // 60}分钟"
        else:
            time_desc = f"{duration}秒"

        attr_name_map = {
            "attack": "攻击",
            "defense": "防御",
            "max_health": "生命上限",
            "speed": "速度",
        }
        attr_name = attr_name_map.get(attribute_type, attribute_type)

        logger.info(
            f"玩家 {player_id} 获得临时{attr_name}+{attribute_value}，持续 {time_desc}"
        )

        return EffectResult(
            success=True,
            effect_desc=f"{attr_name}+{attribute_value}（持续{time_desc}）",
            effect_params={
                "attribute_type": attribute_type,
                "attribute_name": attr_name,
                "attribute_value": attribute_value,
                "duration": duration,
                "time_desc": time_desc,
            },
        )
