"""
后台管理API
提供后台管理系统的HTTP接口
"""
from typing import Dict, Any
from aiohttp import web
from ..services import (
    PlayerService,
    CultivationService,
    CombatService,
    InventoryService,
    EventService,
)


class AdminAPI:
    """后台管理API类"""

    def __init__(
        self,
        player_service: PlayerService,
        cultivation_service: CultivationService,
        combat_service: CombatService,
        inventory_service: InventoryService,
        event_service: EventService,
    ):
        """
        初始化后台管理API
        
        Args:
            player_service: 玩家服务
            cultivation_service: 修炼服务
            combat_service: 战斗服务
            inventory_service: 背包服务
            event_service: 事件服务
        """
        self.player_service = player_service
        self.cultivation_service = cultivation_service
        self.combat_service = combat_service
        self.inventory_service = inventory_service
        self.event_service = event_service

    # ==================== 玩家管理 ====================

    async def get_all_players(self, request: web.Request) -> web.Response:
        """获取所有玩家"""
        page = int(request.query.get("page", 1))
        page_size = int(request.query.get("page_size", 20))
        result = await self.player_service.get_all_players(page, page_size)
        return web.json_response({"code": 0, "data": result})

    async def get_player_detail(self, request: web.Request) -> web.Response:
        """获取玩家详情"""
        player_id = request.match_info["player_id"]
        player = await self.player_service.get_player_by_id(player_id)
        if not player:
            return web.json_response({"code": -1, "message": "玩家不存在"}, status=404)
        
        # 获取背包信息
        inventory = await self.inventory_service.get_player_inventory(player_id)
        
        # 获取功法信息
        skills = await self.cultivation_service.db.fetch_all(
            """SELECT ps.*, s.name, s.description 
            FROM player_skills ps 
            JOIN skills s ON ps.skill_id = s.id 
            WHERE ps.player_id = ?""",
            (player_id,)
        )
        
        return web.json_response({
            "code": 0,
            "data": {
                "player": player.to_dict(),
                "inventory": inventory,
                "skills": skills,
            },
        })

    async def update_player(self, request: web.Request) -> web.Response:
        """更新玩家"""
        player_id = request.match_info["player_id"]
        data = await request.json()
        player = await self.player_service.update_player(player_id, **data)
        if not player:
            return web.json_response({"code": -1, "message": "玩家不存在"}, status=404)
        return web.json_response({"code": 0, "data": player.to_dict()})

    async def delete_player(self, request: web.Request) -> web.Response:
        """删除玩家"""
        player_id = request.match_info["player_id"]
        success = await self.player_service.delete_player(player_id)
        if not success:
            return web.json_response({"code": -1, "message": "删除失败"}, status=400)
        return web.json_response({"code": 0, "message": "删除成功"})

    # ==================== 物品管理 ====================

    async def get_all_items(self, request: web.Request) -> web.Response:
        """获取所有物品"""
        items = await self.inventory_service.get_all_items()
        return web.json_response({
            "code": 0,
            "data": [item.to_dict() for item in items],
        })

    async def create_item(self, request: web.Request) -> web.Response:
        """创建物品"""
        data = await request.json()
        try:
            item = await self.inventory_service.create_item(data)
            return web.json_response({"code": 0, "data": item.to_dict()})
        except Exception as e:
            return web.json_response({"code": -1, "message": str(e)}, status=400)

    async def update_item(self, request: web.Request) -> web.Response:
        """更新物品"""
        item_id = request.match_info["item_id"]
        data = await request.json()
        item = await self.inventory_service.update_item(item_id, **data)
        if not item:
            return web.json_response({"code": -1, "message": "物品不存在"}, status=404)
        return web.json_response({"code": 0, "data": item.to_dict()})

    async def delete_item(self, request: web.Request) -> web.Response:
        """删除物品"""
        item_id = request.match_info["item_id"]
        success = await self.inventory_service.delete_item(item_id)
        if not success:
            return web.json_response({"code": -1, "message": "删除失败"}, status=400)
        return web.json_response({"code": 0, "message": "删除成功"})

    # ==================== 功法管理 ====================

    async def get_all_skills(self, request: web.Request) -> web.Response:
        """获取所有功法"""
        skills = await self.cultivation_service.get_all_skills()
        return web.json_response({
            "code": 0,
            "data": [skill.to_dict() for skill in skills],
        })

    async def create_skill(self, request: web.Request) -> web.Response:
        """创建功法"""
        data = await request.json()
        try:
            skill = await self.cultivation_service.create_skill(data)
            return web.json_response({"code": 0, "data": skill.to_dict()})
        except Exception as e:
            return web.json_response({"code": -1, "message": str(e)}, status=400)

    async def update_skill(self, request: web.Request) -> web.Response:
        """更新功法"""
        skill_id = request.match_info["skill_id"]
        data = await request.json()
        skill = await self.cultivation_service.update_skill(skill_id, **data)
        if not skill:
            return web.json_response({"code": -1, "message": "功法不存在"}, status=404)
        return web.json_response({"code": 0, "data": skill.to_dict()})

    async def delete_skill(self, request: web.Request) -> web.Response:
        """删除功法"""
        skill_id = request.match_info["skill_id"]
        success = await self.cultivation_service.delete_skill(skill_id)
        if not success:
            return web.json_response({"code": -1, "message": "删除失败"}, status=400)
        return web.json_response({"code": 0, "message": "删除成功"})

    # ==================== 境界管理 ====================

    async def get_all_realms(self, request: web.Request) -> web.Response:
        """获取所有境界"""
        realms = await self.cultivation_service.get_all_realms()
        return web.json_response({
            "code": 0,
            "data": [realm.to_dict() for realm in realms],
        })

    async def create_realm(self, request: web.Request) -> web.Response:
        """创建境界"""
        data = await request.json()
        try:
            realm = await self.cultivation_service.create_realm(data)
            return web.json_response({"code": 0, "data": realm.to_dict()})
        except Exception as e:
            return web.json_response({"code": -1, "message": str(e)}, status=400)

    async def update_realm(self, request: web.Request) -> web.Response:
        """更新境界"""
        realm_id = request.match_info["realm_id"]
        data = await request.json()
        realm = await self.cultivation_service.update_realm(realm_id, **data)
        if not realm:
            return web.json_response({"code": -1, "message": "境界不存在"}, status=404)
        return web.json_response({"code": 0, "data": realm.to_dict()})

    async def delete_realm(self, request: web.Request) -> web.Response:
        """删除境界"""
        realm_id = request.match_info["realm_id"]
        success = await self.cultivation_service.delete_realm(realm_id)
        if not success:
            return web.json_response({"code": -1, "message": "删除失败"}, status=400)
        return web.json_response({"code": 0, "message": "删除成功"})

    # ==================== 事件管理 ====================

    async def get_all_events(self, request: web.Request) -> web.Response:
        """获取所有事件"""
        events = await self.event_service.get_all_events()
        return web.json_response({
            "code": 0,
            "data": [event.to_dict() for event in events],
        })

    async def create_event(self, request: web.Request) -> web.Response:
        """创建事件"""
        data = await request.json()
        try:
            event = await self.event_service.create_event(data)
            return web.json_response({"code": 0, "data": event.to_dict()})
        except Exception as e:
            return web.json_response({"code": -1, "message": str(e)}, status=400)

    async def update_event(self, request: web.Request) -> web.Response:
        """更新事件"""
        event_id = request.match_info["event_id"]
        data = await request.json()
        event = await self.event_service.update_event(event_id, **data)
        if not event:
            return web.json_response({"code": -1, "message": "事件不存在"}, status=404)
        return web.json_response({"code": 0, "data": event.to_dict()})

    async def delete_event(self, request: web.Request) -> web.Response:
        """删除事件"""
        event_id = request.match_info["event_id"]
        success = await self.event_service.delete_event(event_id)
        if not success:
            return web.json_response({"code": -1, "message": "删除失败"}, status=400)
        return web.json_response({"code": 0, "message": "删除成功"})

    # ==================== 配置管理 ====================

    async def get_config(self, request: web.Request) -> web.Response:
        """获取配置"""
        # 配置需要从数据库或配置文件读取
        return web.json_response({"code": 0, "data": {}})

    async def update_config(self, request: web.Request) -> web.Response:
        """更新配置"""
        data = await request.json()
        # 更新配置逻辑
        return web.json_response({"code": 0, "message": "配置更新成功"})

    # ==================== 数据统计 ====================

    async def get_game_stats(self, request: web.Request) -> web.Response:
        """获取游戏统计数据"""
        # 玩家总数
        player_count = await self.player_service.db.fetch_one(
            "SELECT COUNT(*) as count FROM players"
        )
        
        # 各境界玩家分布
        realm_distribution = await self.player_service.db.fetch_all(
            """SELECT r.name, COUNT(p.id) as count 
            FROM players p 
            JOIN realms r ON p.realm_id = r.id 
            GROUP BY r.name"""
        )
        
        # 总灵石流通量
        total_stones = await self.player_service.db.fetch_one(
            "SELECT SUM(spirit_stone) as total FROM players"
        )
        
        return web.json_response({
            "code": 0,
            "data": {
                "player_count": player_count["count"] if player_count else 0,
                "realm_distribution": realm_distribution,
                "total_spirit_stones": total_stones["total"] if total_stones else 0,
            },
        })
