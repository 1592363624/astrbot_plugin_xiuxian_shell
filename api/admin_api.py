"""
后台管理API
提供后台管理系统的HTTP接口
"""

from typing import TYPE_CHECKING, Any

from quart import jsonify, request

from ..services import (
    BreakthroughService,
    CombatService,
    CultivationService,
    EventService,
    InventoryService,
    PlayerService,
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
        breakthrough_service: BreakthroughService = None,
    ):
        """
        初始化后台管理API

        Args:
            player_service: 玩家服务
            cultivation_service: 修炼服务
            combat_service: 战斗服务
            inventory_service: 储物袋服务
            event_service: 事件服务
            config_manager: 配置管理器
            breakthrough_service: 突破服务
        """
        self.player_service = player_service
        self.cultivation_service = cultivation_service
        self.combat_service = combat_service
        self.inventory_service = inventory_service
        self.event_service = event_service
        self.config_manager = config_manager
        self.breakthrough_service = breakthrough_service

    # ==================== 玩家管理 ====================

    async def get_all_players(self, **kwargs) -> dict[str, Any]:
        """获取所有玩家"""
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 20))
        result = await self.player_service.get_all_players(page, page_size)
        return jsonify({"code": 0, "data": result})

    async def get_player_detail(self, player_id=None, **kwargs) -> dict[str, Any]:
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

        return jsonify(
            {
                "code": 0,
                "data": {
                    "player": player.to_dict(),
                    "inventory": inventory,
                    "skills": skills,
                },
            }
        )

    async def update_player(self, player_id=None, **kwargs) -> dict[str, Any]:
        """更新玩家"""
        if player_id is None:
            return jsonify({"code": -1, "message": "缺少player_id"}), 400

        data = await request.get_json()
        player = await self.player_service.update_player(player_id, **data)
        if not player:
            return jsonify({"code": -1, "message": "玩家不存在"}), 404
        return jsonify({"code": 0, "data": player.to_dict()})

    async def delete_player(self, player_id=None, **kwargs) -> dict[str, Any]:
        """
        彻底删除玩家及其所有关联数据

        会级联删除：背包、功法、事件记录、签到记录、闭关记录、丹毒记录、会话信息
        """
        if player_id is None:
            return jsonify({"code": -1, "message": "缺少player_id"}), 400

        # 获取玩家信息以取得 user_id
        player = await self.player_service.get_player_by_id(player_id)
        user_id = player.user_id if player else None

        success = await self.player_service.delete_player(player_id, user_id)
        if not success:
            return jsonify({"code": -1, "message": "删除失败"}), 400
        return jsonify({"code": 0, "message": "删除成功"})

    async def reset_player(self, player_id=None, **kwargs) -> dict[str, Any]:
        """
        重置玩家数据

        保留玩家账号，但清空所有游戏进度：
        - 清空储物袋、功法、事件记录、签到记录、闭关记录、丹毒记录
        - 重置境界为凡人、修为清零、灵石回到初始值、后天属性清零
        """
        if player_id is None:
            return jsonify({"code": -1, "message": "缺少player_id"}), 400

        player = await self.player_service.get_player_by_id(player_id)
        if not player:
            return jsonify({"code": -1, "message": "玩家不存在"}), 404

        user_id = player.user_id
        reset_player = await self.player_service.reset_player(player_id, user_id)
        if not reset_player:
            return jsonify({"code": -1, "message": "重置失败"}), 400

        return jsonify(
            {"code": 0, "message": "重置成功", "data": reset_player.to_dict()}
        )

    async def ban_player(self, player_id=None, **kwargs) -> dict[str, Any]:
        """
        封禁玩家（软删除）

        不真正删除数据，而是将 is_deleted 标记为 1，并记录封禁理由。
        被软删除的玩家无法正常使用游戏功能。
        """
        if player_id is None:
            return jsonify({"code": -1, "message": "缺少player_id"}), 400

        player = await self.player_service.get_player_by_id(player_id)
        if not player:
            return jsonify({"code": -1, "message": "玩家不存在"}), 404

        # 从请求体中获取封禁理由
        data = await request.get_json() or {}
        ban_reason = data.get("ban_reason", "违反游戏规则")

        user_id = player.user_id
        success = await self.player_service.soft_delete_player(
            player_id, user_id, ban_reason
        )
        if not success:
            return jsonify({"code": -1, "message": "封禁失败"}), 400

        return jsonify(
            {
                "code": 0,
                "message": "封禁成功",
                "data": {"ban_reason": ban_reason},
            }
        )

    async def unban_player(self, player_id=None, **kwargs) -> dict[str, Any]:
        """
        解封玩家（恢复软删除）

        将 is_deleted 标记重置为 0，恢复玩家正常使用权限
        """
        if player_id is None:
            return jsonify({"code": -1, "message": "缺少player_id"}), 400

        success = await self.player_service.restore_player(player_id)
        if not success:
            return jsonify({"code": -1, "message": "解封失败"}), 400

        return jsonify({"code": 0, "message": "解封成功"})

    # ==================== 物品管理 ====================

    async def get_all_items(self, **kwargs) -> dict[str, Any]:
        """获取所有物品"""
        items = await self.inventory_service.get_all_items()
        return jsonify(
            {
                "code": 0,
                "data": [item.to_dict() for item in items],
            }
        )

    async def create_item(self, **kwargs) -> dict[str, Any]:
        """创建物品"""
        data = await request.get_json()
        try:
            item = await self.inventory_service.create_item(data)
            return jsonify({"code": 0, "data": item.to_dict()})
        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 400

    async def update_item(self, item_id=None, **kwargs) -> dict[str, Any]:
        """更新物品"""
        if item_id is None:
            return jsonify({"code": -1, "message": "缺少item_id"}), 400

        data = await request.get_json()
        item = await self.inventory_service.update_item(item_id, **data)
        if not item:
            return jsonify({"code": -1, "message": "物品不存在"}), 404
        return jsonify({"code": 0, "data": item.to_dict()})

    async def delete_item(self, item_id=None, **kwargs) -> dict[str, Any]:
        """删除物品"""
        if item_id is None:
            return jsonify({"code": -1, "message": "缺少item_id"}), 400

        success = await self.inventory_service.delete_item(item_id)
        if not success:
            return jsonify({"code": -1, "message": "删除失败"}), 400
        return jsonify({"code": 0, "message": "删除成功"})

    # ==================== 功法管理 ====================

    async def get_all_skills(self, **kwargs) -> dict[str, Any]:
        """获取所有功法"""
        skills = await self.cultivation_service.get_all_skills()
        return jsonify(
            {
                "code": 0,
                "data": [skill.to_dict() for skill in skills],
            }
        )

    async def create_skill(self, **kwargs) -> dict[str, Any]:
        """创建功法"""
        data = await request.get_json()
        try:
            skill = await self.cultivation_service.create_skill(data)
            return jsonify({"code": 0, "data": skill.to_dict()})
        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 400

    async def update_skill(self, skill_id=None, **kwargs) -> dict[str, Any]:
        """更新功法"""
        if skill_id is None:
            return jsonify({"code": -1, "message": "缺少skill_id"}), 400

        data = await request.get_json()
        skill = await self.cultivation_service.update_skill(skill_id, **data)
        if not skill:
            return jsonify({"code": -1, "message": "功法不存在"}), 404
        return jsonify({"code": 0, "data": skill.to_dict()})

    async def delete_skill(self, skill_id=None, **kwargs) -> dict[str, Any]:
        """删除功法"""
        if skill_id is None:
            return jsonify({"code": -1, "message": "缺少skill_id"}), 400

        success = await self.cultivation_service.delete_skill(skill_id)
        if not success:
            return jsonify({"code": -1, "message": "删除失败"}), 400
        return jsonify({"code": 0, "message": "删除成功"})

    # ==================== 境界管理 ====================

    async def get_all_realms(self, **kwargs) -> dict[str, Any]:
        """获取所有境界"""
        realms = await self.cultivation_service.get_all_realms()
        return jsonify(
            {
                "code": 0,
                "data": [realm.to_dict() for realm in realms],
            }
        )

    async def create_realm(self, **kwargs) -> dict[str, Any]:
        """创建境界"""
        data = await request.get_json()
        try:
            realm = await self.cultivation_service.create_realm(data)
            return jsonify({"code": 0, "data": realm.to_dict()})
        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 400

    async def update_realm(self, realm_id=None, **kwargs) -> dict[str, Any]:
        """更新境界"""
        if realm_id is None:
            return jsonify({"code": -1, "message": "缺少realm_id"}), 400

        data = await request.get_json()
        realm = await self.cultivation_service.update_realm(realm_id, **data)
        if not realm:
            return jsonify({"code": -1, "message": "境界不存在"}), 404
        return jsonify({"code": 0, "data": realm.to_dict()})

    async def delete_realm(self, realm_id=None, **kwargs) -> dict[str, Any]:
        """删除境界"""
        if realm_id is None:
            return jsonify({"code": -1, "message": "缺少realm_id"}), 400

        success = await self.cultivation_service.delete_realm(realm_id)
        if not success:
            return jsonify({"code": -1, "message": "删除失败"}), 400
        return jsonify({"code": 0, "message": "删除成功"})

    # ==================== 事件管理 ====================

    async def get_all_events(self, **kwargs) -> dict[str, Any]:
        """获取所有事件"""
        events = await self.event_service.get_all_events()
        return jsonify(
            {
                "code": 0,
                "data": [event.to_dict() for event in events],
            }
        )

    async def create_event(self, **kwargs) -> dict[str, Any]:
        """创建事件"""
        data = await request.get_json()
        try:
            event = await self.event_service.create_event(data)
            return jsonify({"code": 0, "data": event.to_dict()})
        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 400

    async def update_event(self, event_id=None, **kwargs) -> dict[str, Any]:
        """更新事件"""
        if event_id is None:
            return jsonify({"code": -1, "message": "缺少event_id"}), 400

        data = await request.get_json()
        event = await self.event_service.update_event(event_id, **data)
        if not event:
            return jsonify({"code": -1, "message": "事件不存在"}), 404
        return jsonify({"code": 0, "data": event.to_dict()})

    async def delete_event(self, event_id=None, **kwargs) -> dict[str, Any]:
        """删除事件"""
        if event_id is None:
            return jsonify({"code": -1, "message": "缺少event_id"}), 400

        success = await self.event_service.delete_event(event_id)
        if not success:
            return jsonify({"code": -1, "message": "删除失败"}), 400
        return jsonify({"code": 0, "message": "删除成功"})

    # ==================== 配置管理 ====================

    async def get_config(self, **kwargs) -> dict[str, Any]:
        """获取配置"""
        config = self.config_manager.get_all()
        return jsonify({"code": 0, "data": config})

    async def update_config(self, **kwargs) -> dict[str, Any]:
        """更新配置"""
        data = await request.get_json()
        self.config_manager.update(data)
        return jsonify({"code": 0, "message": "配置更新成功"})

    # ==================== 闭关管理 ====================

    async def get_seclusion_status(self, player_id=None, **kwargs) -> dict[str, Any]:
        """获取玩家闭关状态"""
        if player_id is None:
            return jsonify({"code": -1, "message": "缺少player_id"}), 400

        status = await self.cultivation_service.get_seclusion_status(player_id)
        return jsonify({"code": 0, "data": status})

    async def get_seclusion_records(self, player_id=None, **kwargs) -> dict[str, Any]:
        """获取玩家闭关记录"""
        if player_id is None:
            return jsonify({"code": -1, "message": "缺少player_id"}), 400

        limit = int(request.args.get("limit", 10))
        records = await self.cultivation_service.get_seclusion_records(player_id, limit)
        return jsonify({"code": 0, "data": records})

    # ==================== 丹毒管理 ====================

    async def get_toxicity_status(self, player_id=None, **kwargs) -> dict[str, Any]:
        """获取玩家丹毒状态"""
        if player_id is None:
            return jsonify({"code": -1, "message": "缺少player_id"}), 400

        status = await self.inventory_service.get_toxicity_status(player_id)
        return jsonify({"code": 0, "data": status})

    # ==================== 数据统计 ====================

    async def get_game_stats(self, **kwargs) -> dict[str, Any]:
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

        return jsonify(
            {
                "code": 0,
                "data": {
                    "player_count": player_count["count"] if player_count else 0,
                    "realm_distribution": realm_distribution,
                    "total_spirit_stones": total_stones["total"] if total_stones else 0,
                },
            }
        )

    # ==================== 突破条件管理 ====================

    async def get_breakthrough_conditions(self, **kwargs) -> dict[str, Any]:
        """获取所有突破条件"""
        if not self.breakthrough_service:
            return jsonify({"code": 1, "message": "突破服务未初始化"})
        result = await self.breakthrough_service.get_all_breakthrough_conditions()
        return jsonify({"code": 0, "data": result})

    async def get_breakthrough_condition(
        self, condition_id: str, **kwargs
    ) -> dict[str, Any]:
        """获取单个突破条件"""
        if not self.breakthrough_service:
            return jsonify({"code": 1, "message": "突破服务未初始化"})
        result = await self.breakthrough_service.get_breakthrough_condition_by_id(
            condition_id
        )
        return jsonify({"code": 0, "data": result})

    async def update_breakthrough_condition(
        self, condition_id: str, **kwargs
    ) -> dict[str, Any]:
        """更新突破条件"""
        if not self.breakthrough_service:
            return jsonify({"code": 1, "message": "突破服务未初始化"})
        try:
            data = await request.json()
        except Exception:
            return jsonify({"code": 1, "message": "请求格式错误"})
        result = await self.breakthrough_service.update_breakthrough_condition(
            condition_id, **data
        )
        return jsonify({"code": 0, "data": result})

    # ==================== 发言日志管理 ====================

    async def get_chat_logs(self, **kwargs) -> dict[str, Any]:
        """获取发言日志列表"""
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 100))
        sort_field = request.args.get("sort_field", "created_at")
        sort_order = request.args.get("sort_order", "DESC")
        keyword = request.args.get("keyword", None)

        result = await self.player_service.get_chat_logs(
            page=page,
            page_size=page_size,
            sort_field=sort_field,
            sort_order=sort_order,
            keyword=keyword,
        )
        return jsonify({"code": 0, "data": result})
