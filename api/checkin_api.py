"""
签到API
提供签到相关的接口，供命令层和后台管理调用
"""
from typing import Dict, Any
from aiohttp import web
from ..services import CheckinService, PlayerService


class CheckinAPI:
    """签到API类"""

    def __init__(self, checkin_service: CheckinService, player_service: PlayerService):
        """
        初始化签到API

        Args:
            checkin_service: 签到服务实例
            player_service: 玩家服务实例
        """
        self.checkin_service = checkin_service
        self.player_service = player_service

    async def checkin(self, user_id: str) -> str:
        """
        执行签到（命令层调用）

        Args:
            user_id: 用户ID

        Returns:
            str: 签到结果消息
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        try:
            result = await self.checkin_service.checkin(player_dict["id"])
            return result["message"]
        except Exception as e:
            return f"签到失败：{str(e)}"

    async def get_checkin_status(self, user_id: str) -> str:
        """
        查询签到状态（命令层调用）

        Args:
            user_id: 用户ID

        Returns:
            str: 签到状态消息
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        try:
            status = await self.checkin_service.get_checkin_status(player_dict["id"])
            tiers = status["reward_tiers"]
            today_status = "✅ 已签到" if status["checked_in_today"] else "❌ 未签到"

            msg = (
                f"【签到状态】\n"
                f"今日状态：{today_status}\n"
                f"连续签到：{status['consecutive_days']} 天"
            )
            if status["last_checkin_date"]:
                msg += f"\n上次签到：{status['last_checkin_date']}"
            if status["last_exp_reward"] and status["checked_in_today"]:
                msg += f"\n今日获得：+{status['last_exp_reward']} 修为"
            msg += (
                f"\n\n【奖励规则】\n"
                f"每日签到：{tiers['base']}% 升级修为\n"
                f"连续3天：{tiers['three_day']}% 升级修为\n"
                f"连续7天：{tiers['seven_day']}% 升级修为"
            )
            return msg
        except Exception as e:
            return f"查询失败：{str(e)}"

    async def get_checkin_ranking(self, user_id: str) -> str:
        """
        查询签到排行（命令层调用）

        Args:
            user_id: 用户ID

        Returns:
            str: 排行消息
        """
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        try:
            ranking = await self.checkin_service.get_checkin_ranking(10)
            if not ranking:
                return "暂无签到排行数据"

            msg = "【签到排行榜】\n"
            for idx, record in enumerate(ranking, 1):
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, f"{idx}.")
                msg += (
                    f"{medal} {record['username']} - "
                    f"连续 {record['consecutive_days']} 天\n"
                )
            return msg.strip()
        except Exception as e:
            return f"查询失败：{str(e)}"

    # ==================== HTTP API接口 ====================

    async def api_checkin(self, request: web.Request) -> web.Response:
        """执行签到（HTTP API）"""
        data = await request.json()
        player_id = data.get("player_id")
        if not player_id:
            return web.json_response({"code": -1, "message": "缺少 player_id"}, status=400)

        try:
            result = await self.checkin_service.checkin(player_id)
            return web.json_response({"code": 0, "data": result})
        except Exception as e:
            return web.json_response({"code": -1, "message": str(e)}, status=400)

    async def api_get_status(self, request: web.Request) -> web.Response:
        """获取签到状态（HTTP API）"""
        player_id = request.match_info["player_id"]
        try:
            status = await self.checkin_service.get_checkin_status(player_id)
            return web.json_response({"code": 0, "data": status})
        except Exception as e:
            return web.json_response({"code": -1, "message": str(e)}, status=400)

    async def api_get_records(self, request: web.Request) -> web.Response:
        """获取玩家签到记录（HTTP API）"""
        player_id = request.match_info["player_id"]
        limit = int(request.query.get("limit", 30))
        try:
            records = await self.checkin_service.get_player_checkin_records(player_id, limit)
            return web.json_response({"code": 0, "data": records})
        except Exception as e:
            return web.json_response({"code": -1, "message": str(e)}, status=400)

    async def api_get_ranking(self, request: web.Request) -> web.Response:
        """获取签到排行（HTTP API）"""
        limit = int(request.query.get("limit", 10))
        try:
            ranking = await self.checkin_service.get_checkin_ranking(limit)
            return web.json_response({"code": 0, "data": ranking})
        except Exception as e:
            return web.json_response({"code": -1, "message": str(e)}, status=400)

    async def api_get_all_records(self, request: web.Request) -> web.Response:
        """获取所有签到记录（HTTP API，后台管理用）"""
        page = int(request.query.get("page", 1))
        page_size = int(request.query.get("page_size", 20))
        try:
            result = await self.checkin_service.get_all_checkin_records(page, page_size)
            return web.json_response({"code": 0, "data": result})
        except Exception as e:
            return web.json_response({"code": -1, "message": str(e)}, status=400)
