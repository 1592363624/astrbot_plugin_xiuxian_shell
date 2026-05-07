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
)
from .api import PlayerAPI, ItemAPI, SkillAPI, AdminAPI


@register(
    "astrbot_plugin_xiuxian_shell",
    "xiuxian_dev",
    "AstrBot文字修仙游戏插件",
    "1.0.0",
    "https://github.com/xiuxian-dev/astrbot_plugin_xiuxian_shell",
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
        self.player_service = PlayerService(self.db_manager)
        self.cultivation_service = CultivationService(self.db_manager)
        self.combat_service = CombatService(self.db_manager)
        self.inventory_service = InventoryService(self.db_manager)
        self.event_service = EventService(self.db_manager)
        # 初始化API层
        self.player_api = PlayerAPI(self.player_service)
        self.item_api = ItemAPI(self.inventory_service)
        self.skill_api = SkillAPI(self.cultivation_service)
        self.admin_api = AdminAPI(
            self.player_service,
            self.cultivation_service,
            self.combat_service,
            self.inventory_service,
            self.event_service,
        )

    async def initialize(self):
        """插件初始化"""
        logger.info("修仙游戏插件初始化中...")
        # 应用数据库迁移
        await self.migration_manager.apply_migrations()
        logger.info("修仙游戏插件初始化完成")

    async def terminate(self):
        """插件卸载"""
        logger.info("修仙游戏插件卸载中...")
        # 关闭数据库连接
        await self.db_manager.close()
        logger.info("修仙游戏插件已卸载")

    # ==================== 命令注册区域 ====================

    @filter.command("修仙注册")
    async def register_player(self, event: AstrMessageEvent):
        """注册修仙角色"""
        user_id = event.get_sender_id()
        username = event.get_sender_name()
        result = await self.player_api.create_player(user_id, username)
        yield event.plain_result(result)

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

    @filter.command("修仙帮助")
    async def help_command(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = """
【修仙游戏帮助】
修仙注册 - 注册修仙角色
修仙状态 - 查看角色状态
修炼 - 进行修炼获取修为
突破 - 尝试境界突破
探索 - 探索秘境获取资源
背包 - 查看背包物品
使用物品 <名称> - 使用指定物品
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

        logger.info("修仙游戏后台管理API路由已注册")
