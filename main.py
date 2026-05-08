"""
AstrBot文字修仙游戏插件主入口
负责插件生命周期管理和命令注册，不包含具体业务逻辑
"""
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .config import ConfigManager
from .database import DatabaseManager, MigrationManager
from .services import (
    PlayerService,
    CultivationService,
    CombatService,
    InventoryService,
    EventService,
    CheckinService,
)
from .api import PlayerAPI, ItemAPI, SkillAPI, AdminAPI, CheckinAPI


@register(
    "astrbot_plugin_xiuxian_shell",
    "xiuxian_dev",
    "重生之凡人修仙",
    "0.0.1",
    "https://github.com/1592363624/astrbot_plugin_xiuxian_shell",
)
class XiuxianPlugin(Star):
    """修仙游戏插件主类"""

    def __init__(self, context: Context, config=None):
        super().__init__(context)
        # 初始化配置管理器
        self.config_manager = ConfigManager(context, config)
        # 初始化数据库管理器
        self.db_manager = DatabaseManager(self.config_manager.get_db_path())
        # 初始化迁移管理器
        self.migration_manager = MigrationManager(self.db_manager)
        # 初始化服务层
        self.player_service = PlayerService(self.db_manager, self.config_manager)
        self.cultivation_service = CultivationService(self.db_manager)
        self.combat_service = CombatService(self.db_manager)
        self.inventory_service = InventoryService(self.db_manager)
        self.event_service = EventService(self.db_manager)
        # 初始化签到服务
        self.checkin_service = CheckinService(self.db_manager, self.config_manager)
        # 初始化API层
        self.player_api = PlayerAPI(self.player_service)
        self.item_api = ItemAPI(self.inventory_service, self.player_service)
        self.skill_api = SkillAPI(self.cultivation_service, self.player_service)
        self.checkin_api = CheckinAPI(self.checkin_service, self.player_service)
        self.admin_api = AdminAPI(
            self.player_service,
            self.cultivation_service,
            self.combat_service,
            self.inventory_service,
            self.event_service,
            self.config_manager,
        )


    async def initialize(self):
        """插件初始化"""
        # 更新插件描述信息
        self.description = "重生之凡人修仙，文字修仙游戏插件"
        logger.info("重生之凡人修仙游戏插件初始化中...")
        # 应用数据库迁移
        await self.migration_manager.apply_migrations()
        # 加载已注册玩家到内存缓存
        await self.player_service.load_all_players_to_cache()
        logger.info("重生之凡人修仙游戏插件初始化完成")

    async def terminate(self):
        """插件卸载"""
        logger.info("重生之凡人修仙游戏插件卸载中...")
        # 关闭数据库连接
        await self.db_manager.close()
        logger.info("重生之凡人修仙游戏插件已卸载")

    # ==================== 事件监听区域 ====================

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """监听所有消息，自动为未注册用户创建角色"""
        user_id = event.get_sender_id()
        # 检查用户是否已注册，未注册则自动创建
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error and "自动" in error:
            # 自动注册新用户
            username = event.get_sender_name()
            await self.player_service.auto_register_player(user_id, username)

    # ==================== 命令注册区域 ====================

    @filter.command("修仙状态")
    async def player_status(self, event: AstrMessageEvent):
        """查看修仙状态"""
        user_id = event.get_sender_id()
        result = await self.player_api.get_player_status(user_id)
        yield event.plain_result(result)

    @filter.command("修炼")
    async def cultivate(self, event: AstrMessageEvent):
        """开始修炼"""
        user_id = event.get_sender_id()
        result = await self.skill_api.cultivate(user_id)
        yield event.plain_result(result)

    @filter.command("突破")
    async def breakthrough(self, event: AstrMessageEvent):
        """尝试境界突破"""
        user_id = event.get_sender_id()
        result = await self.skill_api.breakthrough(user_id)
        yield event.plain_result(result)

    @filter.command("探索")
    async def explore(self, event: AstrMessageEvent):
        """探索秘境"""
        user_id = event.get_sender_id()
        result = await self.player_api.explore(user_id)
        yield event.plain_result(result)

    @filter.command("背包")
    async def inventory(self, event: AstrMessageEvent):
        """查看背包"""
        user_id = event.get_sender_id()
        result = await self.item_api.get_inventory(user_id)
        yield event.plain_result(result)

    @filter.command("使用物品")
    async def use_item(self, event: AstrMessageEvent):
        """使用物品"""
        user_id = event.get_sender_id()
        item_name = event.get_message_str().replace("使用物品", "").strip()
        result = await self.item_api.use_item(user_id, item_name)
        yield event.plain_result(result)

    @filter.command("更改道号")
    async def change_username(self, event: AstrMessageEvent):
        """更改道号"""
        user_id = event.get_sender_id()
        new_username = event.get_message_str().replace("更改道号", "").strip()
        result = await self.player_api.change_username(user_id, new_username)
        yield event.plain_result(result)

    @filter.command("修仙签到")
    async def checkin(self, event: AstrMessageEvent):
        """每日签到获取修为奖励"""
        user_id = event.get_sender_id()
        result = await self.checkin_api.checkin(user_id)
        yield event.plain_result(result)

    @filter.command("签到状态")
    async def checkin_status(self, event: AstrMessageEvent):
        """查看签到状态和奖励规则"""
        user_id = event.get_sender_id()
        result = await self.checkin_api.get_checkin_status(user_id)
        yield event.plain_result(result)

    @filter.command("签到排行")
    async def checkin_ranking(self, event: AstrMessageEvent):
        """查看签到排行榜"""
        user_id = event.get_sender_id()
        result = await self.checkin_api.get_checkin_ranking(user_id)
        yield event.plain_result(result)

    @filter.command("修仙帮助")
    async def help_command(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = """
【修仙游戏帮助】
首次发言自动注册修仙角色
修仙状态 - 查看角色状态
修炼 - 进行修炼获取修为
突破 - 尝试境界突破
探索 - 探索秘境获取资源
背包 - 查看背包物品
使用物品 <名称> - 使用指定物品
更改道号 <新道号> - 修改角色道号（2-10个中文字符）
修仙签到 - 每日签到获取修为奖励
签到状态 - 查看签到状态和奖励规则
签到排行 - 查看签到排行榜
修仙帮助 - 显示本帮助
        """
        yield event.plain_result(help_text.strip())

    # ==================== 后台管理API路由 ====================

    async def setup_api_routes(self):
        """设置后台管理API路由"""
        from aiohttp import web

        # 玩家管理API
        self.context.web_app.router.add_get(
            "/api/xiuxian/players", self.admin_api.get_all_players
        )
        self.context.web_app.router.add_get(
            "/api/xiuxian/players/{player_id}", self.admin_api.get_player_detail
        )
        self.context.web_app.router.add_put(
            "/api/xiuxian/players/{player_id}", self.admin_api.update_player
        )
        self.context.web_app.router.add_delete(
            "/api/xiuxian/players/{player_id}", self.admin_api.delete_player
        )

        # 物品管理API
        self.context.web_app.router.add_get(
            "/api/xiuxian/items", self.admin_api.get_all_items
        )
        self.context.web_app.router.add_post(
            "/api/xiuxian/items", self.admin_api.create_item
        )
        self.context.web_app.router.add_put(
            "/api/xiuxian/items/{item_id}", self.admin_api.update_item
        )
        self.context.web_app.router.add_delete(
            "/api/xiuxian/items/{item_id}", self.admin_api.delete_item
        )

        # 功法管理API
        self.context.web_app.router.add_get(
            "/api/xiuxian/skills", self.admin_api.get_all_skills
        )
        self.context.web_app.router.add_post(
            "/api/xiuxian/skills", self.admin_api.create_skill
        )
        self.context.web_app.router.add_put(
            "/api/xiuxian/skills/{skill_id}", self.admin_api.update_skill
        )
        self.context.web_app.router.add_delete(
            "/api/xiuxian/skills/{skill_id}", self.admin_api.delete_skill
        )

        # 境界管理API
        self.context.web_app.router.add_get(
            "/api/xiuxian/realms", self.admin_api.get_all_realms
        )
        self.context.web_app.router.add_post(
            "/api/xiuxian/realms", self.admin_api.create_realm
        )
        self.context.web_app.router.add_put(
            "/api/xiuxian/realms/{realm_id}", self.admin_api.update_realm
        )
        self.context.web_app.router.add_delete(
            "/api/xiuxian/realms/{realm_id}", self.admin_api.delete_realm
        )

        # 事件管理API
        self.context.web_app.router.add_get(
            "/api/xiuxian/events", self.admin_api.get_all_events
        )
        self.context.web_app.router.add_post(
            "/api/xiuxian/events", self.admin_api.create_event
        )
        self.context.web_app.router.add_put(
            "/api/xiuxian/events/{event_id}", self.admin_api.update_event
        )
        self.context.web_app.router.add_delete(
            "/api/xiuxian/events/{event_id}", self.admin_api.delete_event
        )

        # 配置管理API
        self.context.web_app.router.add_get(
            "/api/xiuxian/config", self.admin_api.get_config
        )
        self.context.web_app.router.add_put(
            "/api/xiuxian/config", self.admin_api.update_config
        )

        # 数据统计API
        self.context.web_app.router.add_get(
            "/api/xiuxian/stats", self.admin_api.get_game_stats
        )

        # 签到管理API
        self.context.web_app.router.add_get(
            "/api/xiuxian/checkin/records", self.checkin_api.api_get_all_records
        )
        self.context.web_app.router.add_get(
            "/api/xiuxian/checkin/ranking", self.checkin_api.api_get_ranking
        )
        self.context.web_app.router.add_get(
            "/api/xiuxian/checkin/{player_id}/status", self.checkin_api.api_get_status
        )
        self.context.web_app.router.add_get(
            "/api/xiuxian/checkin/{player_id}/records", self.checkin_api.api_get_records
        )

        logger.info("修仙游戏后台管理API路由已注册")
