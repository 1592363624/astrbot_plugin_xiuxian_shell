"""
功法API
提供功法修炼相关的接口
"""
from typing import Dict, Any
from aiohttp import web
from ..services import CultivationService


class SkillAPI:
    """功法API类"""

    def __init__(self, cultivation_service: CultivationService):
        """
        初始化功法API
        
        Args:
            cultivation_service: 修炼服务实例
        """
        self.cultivation_service = cultivation_service

    async def cultivate(self, user_id: str) -> str:
        """
        修炼
        
        Args:
            user_id: 用户ID
            
        Returns:
            str: 修炼结果
        """
        # 获取玩家
        player = await self.cultivation_service.db.fetch_one(
            "SELECT id FROM players WHERE user_id = ?",
            (user_id,)
        )
        if not player:
            return "你还没有注册修仙角色，请先使用【修仙注册】"
        
        try:
            result = await self.cultivation_service.cultivate(player["id"])
            return result["message"]
        except Exception as e:
            return f"修炼失败：{str(e)}"

    async def breakthrough(self, user_id: str) -> str:
        """
        突破
        
        Args:
            user_id: 用户ID
            
        Returns:
            str: 突破结果
        """
        # 获取玩家
        player = await self.cultivation_service.db.fetch_one(
            "SELECT id FROM players WHERE user_id = ?",
            (user_id,)
        )
        if not player:
            return "你还没有注册修仙角色，请先使用【修仙注册】"
        
        try:
            result = await self.cultivation_service.breakthrough(player["id"])
            return result["message"]
        except Exception as e:
            return f"突破失败：{str(e)}"

    # ==================== HTTP API接口 ====================

    async def api_get_all_skills(self, request: web.Request) -> web.Response:
        """获取所有功法（HTTP API）"""
        skills = await self.cultivation_service.get_all_skills()
        return web.json_response({
            "code": 0,
            "data": [skill.to_dict() for skill in skills],
        })

    async def api_create_skill(self, request: web.Request) -> web.Response:
        """创建功法（HTTP API）"""
        data = await request.json()
        try:
            skill = await self.cultivation_service.create_skill(data)
            return web.json_response({"code": 0, "data": skill.to_dict()})
        except Exception as e:
            return web.json_response({"code": -1, "message": str(e)}, status=400)

    async def api_update_skill(self, request: web.Request) -> web.Response:
        """更新功法（HTTP API）"""
        skill_id = request.match_info["skill_id"]
        data = await request.json()
        skill = await self.cultivation_service.update_skill(skill_id, **data)
        if not skill:
            return web.json_response({"code": -1, "message": "功法不存在"}, status=404)
        return web.json_response({"code": 0, "data": skill.to_dict()})

    async def api_delete_skill(self, request: web.Request) -> web.Response:
        """删除功法（HTTP API）"""
        skill_id = request.match_info["skill_id"]
        success = await self.cultivation_service.delete_skill(skill_id)
        if not success:
            return web.json_response({"code": -1, "message": "删除失败"}, status=400)
        return web.json_response({"code": 0, "message": "删除成功"})

    async def api_get_all_realms(self, request: web.Request) -> web.Response:
        """获取所有境界（HTTP API）"""
        realms = await self.cultivation_service.get_all_realms()
        return web.json_response({
            "code": 0,
            "data": [realm.to_dict() for realm in realms],
        })

    async def api_create_realm(self, request: web.Request) -> web.Response:
        """创建境界（HTTP API）"""
        data = await request.json()
        try:
            realm = await self.cultivation_service.create_realm(data)
            return web.json_response({"code": 0, "data": realm.to_dict()})
        except Exception as e:
            return web.json_response({"code": -1, "message": str(e)}, status=400)

    async def api_update_realm(self, request: web.Request) -> web.Response:
        """更新境界（HTTP API）"""
        realm_id = request.match_info["realm_id"]
        data = await request.json()
        realm = await self.cultivation_service.update_realm(realm_id, **data)
        if not realm:
            return web.json_response({"code": -1, "message": "境界不存在"}, status=404)
        return web.json_response({"code": 0, "data": realm.to_dict()})

    async def api_delete_realm(self, request: web.Request) -> web.Response:
        """删除境界（HTTP API）"""
        realm_id = request.match_info["realm_id"]
        success = await self.cultivation_service.delete_realm(realm_id)
        if not success:
            return web.json_response({"code": -1, "message": "删除失败"}, status=400)
        return web.json_response({"code": 0, "message": "删除成功"})
