"""
深度闭关API
提供深度闭关、避世入世、死亡惩罚等接口
"""

from ..services import DeepSeclusionService, PlayerService


class DeepSeclusionAPI:
    """深度闭关API类"""

    def __init__(
        self,
        deep_seclusion_service: DeepSeclusionService,
        player_service: PlayerService,
    ):
        """
        初始化深度闭关API

        Args:
            deep_seclusion_service: 深度闭关服务实例
            player_service: 玩家服务实例
        """
        self.deep_seclusion_service = deep_seclusion_service
        self.player_service = player_service

    async def start_deep_seclusion(self, user_id: str) -> str:
        """
        开启深度闭关

        Args:
            user_id: 用户ID

        Returns:
            str: 闭关结果文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        try:
            result = await self.deep_seclusion_service.start_deep_seclusion(
                player_dict["id"]
            )
            return result.get("message", "深度闭关异常")
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"深度闭关失败：{str(e)}"

    async def get_deep_seclusion_status(self, user_id: str) -> str:
        """
        查看深度闭关状态

        Args:
            user_id: 用户ID

        Returns:
            str: 闭关状态文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        try:
            status = await self.deep_seclusion_service.get_deep_seclusion_status(
                player_dict["id"]
            )
            return status.get("message", "查询状态异常")
        except Exception as e:
            return f"查询失败：{str(e)}"

    async def force_end_deep_seclusion(self, user_id: str) -> str:
        """
        强行出关

        Args:
            user_id: 用户ID

        Returns:
            str: 出关结果文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        try:
            result = await self.deep_seclusion_service.force_end_deep_seclusion(
                player_dict["id"]
            )
            return result.get("message", "强行出关异常")
        except Exception as e:
            return f"强行出关失败：{str(e)}"

    async def settle_deep_seclusion(self, user_id: str) -> str | None:
        """
        结算深度闭关

        在玩家下次发言时自动调用。

        Args:
            user_id: 用户ID

        Returns:
            Optional[str]: 结算结果文本，无未结算记录返回None
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return None

        try:
            result = await self.deep_seclusion_service.settle_deep_seclusion(
                player_dict["id"]
            )
            if result:
                return result.get("message")
            return None
        except Exception as e:
            return f"结算失败：{str(e)}"

    async def enter_peace_mode(self, user_id: str) -> str:
        """
        开启避世模式

        Args:
            user_id: 用户ID

        Returns:
            str: 操作结果文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        try:
            result = await self.deep_seclusion_service.enter_peace_mode(
                player_dict["id"]
            )
            return result.get("message", "避世异常")
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"避世失败：{str(e)}"

    async def exit_peace_mode(self, user_id: str) -> str:
        """
        关闭避世模式（入世）

        Args:
            user_id: 用户ID

        Returns:
            str: 操作结果文本
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        try:
            result = await self.deep_seclusion_service.exit_peace_mode(
                player_dict["id"]
            )
            return result.get("message", "入世异常")
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"入世失败：{str(e)}"
