"""
修炼API
提供闭关修炼、境界突破等接口
"""

from ..services import CultivationService, PlayerService


class CultivationAPI:
    """修炼API类"""

    def __init__(
        self, cultivation_service: CultivationService, player_service: PlayerService
    ):
        """
        初始化修炼API

        Args:
            cultivation_service: 修炼服务实例
            player_service: 玩家服务实例
        """
        self.cultivation_service = cultivation_service
        self.player_service = player_service

    async def seclusion(self, user_id: str) -> str:
        """
        闭关修炼

        Args:
            user_id: 用户ID

        Returns:
            str: 闭关结果文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        try:
            result = await self.cultivation_service.seclusion(player_dict["id"])
            return result.get("message", "闭关异常")
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"闭关失败：{str(e)}"

    async def get_seclusion_status(self, user_id: str) -> str:
        """
        获取闭关状态

        Args:
            user_id: 用户ID

        Returns:
            str: 闭关状态文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        status = await self.cultivation_service.get_seclusion_status(player_dict["id"])

        if status["can_seclude"]:
            return "你目前可以闭关修炼。"
        else:
            remaining = status["cooldown_remaining_minutes"]
            return f"你正在调息中，还需{remaining}分钟方可再次闭关。"

    async def breakthrough(self, user_id: str) -> str:
        """
        尝试境界突破

        Args:
            user_id: 用户ID

        Returns:
            str: 突破结果文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        try:
            result = await self.cultivation_service.breakthrough(player_dict["id"])
            return result.get("message", "突破异常")
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"突破失败：{str(e)}"
