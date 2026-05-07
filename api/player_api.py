"""
玩家API
提供玩家相关的接口，供命令层和后台管理调用
"""
from typing import Dict, Any, Optional
from aiohttp import web
from ..services import PlayerService, EventService


class PlayerAPI:
    """玩家API类"""

    def __init__(self, player_service: PlayerService):
        """
        初始化玩家API
        
        Args:
            player_service: 玩家服务实例
        """
        self.player_service = player_service
        self.event_service: Optional[EventService] = None

    def set_event_service(self, event_service: EventService):
        """设置事件服务"""
        self.event_service = event_service

    async def create_player(self, user_id: str, username: str) -> str:
        """
        创建玩家
        
        Args:
            user_id: 用户ID
            username: 用户名
            
        Returns:
            str: 结果消息
        """
        try:
            player = await self.player_service.create_player(user_id, username)
            return f"注册成功！欢迎 {username} 进入修仙世界！\n当前境界：练气期\n初始灵石：100"
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"注册失败：{str(e)}"

    async def get_player_status(self, user_id: str) -> str:
        """
        获取玩家状态
        
        Args:
            user_id: 用户ID
            
        Returns:
            str: 状态信息
        """
        player = await self.player_service.get_player_by_user_id(user_id)
        if not player:
            return "你还没有注册修仙角色，请先使用【修仙注册】"
        
        # 获取境界信息
        from ..database import DatabaseManager
        realm = await self.player_service.db.fetch_one(
            "SELECT name FROM realms WHERE id = ?",
            (player.realm_id,)
        )
        realm_name = realm["name"] if realm else "未知"
        
        status = f"""
【修仙状态】
道号：{player.username}
境界：{realm_name}
修为：{player.experience}
灵石：{player.spirit_stone}
生命：{player.health}/{player.max_health}
攻击：{player.attack}
防御：{player.defense}
        """
        return status.strip()

    async def explore(self, user_id: str) -> str:
        """
        探索
        
        Args:
            user_id: 用户ID
            
        Returns:
            str: 探索结果
        """
        player = await self.player_service.get_player_by_user_id(user_id)
        if not player:
            return "你还没有注册修仙角色，请先使用【修仙注册】"
        
        if self.event_service:
            result = await self.event_service.trigger_event(player.id, "explore")
            if result.get("triggered"):
                return result["message"]
        
        # 默认探索结果
        import random
        exp_gain = random.randint(5, 20)
        stone_gain = random.randint(1, 10)
        
        await self.player_service.modify_resource(player.id, "experience", exp_gain)
        await self.player_service.modify_resource(player.id, "spirit_stone", stone_gain)
        
        return f"你外出探索，获得 {exp_gain} 修为和 {stone_gain} 灵石"

    # ==================== HTTP API接口 ====================

    async def api_get_all_players(self, request: web.Request) -> web.Response:
        """获取所有玩家（HTTP API）"""
        page = int(request.query.get("page", 1))
        page_size = int(request.query.get("page_size", 20))
        result = await self.player_service.get_all_players(page, page_size)
        return web.json_response({"code": 0, "data": result})

    async def api_get_player(self, request: web.Request) -> web.Response:
        """获取单个玩家详情（HTTP API）"""
        player_id = request.match_info["player_id"]
        player = await self.player_service.get_player_by_id(player_id)
        if not player:
            return web.json_response({"code": -1, "message": "玩家不存在"}, status=404)
        return web.json_response({"code": 0, "data": player.to_dict()})

    async def api_update_player(self, request: web.Request) -> web.Response:
        """更新玩家信息（HTTP API）"""
        player_id = request.match_info["player_id"]
        data = await request.json()
        player = await self.player_service.update_player(player_id, **data)
        if not player:
            return web.json_response({"code": -1, "message": "玩家不存在"}, status=404)
        return web.json_response({"code": 0, "data": player.to_dict()})

    async def api_delete_player(self, request: web.Request) -> web.Response:
        """删除玩家（HTTP API）"""
        player_id = request.match_info["player_id"]
        success = await self.player_service.delete_player(player_id)
        if not success:
            return web.json_response({"code": -1, "message": "删除失败"}, status=400)
        return web.json_response({"code": 0, "message": "删除成功"})
