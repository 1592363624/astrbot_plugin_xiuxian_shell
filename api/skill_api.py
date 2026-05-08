"""
功法API
提供功法修炼相关的接口
"""
from typing import Dict, Any

from ..services import CultivationService, PlayerService


class SkillAPI:
    """功法API类"""

    def __init__(self, cultivation_service: CultivationService, player_service: PlayerService):
        """
        初始化功法API

        Args:
            cultivation_service: 修炼服务实例
            player_service: 玩家服务实例
        """
        self.cultivation_service = cultivation_service
        self.player_service = player_service

    async def cultivate(self, user_id: str) -> str:
        """
        修炼

        Args:
            user_id: 用户ID

        Returns:
            修炼结果
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        try:
            result = await self.cultivation_service.cultivate(player_dict["id"])
            return result["message"]
        except Exception as e:
            return f"修炼失败：{str(e)}"

    async def breakthrough(self, user_id: str) -> str:
        """
        突破

        Args:
            user_id: 用户ID

        Returns:
            突破结果
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        try:
            result = await self.cultivation_service.breakthrough(player_dict["id"])
            return result["message"]
        except Exception as e:
            return f"突破失败：{str(e)}"
