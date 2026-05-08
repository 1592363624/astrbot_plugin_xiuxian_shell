"""
玩家API
提供玩家相关的接口，供命令层和后台管理调用
"""
from typing import Dict, Any, Optional
from aiohttp import web
from ..services import PlayerService, EventService
from ..utils.attributes import calc_battle_attrs


class PlayerAPI:
    """玩家API类"""

    def __init__(self, player_service: PlayerService):
        self.player_service = player_service
        self.event_service: Optional[EventService] = None

    def set_event_service(self, event_service: EventService):
        self.event_service = event_service

    async def create_player(self, user_id: str, username: str) -> str:
        try:
            player = await self.player_service.create_player(user_id, username)
            realm = await self.player_service.db.fetch_one(
                "SELECT name FROM realms WHERE id = ?",
                (player.realm_id,)
            )
            realm_name = realm["name"] if realm else "未知"
            return (
                f"注册成功！欢迎 {username} 进入修仙世界！\n"
                f"当前境界：{realm_name}\n"
                f"初始灵石：{player.spirit_stone}\n"
                f"———后天属性———\n"
                f"根骨:{player.bone} 神识:{player.spirit} 悟性:{player.intel}\n"
                f"体魄:{player.str_} 灵觉:{player.percep} 机缘:{player.luck}"
            )
        except ValueError as e:
            return str(e)
        except Exception as e:
            return f"注册失败：{str(e)}"

    async def get_player_status(self, user_id: str) -> str:
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        realm = await self.player_service.db.fetch_one(
            "SELECT name, level FROM realms WHERE id = ?",
            (player_dict["realm_id"],)
        )
        realm_name = realm["name"] if realm else "未知"
        realm_level = realm["level"] if realm else 1

        battle_attrs = calc_battle_attrs(
            level=realm_level,
            bone=player_dict["bone"],
            spirit=player_dict["spirit"],
            intel=player_dict["intel"],
            str_=player_dict["str"],
            percep=player_dict["percep"],
            luck=player_dict["luck"],
        )

        status = f"""
【修仙状态】
道号：{player_dict['username']}
境界：{realm_name}
修为：{player_dict['experience']}
灵石：{player_dict['spirit_stone']}
———战斗属性———
气血：{player_dict['health']}/{battle_attrs['max_health']}
法力：{player_dict['mp']}/{battle_attrs['max_mp']}
体力：{player_dict['stamina']}/{battle_attrs['max_stamina']}
物攻：{battle_attrs['attack']} 法攻：{battle_attrs['magic_attack']}
物防：{battle_attrs['defense']} 法防：{battle_attrs['magic_defense']}
速度：{battle_attrs['speed']} 闪避：{battle_attrs['dodge']:.1%}
———后天属性———
根骨:{player_dict['bone']} 神识:{player_dict['spirit']} 悟性:{player_dict['intel']}
体魄:{player_dict['str']} 灵觉:{player_dict['percep']} 机缘:{player_dict['luck']}
        """
        return status.strip()

    async def explore(self, user_id: str) -> str:
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            return error

        if self.event_service:
            result = await self.event_service.trigger_event(player_dict["id"], "explore")
            if result.get("triggered"):
                return result["message"]

        import random
        exp_gain = random.randint(5, 20)
        stone_gain = random.randint(1, 10)

        await self.player_service.modify_resource(player_dict["id"], "experience", exp_gain)
        await self.player_service.modify_resource(player_dict["id"], "spirit_stone", stone_gain)

        return f"你外出探索，获得 {exp_gain} 修为和 {stone_gain} 灵石"

    async def change_username(self, user_id: str, new_username: str) -> str:
        result, error = await self.player_service.change_username(user_id, new_username)
        if error:
            return f"修改失败：{error}"
        return f"道号修改成功！你的新道号为：{result}"

    # ==================== HTTP API接口 ====================

    async def api_get_all_players(self, request: web.Request) -> web.Response:
        page = int(request.query.get("page", 1))
        page_size = int(request.query.get("page_size", 20))
        result = await self.player_service.get_all_players(page, page_size)
        return web.json_response({"code": 0, "data": result})

    async def api_get_player(self, request: web.Request) -> web.Response:
        player_id = request.match_info["player_id"]
        player = await self.player_service.get_player_by_id(player_id)
        if not player:
            return web.json_response({"code": -1, "message": "玩家不存在"}, status=404)
        return web.json_response({"code": 0, "data": player.to_dict()})

    async def api_update_player(self, request: web.Request) -> web.Response:
        player_id = request.match_info["player_id"]
        data = await request.json()
        player = await self.player_service.update_player(player_id, **data)
        if not player:
            return web.json_response({"code": -1, "message": "玩家不存在"}, status=404)
        return web.json_response({"code": 0, "data": player.to_dict()})

    async def api_delete_player(self, request: web.Request) -> web.Response:
        player_id = request.match_info["player_id"]
        success = await self.player_service.delete_player(player_id)
        if not success:
            return web.json_response({"code": -1, "message": "删除失败"}, status=400)
        return web.json_response({"code": 0, "message": "删除成功"})
