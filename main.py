"""
AstrBot文字修仙游戏插件主入口
负责插件生命周期管理和命令注册，不包含具体业务逻辑
"""

from pathlib import Path

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star
from astrbot.core.message.components import Plain
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.star import StarTools
from astrbot.core.star.filter.permission import PermissionType

from .admin_server import AdminServer
from .api import (
    AdminAPI,
    CheckinAPI,
    CultivationAPI,
    DeepSeclusionAPI,
    ItemAPI,
    MarketAPI,
    NotificationAPI,
    PlayerAPI,
)
from .config import ConfigManager
from .data.json_data_manager import JsonDataManager
from .database import DatabaseManager, MigrationManager
from .services import (
    BreakthroughService,
    CheckinService,
    CombatService,
    CultivationService,
    DeepSeclusionService,
    EventService,
    InventoryService,
    ItemEffectService,
    MarketService,
    NotificationService,
    PlayerService,
    PlayerStateChecker,
)


class XiuxianPlugin(Star):
    """修仙游戏插件主类"""

    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.plugin_name = "astrbot_plugin_xiuxian_shell"
        self.config_manager = ConfigManager(context, config)
        self.db_manager = DatabaseManager(self.config_manager.get_db_path())
        self.migration_manager = MigrationManager(self.db_manager)
        json_data_dir = Path(__file__).parent / "data" / "game_data"
        self.json_data_manager = JsonDataManager(json_data_dir)
        self.cultivation_service = CultivationService(
            self.db_manager, self.config_manager, self.json_data_manager
        )
        self.player_service = PlayerService(self.db_manager, self.config_manager, self.cultivation_service)
        self.combat_service = CombatService(
            self.db_manager, self.cultivation_service
        )
        self.inventory_service = InventoryService(
            self.db_manager, self.config_manager, self.json_data_manager, self.cultivation_service
        )
        self.event_service = EventService(self.db_manager, self.json_data_manager, self.cultivation_service)
        self.cultivation_service.event_service = self.event_service
        # 初始化签到服务
        self.checkin_service = CheckinService(self.db_manager, self.config_manager, self.cultivation_service)
        # 初始化通知服务
        self.notification_service = NotificationService(
            self.db_manager, self.player_service, self.context, self.config_manager
        )
        # 初始化深度闭关服务
        self.deep_seclusion_service = DeepSeclusionService(
            self.db_manager, self.config_manager, self.cultivation_service
        )
        # 初始化突破服务
        self.breakthrough_service = BreakthroughService(
            self.db_manager, self.config_manager, self.cultivation_service
        )
        # 回注突破服务引用到修炼服务，用于突破提示差异化
        self.cultivation_service._breakthrough_service_ref = self.breakthrough_service
        # 回注背包服务引用到修炼服务，用于闭关奇遇物品发放（避免内联创建InventoryService）
        self.cultivation_service._inventory_service_ref = self.inventory_service
        # 初始化万宝楼服务
        self.market_service = MarketService(
            self.db_manager, self.config_manager, self.inventory_service
        )
        # 初始化物品效果服务（新效果系统）
        self.item_effect_service = ItemEffectService(
            self.db_manager,
            self.config_manager,
            self.json_data_manager,
            self.cultivation_service,
            self.inventory_service,
        )
        # 初始化玩家状态检查器（统一状态检查入口）
        self.state_checker = PlayerStateChecker(
            self.db_manager,
            cultivation_service=self.cultivation_service,
            breakthrough_service=self.breakthrough_service,
            inventory_service=self.inventory_service,
            item_effect_service=self.item_effect_service,
        )
        # 初始化API层
        self.player_api = PlayerAPI(
            self.player_service, self.deep_seclusion_service, self.cultivation_service
        )
        self.item_api = ItemAPI(self.inventory_service, self.player_service, self.item_effect_service)
        self.cultivation_api = CultivationAPI(
            self.cultivation_service, self.player_service, self.breakthrough_service
        )
        self.checkin_api = CheckinAPI(self.checkin_service, self.player_service)
        self.notification_api = NotificationAPI(self.notification_service)
        self.deep_seclusion_api = DeepSeclusionAPI(
            self.deep_seclusion_service, self.player_service
        )
        self.admin_api = AdminAPI(
            self.player_service,
            self.cultivation_service,
            self.combat_service,
            self.inventory_service,
            self.event_service,
            self.config_manager,
            self.breakthrough_service,
        )
        self.market_api = MarketAPI(self.market_service, self.player_service)
        # 初始化独立管理服务器
        admin_password = self.config_manager.get("admin_password", "xiuxian_admin")
        admin_port = self.config_manager.get("admin_port", 6186)
        self.admin_server = AdminServer(
            self.admin_api,
            self.checkin_api,
            self.notification_api,
            item_effect_service=self.item_effect_service,
            host="0.0.0.0",
            port=admin_port,
            password=admin_password,
        )

    async def initialize(self):
        """插件初始化"""
        # 更新插件描述信息
        self.description = "重生之凡人修仙，文字修仙游戏插件"
        logger.info("重生之凡人修仙游戏插件初始化中...")
        # 应用数据库迁移
        await self.migration_manager.apply_migrations()
        # 确保被动修为每日统计表存在（Bot重启后数据不丢失）
        await self.player_service.ensure_daily_stats_table()
        # 加载已注册玩家到内存缓存
        await self.player_service.load_all_players_to_cache()
        # 恢复进行中的深度闭关定时任务
        await self.deep_seclusion_service.restore_ongoing_seclusion_tasks()
        # 注册后台管理API路由
        await self.setup_api_routes()
        # 启动独立管理服务器
        try:
            actual_port = await self.admin_server.start()
            logger.info(
                f"修仙后台管理独立服务器已启动，访问地址: http://localhost:{actual_port}"
            )
        except Exception as e:
            logger.error(f"修仙后台管理独立服务器启动失败: {e}")
        # 启动定时通知检查任务（先停止旧任务避免重入）
        await self._stop_scheduled_notification_checker()
        self._start_scheduled_notification_checker()
        # 启动玩家状态定时tick任务（先停止旧任务避免重入）
        await self._stop_state_tick()
        self._start_state_tick()
        logger.info("重生之凡人修仙游戏插件初始化完成")

    async def terminate(self):
        """插件卸载"""
        logger.info("重生之凡人修仙游戏插件卸载中...")
        # 停止独立管理服务器
        try:
            await self.admin_server.stop()
        except Exception as e:
            logger.error(f"停止独立管理服务器失败: {e}")
        # 停止定时通知检查任务并等待其完成
        await self._stop_scheduled_notification_checker()
        # 停止玩家状态定时tick任务并等待其完成
        await self._stop_state_tick()
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

        self._scheduled_check_task = asyncio.create_task(_check_loop(), name="xiuxian_notification_checker")
        logger.info("定时通知检查任务已启动（每60秒检查一次）")

    async def _stop_scheduled_notification_checker(self):
        """停止定时通知检查后台任务"""
        import asyncio

        if self._scheduled_check_task and not self._scheduled_check_task.done():
            self._scheduled_check_task.cancel()
            try:
                await self._scheduled_check_task
            except asyncio.CancelledError:
                pass
            self._scheduled_check_task = None
            logger.info("定时通知检查任务已停止")

    # ==================== 玩家状态定时tick ====================

    _state_tick_task = None

    def _start_state_tick(self):
        """启动玩家状态定时tick后台任务"""
        import asyncio

        async def _tick_loop():
            while True:
                try:
                    await asyncio.sleep(600)
                    # 批量清理所有玩家的过期数据（丹毒、临时增益）
                    cleaned = await self.state_checker.cleanup_all_expired()
                    if cleaned > 0:
                        logger.info(f"玩家状态tick: 清理了{cleaned}条过期记录")

                    # 清理所有玩家的过期状态（道心破碎、避世等过期状态）
                    try:
                        await self.deep_seclusion_service.cleanup_expired_states()
                    except Exception as e:
                        logger.error(f"tick清理过期玩家状态失败: {e}")

                    # 检查所有玩家的突破状态（生成待通知列表）
                    notifications = await self.state_checker.tick_all_players()
                    for notification in notifications:
                        try:
                            user_id = notification["user_id"]
                            for msg in notification.get("messages", []):
                                try:
                                    await self.context.send_by_user_id(user_id, msg)
                                except Exception as e:
                                    logger.warning(f"tick通知发送失败(用户{user_id}): {e}")

                            # 执行自动突破
                            if notification.get("needs_auto_breakthrough"):
                                try:
                                    auto_break = await self.breakthrough_service.try_auto_breakthrough(
                                        notification["player_id"]
                                    )
                                    if auto_break and auto_break.get("message"):
                                        try:
                                            await self.context.send_by_user_id(user_id, auto_break["message"])
                                        except Exception as e:
                                            logger.warning(f"tick自动突破通知发送失败(用户{user_id}): {e}")
                                except Exception as e:
                                    logger.error(f"tick自动突破失败(玩家{notification['player_id']}): {e}")
                        except Exception as e:
                            logger.error(f"tick通知处理失败: {e}")
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"玩家状态tick循环异常: {e}")

        self._state_tick_task = asyncio.create_task(_tick_loop(), name="xiuxian_state_tick")
        logger.info("玩家状态定时tick已启动（每10分钟检查一次）")

    async def _stop_state_tick(self):
        """停止玩家状态定时tick后台任务"""
        import asyncio

        if self._state_tick_task and not self._state_tick_task.done():
            self._state_tick_task.cancel()
            try:
                await self._state_tick_task
            except asyncio.CancelledError:
                pass
            self._state_tick_task = None
            logger.info("玩家状态定时tick已停止")

    # ==================== 封禁检查辅助方法 ====================

    async def _check_player_banned(self, user_id: str) -> str | None:
        """
        检查玩家是否被封禁

        Args:
            user_id: 用户ID

        Returns:
            Optional[str]: 如果被封禁返回提示信息，否则返回 None
        """
        player = await self.player_service.get_player_by_user_id(user_id)
        if not player:
            return None

        ban_info = await self.player_service.get_ban_info(player.id)
        if ban_info["is_banned"]:
            reason = ban_info.get("ban_reason") or "违反游戏规则"
            return (
                f"【仙途阻断】\n"
                f"你已被仙界执法堂封禁，无法继续修仙。\n"
                f"封禁理由：{reason}\n"
                f"如有疑问，请联系管理员。"
            )
        return None

    # ==================== 事件监听区域 ====================

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """监听所有消息，自动为未注册用户创建角色，并记录玩家会话信息"""
        user_id = event.get_sender_id()

        # 检查玩家是否被封禁，被封禁则不再处理
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            return

        # 检查用户是否已注册，未注册则自动创建并跳过后续逻辑
        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error and "自动" in error:
            username = event.get_sender_name()
            await self.player_service.auto_register_player(user_id, username)
            return

        # player_dict 为 None 说明查询异常，跳过后续处理
        if not player_dict:
            return

        # 记录玩家会话信息，用于后续主动推送通知
        await self.notification_service.record_player_session(
            user_id=user_id,
            unified_msg_origin=event.unified_msg_origin,
            platform_name=event.get_platform_name(),
        )

        # 自动结算未完成的深度闭关
        try:
            settle_result = await self.deep_seclusion_api.settle_deep_seclusion(user_id)
            if settle_result:
                await event.send(MessageChain([Plain(settle_result)]))
        except Exception as e:
            logger.error(f"深度闭关结算失败: {e}")

        # 群聊发言被动增长修为（仅限群聊消息）
        if event.get_group_id():
            try:
                passive_result = await self.player_service.add_passive_experience(
                    player_id=player_dict["id"],
                    user_id=user_id,
                    message_content=event.message_str,
                    group_id=event.get_group_id(),
                )
                if passive_result.get("message"):
                    await event.send(MessageChain([Plain(passive_result["message"])]))
            except Exception as e:
                logger.error(f"被动增长修为失败: {e}")

        # 统一状态检查：突破提示、丹毒清理、buff过期清理、自动突破
        try:
            state_result = await self.state_checker.check_player_state(player_dict["id"])
            for msg in state_result.get("messages", []):
                await event.send(MessageChain([Plain(msg)]))
            if state_result.get("needs_auto_breakthrough"):
                try:
                    auto_break = await self.breakthrough_service.try_auto_breakthrough(
                        player_dict["id"]
                    )
                    if auto_break and auto_break.get("success"):
                        await event.send(MessageChain([Plain(auto_break["message"])]))
                    elif auto_break and auto_break.get("message"):
                        await event.send(MessageChain([Plain(auto_break["message"])]))
                except Exception as e:
                    logger.error(f"自动突破失败: {e}")
                    await event.send(MessageChain([Plain("【系统】自动突破时发生异常，请联系管理员")]))
        except Exception as e:
            logger.error(f"玩家状态检查失败: {e}")
            await event.send(MessageChain([Plain("【系统】状态检查时发生异常，请联系管理员")]))

    # ==================== 命令注册区域 ====================

    @filter.command("修仙状态")
    async def player_status(self, event: AstrMessageEvent):
        """查看修仙状态"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        result = await self.player_api.get_player_status(user_id)
        yield event.plain_result(result)

    @filter.command("闭关修炼")
    async def seclusion(self, event: AstrMessageEvent):
        """闭关修炼，获取大量修为，示例：闭关修炼"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        result = await self.cultivation_api.seclusion(user_id)
        yield event.plain_result(result)

    @filter.command("服用")
    async def use_pill(self, event: AstrMessageEvent):
        """服用丹药，示例：服用 聚灵丹 / 服用 回春丹 3"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        message = event.get_message_str().replace("服用", "").strip()

        if not message:
            yield event.plain_result(
                "用法：服用 <丹药名> [数量]\n示例：服用 聚灵丹 / 服用 回春丹 3"
            )
            return

        parts = message.rsplit(None, 1)
        if len(parts) == 2 and parts[1].isdigit():
            item_name = parts[0]
            quantity = int(parts[1])
        else:
            item_name = message
            quantity = 1

        result = await self.item_api.use_pill(user_id, item_name, quantity)
        yield event.plain_result(result)

    @filter.command("丹毒")
    async def toxicity_status(self, event: AstrMessageEvent):
        """查看丹毒状态，示例：丹毒"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        result = await self.item_api.get_toxicity_status(user_id)
        yield event.plain_result(result)

    @filter.command("使用")
    async def use_item(self, event: AstrMessageEvent):
        """使用物品（新效果系统），示例：使用 聚灵丹 / 使用 回春丹 3"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        message = event.get_message_str().replace("使用", "").strip()

        if not message:
            yield event.plain_result(
                "用法：使用 <物品名> [数量]\n示例：使用 聚灵丹 / 使用 回春丹 3"
            )
            return

        parts = message.rsplit(None, 1)
        if len(parts) == 2 and parts[1].isdigit():
            item_name = parts[0]
            quantity = int(parts[1])
        else:
            item_name = message
            quantity = 1

        result = await self.item_api.use_item(user_id, item_name, quantity)
        yield event.plain_result(result)

    @filter.command("储物袋")
    async def inventory(self, event: AstrMessageEvent):
        """查看储物袋"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        result = await self.item_api.get_inventory(user_id)
        yield event.plain_result(result)

    @filter.command("更改道号")
    async def change_username(self, event: AstrMessageEvent):
        """更改道号"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        new_username = event.get_message_str().replace("更改道号", "").strip()
        result = await self.player_api.change_username(user_id, new_username)
        yield event.plain_result(result)

    @filter.command("签到")
    async def checkin(self, event: AstrMessageEvent):
        """每日签到获取修为奖励"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        result = await self.checkin_api.checkin(user_id)
        yield event.plain_result(result)

    @filter.command("签到状态")
    async def checkin_status(self, event: AstrMessageEvent):
        """查看签到状态和奖励规则"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        result = await self.checkin_api.get_checkin_status(user_id)
        yield event.plain_result(result)

    @filter.command("签到排行")
    async def checkin_ranking(self, event: AstrMessageEvent):
        """查看签到排行榜"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        result = await self.checkin_api.get_checkin_ranking(user_id)
        yield event.plain_result(result)

    @filter.command("深度闭关")
    async def deep_seclusion(self, event: AstrMessageEvent):
        """开启深度闭关，长达8小时的自动挂机修炼"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        result = await self.deep_seclusion_api.start_deep_seclusion(user_id)
        yield event.plain_result(result)

    @filter.command("查看闭关")
    async def check_deep_seclusion(self, event: AstrMessageEvent):
        """查看深度闭关剩余时间"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        result = await self.deep_seclusion_api.get_deep_seclusion_status(user_id)
        yield event.plain_result(result)

    @filter.command("强行出关")
    async def force_end_seclusion(self, event: AstrMessageEvent):
        """强行结束深度闭关，收益大打折扣"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        result = await self.deep_seclusion_api.force_end_deep_seclusion(user_id)
        yield event.plain_result(result)

    @filter.command("避世")
    async def enter_peace(self, event: AstrMessageEvent):
        """开启和平模式（仅限炼气期），无法被攻击也无法攻击他人"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        result = await self.deep_seclusion_api.enter_peace_mode(user_id)
        yield event.plain_result(result)

    @filter.command("入世")
    async def exit_peace(self, event: AstrMessageEvent):
        """关闭和平模式，重返红尘纷争"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        result = await self.deep_seclusion_api.exit_peace_mode(user_id)
        yield event.plain_result(result)

    @filter.command("排行榜")
    async def leaderboard(self, event: AstrMessageEvent):
        """查看排行榜，示例：排行榜 境界 / 排行榜 发言 / 排行榜 财富"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return

        message = event.get_message_str().replace("排行榜", "").strip()
        category_map = {
            "境界": "realm",
            "修为": "realm",
            "发言": "chat",
            "财富": "wealth",
            "灵石": "wealth",
        }

        category = category_map.get(message, "realm")
        result = await self.player_service.get_leaderboard(category, limit=10)

        if not result:
            yield event.plain_result("暂无排行数据。")
            return

        category_names = {
            "realm": "【境界修为排行榜】",
            "chat": "【发言次数排行榜】",
            "wealth": "【财富值排行榜】",
        }

        lines = [category_names.get(category, "【排行榜】")]
        for item in result:
            rank = item["rank"]
            username = item["username"]
            realm = item["realm_name"]

            if category == "realm":
                exp = item["experience"]
                total_attrs = item.get("total_attrs", 0)
                lines.append(
                    f"第{rank}名：{username}（{realm}）- 修为{exp}，总属性{total_attrs}"
                )
            elif category == "chat":
                count = item["chat_count"]
                lines.append(f"第{rank}名：{username}（{realm}）- 发言{count}次")
            elif category == "wealth":
                stones = item["spirit_stone"]
                lines.append(f"第{rank}名：{username}（{realm}）- 灵石{stones}枚")
        lines.append("相关指令：排行榜 境界 / 排行榜 发言 / 排行榜 财富")
        yield event.plain_result("\n".join(lines))

    @filter.command("突破")
    async def breakthrough(self, event: AstrMessageEvent):
        """尝试境界突破，自动检测突破条件"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return

        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            yield event.plain_result(error)
            return

        # 先尝试自动突破（无条件或auto条件），若为manual条件则走手动突破
        auto_result = await self.breakthrough_service.try_auto_breakthrough(
            player_dict["id"]
        )
        if auto_result:
            if auto_result.get("is_manual_condition"):
                # manual 条件：走手动突破流程（有概率失败）
                manual_result = await self.breakthrough_service.try_manual_breakthrough(
                    player_dict["id"]
                )
                yield event.plain_result(manual_result.get("message", "突破异常"))
            elif auto_result.get("success"):
                yield event.plain_result(auto_result["message"])
            elif auto_result.get("message"):
                yield event.plain_result(auto_result["message"])
            else:
                yield event.plain_result("当前不满足突破条件，请继续修炼。")
        else:
            yield event.plain_result("当前不满足突破条件，请继续修炼。")

    @filter.command("冲击结丹")
    async def breakthrough_jiedan(self, event: AstrMessageEvent):
        """冲击结丹之劫，需要集齐天火液、凝魂丹、三转重元丹"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return

        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            yield event.plain_result(error)
            return

        result = await self.breakthrough_service.try_manual_breakthrough(
            player_dict["id"], target_realm_id="realm_007"
        )
        yield event.plain_result(result.get("message", "冲击结丹异常"))

    @filter.command("冲击元婴")
    async def breakthrough_yuanying(self, event: AstrMessageEvent):
        """冲击元婴之劫，需要集齐养魂木x25、九曲灵参丹、青鸾天盾"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return

        player_dict, error = await self.player_service.check_player_registered(user_id)
        if error:
            yield event.plain_result(error)
            return

        result = await self.breakthrough_service.try_manual_breakthrough(
            player_dict["id"], target_realm_id="realm_010"
        )
        yield event.plain_result(result.get("message", "冲击元婴异常"))

    @filter.command("修仙帮助")
    async def help_command(self, event: AstrMessageEvent):
        """显示帮助信息"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return
        help_text = """
【修仙游戏帮助】
首次发言自动注册修仙角色
修仙状态 - 查看角色状态
闭关修炼 - 闭关修炼获取大量修为(有冷却)
深度闭关 - 开启8小时自动挂机修炼(每日限1次，冷却22小时)
查看闭关 - 查看深度闭关剩余时间
强行出关 - 提前结束深度闭关(收益50%)
避世 - 开启和平模式(仅限炼气期)
入世 - 关闭和平模式
服用 <丹药名> [数量] - 服用丹药，示例：服用 聚灵丹 / 服用 回春丹 3
使用 <物品名> [数量] - 使用物品（新效果系统），示例：使用 聚灵丹 / 使用 回春丹 3
丹毒 - 查看丹毒状态
储物袋 - 查看储物袋物品
更改道号 <新道号> - 修改角色道号（2-6个中文字符）
签到 - 每日签到获取修为奖励
签到状态 - 查看签到状态和奖励规则
签到排行 - 查看签到排行榜
排行榜 <类型> - 查看排行榜，类型：境界/发言/财富
突破 - 尝试境界突破（自动检测条件）
冲击结丹 - 冲击结丹之劫（需集齐三样至宝）
冲击元婴 - 冲击元婴之劫（需集齐三样至宝）
发送公告 <标题> | <内容> - 发送公告给所有玩家(管理员)
发送通知 <标题> | <内容> | <用户ID> - 发送通知给指定玩家(管理员)
通知历史 - 查看通知历史记录(管理员)
定时通知 列表/创建/开启/关闭/删除 - 管理定时通知(管理员)
万宝楼 - 查看市场商品列表
万宝楼 <页数> - 查看指定页商品
万宝楼 搜索 <物品名> - 搜索商品
万宝楼 筛选 <类型> - 按类型筛选(丹药/法宝/材料/图纸/种子)
上架 <物品名>*<数量> 换 <所需物品1>*<数量1> ... - 上架物品到市场
购买 <挂单ID>*<数量> - 购买商品
我的货摊 - 查看我的出售商品
下架 <挂单ID> - 下架商品
修仙帮助 - 显示本帮助
        """
        yield event.plain_result(help_text.strip())

    # ==================== 万宝楼命令区域 ====================

    @filter.command("万宝楼")
    async def market(self, event: AstrMessageEvent):
        """浏览万宝楼市场"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return

        message = event.get_message_str().replace("万宝楼", "").strip()

        if not message:
            result = await self.market_api.browse_market(user_id, page=1)
            yield event.plain_result(result)
            return

        parts = message.split(None, 1)
        sub_cmd = parts[0] if parts else ""
        arg = parts[1] if len(parts) > 1 else ""

        if sub_cmd == "搜索" and arg:
            result = await self.market_api.browse_market(
                user_id, page=1, search_keyword=arg
            )
            yield event.plain_result(result)
        elif sub_cmd == "筛选" and arg:
            result = await self.market_api.browse_market(
                user_id, page=1, item_type=arg
            )
            yield event.plain_result(result)
        elif sub_cmd.isdigit():
            page = int(sub_cmd)
            result = await self.market_api.browse_market(user_id, page=page)
            yield event.plain_result(result)
        else:
            result = await self.market_api.browse_market(user_id, page=1)
            yield event.plain_result(result)

    @filter.command("上架")
    async def list_item(self, event: AstrMessageEvent):
        """上架物品到万宝楼"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return

        message = event.get_message_str().replace("上架", "").strip()
        result = await self.market_api.create_listing(user_id, f"上架 {message}")
        yield event.plain_result(result)

    @filter.command("购买")
    async def purchase_item(self, event: AstrMessageEvent):
        """购买万宝楼商品"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return

        message = event.get_message_str().replace("购买", "").strip()

        if not message:
            yield event.plain_result(
                "用法：购买 <挂单ID> 或 购买 <挂单ID>*<数量>\n"
                "示例：购买 ABC123\n"
                "示例：购买 ABC123*5"
            )
            return

        parts = message.rsplit("*", 1)
        listing_id = parts[0].strip()
        quantity = int(parts[1]) if len(parts) > 1 and parts[1].strip().isdigit() else None

        result = await self.market_api.purchase(user_id, listing_id, quantity)
        yield event.plain_result(result)

    @filter.command("我的货摊")
    async def my_stalls(self, event: AstrMessageEvent):
        """查看我的货摊"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return

        result = await self.market_api.get_my_stalls(user_id)
        yield event.plain_result(result)

    @filter.command("下架")
    async def cancel_listing(self, event: AstrMessageEvent):
        """下架万宝楼商品"""
        user_id = event.get_sender_id()
        ban_message = await self._check_player_banned(user_id)
        if ban_message:
            yield event.plain_result(ban_message)
            return

        message = event.get_message_str().replace("下架", "").strip()

        if not message:
            yield event.plain_result("用法：下架 <挂单ID>\n示例：下架 ABC123")
            return

        result = await self.market_api.cancel_listing(user_id, message)
        yield event.plain_result(result)

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
            history_text += f"   状态：{status_text}，成功：{notice['sent_count']}人，失败：{notice['fail_count']}人\n"

        yield event.plain_result(history_text.strip())

    @filter.permission_type(PermissionType.ADMIN)
    @filter.command("定时通知")
    async def scheduled_notification(self, event: AstrMessageEvent):
        """管理定时通知（管理员），示例：定时通知 列表 / 定时通知 创建 标题|内容|cron / 定时通知 开启 1 / 定时通知 关闭 1 / 定时通知 删除 1"""
        message = event.get_message_str().replace("定时通知", "").strip()

        if not message or message == "列表":
            result = await self.notification_api.get_scheduled_notifications(
                page=1, page_size=10
            )
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
                yield event.plain_result(
                    "格式：定时通知 创建 <标题>|<内容>|<Cron表达式>\n示例：定时通知 创建 每日提醒|记得修炼|0 8 * * *"
                )
                return

            create_parts = parts[1].split("|", 2)
            if len(create_parts) < 3:
                yield event.plain_result(
                    "格式：定时通知 创建 <标题>|<内容>|<Cron表达式>"
                )
                return

            title = create_parts[0].strip()
            content = create_parts[1].strip()
            cron_expr = create_parts[2].strip()

            result = await self.notification_api.create_scheduled_notification(
                title=title,
                content=content,
                cron_expression=cron_expr,
                created_by=event.get_sender_id(),
            )

            if not result.get("success", False):
                yield event.plain_result(f"创建失败：{result.get('error', '未知错误')}")
            else:
                yield event.plain_result(
                    f"定时通知创建成功！ID: {result['data']['id']}"
                )

        elif action in ("开启", "启用"):
            if len(parts) < 2:
                yield event.plain_result("格式：定时通知 开启 <ID>")
                return
            try:
                schedule_id = int(parts[1].strip())
            except ValueError:
                yield event.plain_result("ID必须为数字")
                return

            result = await self.notification_api.toggle_scheduled_notification(
                schedule_id, True
            )
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

            result = await self.notification_api.toggle_scheduled_notification(
                schedule_id, False
            )
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

            result = await self.notification_api.delete_scheduled_notification(
                schedule_id
            )
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
    # 所有后台管理API已完全迁移到独立HTTP服务器(AdminServer)
    # 独立服务器在插件初始化时自动启动，默认端口6186
    # 访问地址: http://localhost:6186/
    # 后台管理完全不依赖AstrBot Dashboard，可直接通过浏览器访问

    async def setup_api_routes(self):
        """设置后台管理API路由

        现已全部迁移到独立AdminServer，此方法保留用于兼容性
        """
        logger.info(
            "修仙游戏后台管理API已迁移到独立服务器，不再通过AstrBot插件路由注册"
        )
