"""
后台管理API
提供后台管理系统的HTTP接口，兼容AstrBot Dashboard(Quart)路由分发机制
"""
from pathlib import Path
from typing import Dict, Any, TYPE_CHECKING
from quart import jsonify, request, Response as QuartResponse

from ..services import (
    PlayerService,
    CultivationService,
    CombatService,
    InventoryService,
    EventService,
)

if TYPE_CHECKING:
    from ..config import ConfigManager


class AdminAPI:
    """后台管理API类"""

    def __init__(
        self,
        player_service: PlayerService,
        cultivation_service: CultivationService,
        combat_service: CombatService,
        inventory_service: InventoryService,
        event_service: EventService,
        config_manager: "ConfigManager",
    ):
        """
        初始化后台管理API

        Args:
            player_service: 玩家服务
            cultivation_service: 修炼服务
            combat_service: 战斗服务
            inventory_service: 背包服务
            event_service: 事件服务
            config_manager: 配置管理器
        """
        self.player_service = player_service
        self.cultivation_service = cultivation_service
        self.combat_service = combat_service
        self.inventory_service = inventory_service
        self.event_service = event_service
        self.config_manager = config_manager

    async def serve_admin_page(self):
        """直接返回后台管理HTML页面，支持独立URL访问"""
        html_path = Path(__file__).parent.parent / "pages" / "admin" / "index.html"
        if not html_path.exists():
            return QuartResponse(
                "管理页面文件未找到: " + str(html_path),
                status=404,
                headers={"Content-Type": "text/plain; charset=utf-8"},
            )
        html_content = html_path.read_text(encoding="utf-8")
        return QuartResponse(
            html_content,
            status=200,
            headers={
                "Content-Type": "text/html; charset=utf-8",
                "Cache-Control": "no-store",
            },
        )

    # ==================== 玩家管理 ====================

    async def get_all_players(self, **kwargs) -> Dict[str, Any]:
        """获取所有玩家"""
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
        result = await self.player_service.get_all_players(page, page_size)
        return jsonify({"code": 0, "data": result})

    async def get_player_detail(self, player_id=None, **kwargs) -> Dict[str, Any]:
        """获取玩家详情"""
        if player_id is None:
            return jsonify({"code": -1, "message": "缺少player_id"}), 400

        player = await self.player_service.get_player_by_id(player_id)
        if not player:
            return jsonify({"code": -1, "message": "玩家不存在"}), 404

        inventory = await self.inventory_service.get_player_inventory(player_id)

        skills = await self.cultivation_service.db.fetch_all(
            """SELECT ps.*, s.name, s.description
            FROM player_skills ps
            JOIN skills s ON ps.skill_id = s.id
            WHERE ps.player_id = ?""",
            (player_id,),
        )

        return jsonify({
            "code": 0,
            "data": {
                "player": player.to_dict(),
                "inventory": inventory,
                "skills": skills,
            },
        })

    async def update_player(self, player_id=None, **kwargs) -> Dict[str, Any]:
        """更新玩家"""
        if player_id is None:
            return jsonify({"code": -1, "message": "缺少player_id"}), 400

        data = await request.get_json()
        player = await self.player_service.update_player(player_id, **data)
        if not player:
            return jsonify({"code": -1, "message": "玩家不存在"}), 404
        return jsonify({"code": 0, "data": player.to_dict()})

    async def delete_player(self, player_id=None, **kwargs) -> Dict[str, Any]:
        """删除玩家"""
        if player_id is None:
            return jsonify({"code": -1, "message": "缺少player_id"}), 400

        success = await self.player_service.delete_player(player_id)
        if not success:
            return jsonify({"code": -1, "message": "删除失败"}), 400
        return jsonify({"code": 0, "message": "删除成功"})

    # ==================== 物品管理 ====================

    async def get_all_items(self, **kwargs) -> Dict[str, Any]:
        """获取所有物品"""
        items = await self.inventory_service.get_all_items()
        return jsonify({
            "code": 0,
            "data": [item.to_dict() for item in items],
        })

    async def create_item(self, **kwargs) -> Dict[str, Any]:
        """创建物品"""
        data = await request.get_json()
        try:
            item = await self.inventory_service.create_item(data)
            return jsonify({"code": 0, "data": item.to_dict()})
        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 400

    async def update_item(self, item_id=None, **kwargs) -> Dict[str, Any]:
        """更新物品"""
        if item_id is None:
            return jsonify({"code": -1, "message": "缺少item_id"}), 400

        data = await request.get_json()
        item = await self.inventory_service.update_item(item_id, **data)
        if not item:
            return jsonify({"code": -1, "message": "物品不存在"}), 404
        return jsonify({"code": 0, "data": item.to_dict()})

    async def delete_item(self, item_id=None, **kwargs) -> Dict[str, Any]:
        """删除物品"""
        if item_id is None:
            return jsonify({"code": -1, "message": "缺少item_id"}), 400

        success = await self.inventory_service.delete_item(item_id)
        if not success:
            return jsonify({"code": -1, "message": "删除失败"}), 400
        return jsonify({"code": 0, "message": "删除成功"})

    # ==================== 功法管理 ====================

    async def get_all_skills(self, **kwargs) -> Dict[str, Any]:
        """获取所有功法"""
        skills = await self.cultivation_service.get_all_skills()
        return jsonify({
            "code": 0,
            "data": [skill.to_dict() for skill in skills],
        })

    async def create_skill(self, **kwargs) -> Dict[str, Any]:
        """创建功法"""
        data = await request.get_json()
        try:
            skill = await self.cultivation_service.create_skill(data)
            return jsonify({"code": 0, "data": skill.to_dict()})
        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 400

    async def update_skill(self, skill_id=None, **kwargs) -> Dict[str, Any]:
        """更新功法"""
        if skill_id is None:
            return jsonify({"code": -1, "message": "缺少skill_id"}), 400

        data = await request.get_json()
        skill = await self.cultivation_service.update_skill(skill_id, **data)
        if not skill:
            return jsonify({"code": -1, "message": "功法不存在"}), 404
        return jsonify({"code": 0, "data": skill.to_dict()})

    async def delete_skill(self, skill_id=None, **kwargs) -> Dict[str, Any]:
        """删除功法"""
        if skill_id is None:
            return jsonify({"code": -1, "message": "缺少skill_id"}), 400

        success = await self.cultivation_service.delete_skill(skill_id)
        if not success:
            return jsonify({"code": -1, "message": "删除失败"}), 400
        return jsonify({"code": 0, "message": "删除成功"})

    # ==================== 境界管理 ====================

    async def get_all_realms(self, **kwargs) -> Dict[str, Any]:
        """获取所有境界"""
        realms = await self.cultivation_service.get_all_realms()
        return jsonify({
            "code": 0,
            "data": [realm.to_dict() for realm in realms],
        })

    async def create_realm(self, **kwargs) -> Dict[str, Any]:
        """创建境界"""
        data = await request.get_json()
        try:
            realm = await self.cultivation_service.create_realm(data)
            return jsonify({"code": 0, "data": realm.to_dict()})
        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 400

    async def update_realm(self, realm_id=None, **kwargs) -> Dict[str, Any]:
        """更新境界"""
        if realm_id is None:
            return jsonify({"code": -1, "message": "缺少realm_id"}), 400

        data = await request.get_json()
        realm = await self.cultivation_service.update_realm(realm_id, **data)
        if not realm:
            return jsonify({"code": -1, "message": "境界不存在"}), 404
        return jsonify({"code": 0, "data": realm.to_dict()})

    async def delete_realm(self, realm_id=None, **kwargs) -> Dict[str, Any]:
        """删除境界"""
        if realm_id is None:
            return jsonify({"code": -1, "message": "缺少realm_id"}), 400

        success = await self.cultivation_service.delete_realm(realm_id)
        if not success:
            return jsonify({"code": -1, "message": "删除失败"}), 400
        return jsonify({"code": 0, "message": "删除成功"})

    # ==================== 事件管理 ====================

    async def get_all_events(self, **kwargs) -> Dict[str, Any]:
        """获取所有事件"""
        events = await self.event_service.get_all_events()
        return jsonify({
            "code": 0,
            "data": [event.to_dict() for event in events],
        })

    async def create_event(self, **kwargs) -> Dict[str, Any]:
        """创建事件"""
        data = await request.get_json()
        try:
            event = await self.event_service.create_event(data)
            return jsonify({"code": 0, "data": event.to_dict()})
        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 400

    async def update_event(self, event_id=None, **kwargs) -> Dict[str, Any]:
        """更新事件"""
        if event_id is None:
            return jsonify({"code": -1, "message": "缺少event_id"}), 400

        data = await request.get_json()
        event = await self.event_service.update_event(event_id, **data)
        if not event:
            return jsonify({"code": -1, "message": "事件不存在"}), 404
        return jsonify({"code": 0, "data": event.to_dict()})

    async def delete_event(self, event_id=None, **kwargs) -> Dict[str, Any]:
        """删除事件"""
        if event_id is None:
            return jsonify({"code": -1, "message": "缺少event_id"}), 400

        success = await self.event_service.delete_event(event_id)
        if not success:
            return jsonify({"code": -1, "message": "删除失败"}), 400
        return jsonify({"code": 0, "message": "删除成功"})

    # ==================== 配置管理 ====================

    async def get_config(self, **kwargs) -> Dict[str, Any]:
        """获取配置"""
        config = self.config_manager.get_all()
        return jsonify({"code": 0, "data": config})

    async def update_config(self, **kwargs) -> Dict[str, Any]:
        """更新配置"""
        data = await request.get_json()
        self.config_manager.update(data)
        return jsonify({"code": 0, "message": "配置更新成功"})

    # ==================== 闭关管理 ====================

    async def get_seclusion_status(self, player_id=None, **kwargs) -> Dict[str, Any]:
        """获取玩家闭关状态"""
        if player_id is None:
            return jsonify({"code": -1, "message": "缺少player_id"}), 400

        status = await self.cultivation_service.get_seclusion_status(player_id)
        return jsonify({"code": 0, "data": status})

    async def get_seclusion_records(self, player_id=None, **kwargs) -> Dict[str, Any]:
        """获取玩家闭关记录"""
        if player_id is None:
            return jsonify({"code": -1, "message": "缺少player_id"}), 400

        limit = int(request.args.get("limit", 10))
        records = await self.cultivation_service.get_seclusion_records(player_id, limit)
        return jsonify({"code": 0, "data": records})

    # ==================== 丹毒管理 ====================

    async def get_toxicity_status(self, player_id=None, **kwargs) -> Dict[str, Any]:
        """获取玩家丹毒状态"""
        if player_id is None:
            return jsonify({"code": -1, "message": "缺少player_id"}), 400

        status = await self.inventory_service.get_toxicity_status(player_id)
        return jsonify({"code": 0, "data": status})

    # ==================== 数据统计 ====================

    async def get_game_stats(self, **kwargs) -> Dict[str, Any]:
        """获取游戏统计数据"""
        player_count = await self.player_service.db.fetch_one(
            "SELECT COUNT(*) as count FROM players"
        )

        realm_distribution = await self.player_service.db.fetch_all(
            """SELECT r.name, COUNT(p.id) as count
            FROM players p
            JOIN realms r ON p.realm_id = r.id
            GROUP BY r.name"""
        )

        total_stones = await self.player_service.db.fetch_one(
            "SELECT SUM(spirit_stone) as total FROM players"
        )

        return jsonify({
            "code": 0,
            "data": {
                "player_count": player_count["count"] if player_count else 0,
                "realm_distribution": realm_distribution,
                "total_spirit_stones": total_stones["total"] if total_stones else 0,
            },
        })
