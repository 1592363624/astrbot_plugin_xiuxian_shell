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
            # 从数据库动态读取初始境界名称
            realm = await self.player_service.db.fetch_one(
                "SELECT name FROM realms WHERE id = ?",
                (player.realm_id,)
            )
            realm_name = realm["name"] if realm else "未知"
            return (
                f"注册成功！欢迎 {username} 进入修仙世界！\n"
                f"当前境界：{realm_name}\n"
                f"初始灵石：{player.spirit_stone}\n"
                f"———先天属性———\n"
                f"根骨:{player.bone} 神识:{player.spirit} 悟性:{player.intel}\n"
                f"体魄:{player.str_} 灵觉:{player.percep} 机缘:{player.luck}"
            )
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
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        # 获取境界名称
        realm = await self.player_service.db.fetch_one(
            "SELECT name FROM realms WHERE id = ?",
            (player_dict["realm_id"],)
        )
        realm_name = realm["name"] if realm else "未知"

        status = f"""
【修仙状态】
道号：{player_dict['username']}
境界：{realm_name}
修为：{player_dict['experience']}
灵石：{player_dict['spirit_stone']}
———战斗属性———
气血：{player_dict['health']}/{player_dict['max_health']}
法力：{player_dict['mp']}/{player_dict['max_mp']}
体力：{player_dict['stamina']}/{player_dict['max_stamina']}
物攻：{player_dict['attack']} 法攻：{player_dict['magic_attack']}
物防：{player_dict['defense']} 法防：{player_dict['magic_defense']}
速度：{player_dict['speed']} 闪避：{player_dict['dodge']:.1%}
———先天属性———
根骨:{player_dict['bone']} 神识:{player_dict['spirit']} 悟性:{player_dict['intel']}
体魄:{player_dict['str']} 灵觉:{player_dict['percep']} 机缘:{player_dict['luck']}
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
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        if self.event_service:
            result = await self.event_service.trigger_event(player_dict["id"], "explore")
            if result.get("triggered"):
                return result["message"]

        # 默认探索结果
        import random
        exp_gain = random.randint(5, 20)
        stone_gain = random.randint(1, 10)

        await self.player_service.modify_resource(player_dict["id"], "experience", exp_gain)
        await self.player_service.modify_resource(player_dict["id"], "spirit_stone", stone_gain)

        return f"你外出探索，获得 {exp_gain} 修为和 {stone_gain} 灵石"

    async def change_username(self, user_id: str, new_username: str) -> str:
        """
        修改道号
        
        Args:
            user_id: 用户ID
            new_username: 新的道号
            
        Returns:
            str: 结果消息
        """
        result, error = await self.player_service.change_username(user_id, new_username)
        if error:
            return f"修改失败：{error}"
        return f"道号修改成功！你的新道号为：{result}"

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
