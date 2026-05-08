"""
AstrBot文字修仙游戏插件主入口
负责插件生命周期管理和命令注册，不包含具体业务逻辑
"""

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.star.filter.permission import PermissionType

from .config import ConfigManager
from .database import DatabaseManager, MigrationManager
from .services import (
    PlayerService,
    CultivationService,
    CombatService,
    InventoryService,
    EventService,
    CheckinService,
    NotificationService,
)
from .api import PlayerAPI, ItemAPI, SkillAPI, AdminAPI, CheckinAPI, NotificationAPI


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
        # 初始化通知服务
        self.notification_service = NotificationService(
            self.db_manager, self.player_service, self.context, self.config_manager
        )
        # 初始化API层
        self.player_api = PlayerAPI(self.player_service)
        self.item_api = ItemAPI(self.inventory_service, self.player_service)
        self.skill_api = SkillAPI(self.cultivation_service, self.player_service)
        self.checkin_api = CheckinAPI(self.checkin_service, self.player_service)
        self.notification_api = NotificationAPI(self.notification_service)
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
        # 注册后台管理API路由
        await self.setup_api_routes()
        # 启动定时通知检查任务
        self._start_scheduled_notification_checker()
        logger.info("重生之凡人修仙游戏插件初始化完成")

    async def terminate(self):
        """插件卸载"""
        logger.info("重生之凡人修仙游戏插件卸载中...")
        # 停止定时通知检查任务
        self._stop_scheduled_notification_checker()
        # 关闭数据库连接
        await self.db_manager.close()
        logger.info("重生之凡人修仙游戏插件已卸载")

    # ==================== 定时通知检查 ====================

    _scheduled_check_task = None

    def _start_scheduled_notification_checker(self):
        """启动定时通知检查后台任务"""
        import asyncio

        async def _check_loop():
            while True:
                try:
                    await asyncio.sleep(60)
                    due_list = await self.notification_service.get_due_scheduled_notifications()
                    for record in due_list:
                        try:
                            result = await self.notification_service.execute_scheduled_notification(
                                record["id"]
                            )
                            logger.info(
                                f"定时通知 {record['id']}({record['title']}) 执行结果: "
                                f"成功{result.get('sent_count', 0)}人, 失败{result.get('fail_count', 0)}人"
                            )
                        except Exception as e:
                            logger.error(f"定时通知 {record['id']} 执行失败: {e}")
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"定时通知检查循环异常: {e}")

        self._scheduled_check_task = asyncio.ensure_future(_check_loop())
        logger.info("定时通知检查任务已启动（每60秒检查一次）")

    def _stop_scheduled_notification_checker(self):
        """停止定时通知检查后台任务"""
        if self._scheduled_check_task and not self._scheduled_check_task.done():
            self._scheduled_check_task.cancel()
            logger.info("定时通知检查任务已停止")

    # ==================== 事件监听区域 ====================

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """监听所有消息，自动为未注册用户创建角色，并记录玩家会话信息"""
        user_id = event.get_sender_id()
        # 记录玩家会话信息，用于后续主动推送通知
        await self.notification_service.record_player_session(
            user_id=user_id,
            unified_msg_origin=event.unified_msg_origin,
            platform_name=event.get_platform_name(),
        )
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
发送公告 <标题> | <内容> - 发送公告给所有玩家(管理员)
发送通知 <标题> | <内容> | <用户ID> - 发送通知给指定玩家(管理员)
通知历史 - 查看通知历史记录(管理员)
定时通知 列表/创建/开启/关闭/删除 - 管理定时通知(管理员)
修仙帮助 - 显示本帮助
        """
        yield event.plain_result(help_text.strip())

    # ==================== 通知命令区域（管理员） ====================

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("发送公告")
    async def send_announcement(self, event: AstrMessageEvent):
        """发送公告给所有玩家（管理员），示例：发送公告 系统维护 | 今晚8点维护"""
        user_id = event.get_sender_id()
        message = event.get_message_str().replace("发送公告", "").strip()

        if not message:
            yield event.plain_result("用法：发送公告 <标题> | <内容>")
            return

        parts = message.split("|", 1)
        if len(parts) < 2:
            yield event.plain_result("格式错误，请使用：发送公告 <标题> | <内容>")
            return

        title = parts[0].strip()
        content = parts[1].strip()

        result = await self.notification_api.send_notification(
            title=title, content=content, target_type="all", sender_id=user_id
        )

        if not result.get("success", False):
            yield event.plain_result(f"发送失败：{result.get('error', '未知错误')}")
        else:
            yield event.plain_result(
                f"公告发送成功！已发送给{result.get('sent_count', 0)}名玩家"
            )

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("发送通知")
    async def send_notification_cmd(self, event: AstrMessageEvent):
        """发送通知给指定玩家（管理员），示例：发送通知 活动提醒 | 限时双倍修为 | user123"""
        user_id = event.get_sender_id()
        message = event.get_message_str().replace("发送通知", "").strip()

        if not message:
            yield event.plain_result("用法：发送通知 <标题> | <内容> | <目标用户ID>")
            return

        parts = message.split("|", 2)
        if len(parts) < 3:
            yield event.plain_result(
                "格式错误，请使用：发送通知 <标题> | <内容> | <目标用户ID>"
            )
            return

        title = parts[0].strip()
        content = parts[1].strip()
        target_id = parts[2].strip()

        result = await self.notification_api.send_notification(
            title=title,
            content=content,
            target_type="specific",
            target_ids=[target_id],
            sender_id=user_id,
        )

        if not result.get("success", False):
            yield event.plain_result(f"发送失败：{result.get('error', '未知错误')}")
        else:
            yield event.plain_result(f"通知发送成功！已发送给玩家{target_id}")

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("通知历史")
    async def notification_history(self, event: AstrMessageEvent):
        """查看通知历史（管理员）"""
        result = await self.notification_api.get_notification_history(
            page=1, page_size=10
        )

        history = result.get("items", [])
        if not history:
            yield event.plain_result("暂无通知历史")
            return

        history_text = "【通知历史】\n"
        for i, notice in enumerate(history, 1):
            status_map = {
                "pending": "待发送",
                "sending": "发送中",
                "completed": "已完成",
                "partial": "部分失败",
                "failed": "发送失败",
            }
            status_text = status_map.get(notice["status"], notice["status"])
            history_text += f"{i}. {notice['title']} ({notice['created_at']})\n"
            history_text += (
                f"   状态：{status_text}，成功：{notice['sent_count']}人，失败：{notice['fail_count']}人\n"
            )

        yield event.plain_result(history_text.strip())

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("定时通知")
    async def scheduled_notification(self, event: AstrMessageEvent):
        """管理定时通知（管理员），示例：定时通知 列表 / 定时通知 创建 标题|内容|cron / 定时通知 开启 1 / 定时通知 关闭 1 / 定时通知 删除 1"""
        message = event.get_message_str().replace("定时通知", "").strip()

        if not message or message == "列表":
            result = await self.notification_api.get_scheduled_notifications(page=1, page_size=10)
            items = result.get("data", {}).get("items", [])
            if not items:
                yield event.plain_result("暂无定时通知")
                return

            text = "【定时通知列表】\n"
            for item in items:
                status = "✅启用" if item["enabled"] else "❌禁用"
                text += (
                    f"{item['id']}. {item['title']} [{status}]\n"
                    f"   Cron: {item['cron_expression']}，已执行{item['run_count']}次\n"
                )
            yield event.plain_result(text.strip())
            return

        parts = message.split(None, 1)
        action = parts[0]

        if action == "创建":
            if len(parts) < 2:
                yield event.plain_result("格式：定时通知 创建 <标题>|<内容>|<Cron表达式>\n示例：定时通知 创建 每日提醒|记得修炼|0 8 * * *")
                return

            create_parts = parts[1].split("|", 2)
            if len(create_parts) < 3:
                yield event.plain_result("格式：定时通知 创建 <标题>|<内容>|<Cron表达式>")
                return

            title = create_parts[0].strip()
            content = create_parts[1].strip()
            cron_expr = create_parts[2].strip()

            result = await self.notification_api.create_scheduled_notification(
                title=title, content=content, cron_expression=cron_expr,
                created_by=event.get_sender_id(),
            )

            if not result.get("success", False):
                yield event.plain_result(f"创建失败：{result.get('error', '未知错误')}")
            else:
                yield event.plain_result(f"定时通知创建成功！ID: {result['data']['id']}")

        elif action in ("开启", "启用"):
            if len(parts) < 2:
                yield event.plain_result("格式：定时通知 开启 <ID>")
                return
            try:
                schedule_id = int(parts[1].strip())
            except ValueError:
                yield event.plain_result("ID必须为数字")
                return

            result = await self.notification_api.toggle_scheduled_notification(schedule_id, True)
            if not result.get("success", False):
                yield event.plain_result(f"操作失败：{result.get('error', '未知错误')}")
            else:
                yield event.plain_result(f"定时通知 {schedule_id} 已启用")

        elif action in ("关闭", "禁用"):
            if len(parts) < 2:
                yield event.plain_result("格式：定时通知 关闭 <ID>")
                return
            try:
                schedule_id = int(parts[1].strip())
            except ValueError:
                yield event.plain_result("ID必须为数字")
                return

            result = await self.notification_api.toggle_scheduled_notification(schedule_id, False)
            if not result.get("success", False):
                yield event.plain_result(f"操作失败：{result.get('error', '未知错误')}")
            else:
                yield event.plain_result(f"定时通知 {schedule_id} 已禁用")

        elif action == "删除":
            if len(parts) < 2:
                yield event.plain_result("格式：定时通知 删除 <ID>")
                return
            try:
                schedule_id = int(parts[1].strip())
            except ValueError:
                yield event.plain_result("ID必须为数字")
                return

            result = await self.notification_api.delete_scheduled_notification(schedule_id)
            if not result.get("success", False):
                yield event.plain_result(f"删除失败：{result.get('error', '未知错误')}")
            else:
                yield event.plain_result(f"定时通知 {schedule_id} 已删除")

        else:
            yield event.plain_result(
                "可用操作：列表、创建、开启、关闭、删除\n"
                "示例：\n"
                "定时通知 列表\n"
                "定时通知 创建 每日提醒|记得修炼|0 8 * * *\n"
                "定时通知 开启 1\n"
                "定时通知 关闭 1\n"
                "定时通知 删除 1"
            )

    # ==================== 后台管理API路由 ====================

    async def setup_api_routes(self):
        """设置后台管理API路由"""
        # 玩家管理API
        self.context.register_web_api(
            "/api/xiuxian/players",
            self.admin_api.get_all_players,
            ["GET"],
            "获取所有玩家列表",
        )
        self.context.register_web_api(
            "/api/xiuxian/players/{player_id}",
            self.admin_api.get_player_detail,
            ["GET"],
            "获取玩家详情",
        )
        self.context.register_web_api(
            "/api/xiuxian/players/{player_id}",
            self.admin_api.update_player,
            ["PUT"],
            "更新玩家信息",
        )
        self.context.register_web_api(
            "/api/xiuxian/players/{player_id}",
            self.admin_api.delete_player,
            ["DELETE"],
            "删除玩家",
        )

        # 物品管理API
        self.context.register_web_api(
            "/api/xiuxian/items",
            self.admin_api.get_all_items,
            ["GET"],
            "获取所有物品列表",
        )
        self.context.register_web_api(
            "/api/xiuxian/items",
            self.admin_api.create_item,
            ["POST"],
            "创建物品",
        )
        self.context.register_web_api(
            "/api/xiuxian/items/{item_id}",
            self.admin_api.update_item,
            ["PUT"],
            "更新物品",
        )
        self.context.register_web_api(
            "/api/xiuxian/items/{item_id}",
            self.admin_api.delete_item,
            ["DELETE"],
            "删除物品",
        )

        # 功法管理API
        self.context.register_web_api(
            "/api/xiuxian/skills",
            self.admin_api.get_all_skills,
            ["GET"],
            "获取所有功法列表",
        )
        self.context.register_web_api(
            "/api/xiuxian/skills",
            self.admin_api.create_skill,
            ["POST"],
            "创建功法",
        )
        self.context.register_web_api(
            "/api/xiuxian/skills/{skill_id}",
            self.admin_api.update_skill,
            ["PUT"],
            "更新功法",
        )
        self.context.register_web_api(
            "/api/xiuxian/skills/{skill_id}",
            self.admin_api.delete_skill,
            ["DELETE"],
            "删除功法",
        )

        # 境界管理API
        self.context.register_web_api(
            "/api/xiuxian/realms",
            self.admin_api.get_all_realms,
            ["GET"],
            "获取所有境界列表",
        )
        self.context.register_web_api(
            "/api/xiuxian/realms",
            self.admin_api.create_realm,
            ["POST"],
            "创建境界",
        )
        self.context.register_web_api(
            "/api/xiuxian/realms/{realm_id}",
            self.admin_api.update_realm,
            ["PUT"],
            "更新境界",
        )
        self.context.register_web_api(
            "/api/xiuxian/realms/{realm_id}",
            self.admin_api.delete_realm,
            ["DELETE"],
            "删除境界",
        )

        # 事件管理API
        self.context.register_web_api(
            "/api/xiuxian/events",
            self.admin_api.get_all_events,
            ["GET"],
            "获取所有事件列表",
        )
        self.context.register_web_api(
            "/api/xiuxian/events",
            self.admin_api.create_event,
            ["POST"],
            "创建事件",
        )
        self.context.register_web_api(
            "/api/xiuxian/events/{event_id}",
            self.admin_api.update_event,
            ["PUT"],
            "更新事件",
        )
        self.context.register_web_api(
            "/api/xiuxian/events/{event_id}",
            self.admin_api.delete_event,
            ["DELETE"],
            "删除事件",
        )

        # 配置管理API
        self.context.register_web_api(
            "/api/xiuxian/config",
            self.admin_api.get_config,
            ["GET"],
            "获取插件配置",
        )
        self.context.register_web_api(
            "/api/xiuxian/config",
            self.admin_api.update_config,
            ["PUT"],
            "更新插件配置",
        )

        # 数据统计API
        self.context.register_web_api(
            "/api/xiuxian/stats",
            self.admin_api.get_game_stats,
            ["GET"],
            "获取游戏统计数据",
        )

        # 签到管理API
        self.context.register_web_api(
            "/api/xiuxian/checkin/records",
            self.checkin_api.api_get_all_records,
            ["GET"],
            "获取所有签到记录",
        )
        self.context.register_web_api(
            "/api/xiuxian/checkin/ranking",
            self.checkin_api.api_get_ranking,
            ["GET"],
            "获取签到排行",
        )
        self.context.register_web_api(
            "/api/xiuxian/checkin/{player_id}/status",
            self.checkin_api.api_get_status,
            ["GET"],
            "获取玩家签到状态",
        )
        self.context.register_web_api(
            "/api/xiuxian/checkin/{player_id}/records",
            self.checkin_api.api_get_records,
            ["GET"],
            "获取玩家签到记录",
        )

        # 通知推送API
        self.context.register_web_api(
            "/api/xiuxian/notifications/send",
            self.notification_api.handle_send_notification,
            ["POST"],
            "发送通知",
        )
        self.context.register_web_api(
            "/api/xiuxian/notifications/history",
            self.notification_api.handle_get_history,
            ["GET"],
            "获取通知历史",
        )
        self.context.register_web_api(
            "/api/xiuxian/notifications/{notification_id}",
            self.notification_api.handle_get_detail,
            ["GET"],
            "获取通知详情",
        )
        self.context.register_web_api(
            "/api/xiuxian/notifications/{notification_id}",
            self.notification_api.handle_delete_notification,
            ["DELETE"],
            "删除通知",
        )
        self.context.register_web_api(
            "/api/xiuxian/notifications/sessions",
            self.notification_api.handle_get_sessions,
            ["GET"],
            "获取所有玩家会话信息",
        )
        self.context.register_web_api(
            "/api/xiuxian/notifications/send-template",
            self.notification_api.handle_send_by_template,
            ["POST"],
            "使用模板发送通知",
        )
        self.context.register_web_api(
            "/api/xiuxian/notifications/templates",
            self.notification_api.handle_get_templates,
            ["GET"],
            "获取所有通知模板",
        )
        self.context.register_web_api(
            "/api/xiuxian/notifications/scheduled",
            self.notification_api.handle_create_scheduled,
            ["POST"],
            "创建定时通知",
        )
        self.context.register_web_api(
            "/api/xiuxian/notifications/scheduled",
            self.notification_api.handle_get_scheduled,
            ["GET"],
            "获取定时通知列表",
        )
        self.context.register_web_api(
            "/api/xiuxian/notifications/scheduled/{schedule_id}/toggle",
            self.notification_api.handle_toggle_scheduled,
            ["PUT"],
            "启用/禁用定时通知",
        )
        self.context.register_web_api(
            "/api/xiuxian/notifications/scheduled/{schedule_id}",
            self.notification_api.handle_delete_scheduled,
            ["DELETE"],
            "删除定时通知",
        )

        logger.info("修仙游戏后台管理API路由已注册")
