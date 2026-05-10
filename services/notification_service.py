"""
通知推送服务
负责系统通知和公告的推送，以及玩家会话信息的管理
"""

import json
from typing import TYPE_CHECKING, Any

from astrbot.api import logger
from astrbot.core.message.components import Plain
from astrbot.core.message.message_event_result import MessageChain

from ..database import DatabaseManager
from ..utils import bj_now_iso

if TYPE_CHECKING:
    from astrbot.api.star import Context

    from ..config import ConfigManager
    from .player_service import PlayerService


class NotificationService:
    """通知推送服务类，管理通知记录、玩家会话和主动消息推送"""

    def __init__(
        self,
        db_manager: DatabaseManager,
        player_service: "PlayerService",
        context: "Context",
        config_manager: "ConfigManager",
    ):
        """
        初始化通知服务

        Args:
            db_manager: 数据库管理器
            player_service: 玩家服务
            context: AstrBot上下文，用于主动发送消息
            config_manager: 配置管理器
        """
        self.db = db_manager
        self.player_service = player_service
        self.context = context
        self.config_manager = config_manager

    # ==================== 玩家会话管理 ====================

    async def record_player_session(
        self,
        user_id: str,
        unified_msg_origin: str,
        platform_name: str,
    ) -> None:
        """
        记录或更新玩家会话信息，用于后续主动推送消息

        Args:
            user_id: 玩家用户ID
            unified_msg_origin: 统一消息来源标识 (platform_id:message_type:session_id)
            platform_name: 平台名称
        """
        existing = await self.db.fetch_one(
            "SELECT id FROM player_sessions WHERE user_id = ?",
            (user_id,),
        )
        if existing:
            await self.db.execute(
                """UPDATE player_sessions
                SET unified_msg_origin = ?, platform_name = ?, updated_at = ?
                WHERE user_id = ?""",
                (unified_msg_origin, platform_name, bj_now_iso(), user_id),
            )
        else:
            await self.db.execute(
                """INSERT INTO player_sessions (user_id, unified_msg_origin, platform_name)
                VALUES (?, ?, ?)""",
                (user_id, unified_msg_origin, platform_name),
            )
        await self.db.commit()

    async def get_player_session(self, user_id: str) -> dict[str, Any] | None:
        """
        获取玩家会话信息

        Args:
            user_id: 玩家用户ID

        Returns:
            会话信息字典或None
        """
        return await self.db.fetch_one(
            "SELECT * FROM player_sessions WHERE user_id = ?",
            (user_id,),
        )

    async def get_all_sessions(self) -> list[dict[str, Any]]:
        """
        获取所有已记录的玩家会话

        Returns:
            会话信息列表
        """
        return await self.db.fetch_all(
            "SELECT * FROM player_sessions ORDER BY updated_at DESC"
        )

    # ==================== 通知记录管理 ====================

    async def create_notification(
        self,
        title: str,
        content: str,
        target_type: str = "all",
        target_ids: list[str] | None = None,
        sender_id: str = "system",
    ) -> dict[str, Any]:
        """
        创建通知记录（不立即发送）

        Args:
            title: 通知标题
            content: 通知内容
            target_type: 目标类型 (all=所有玩家, specific=指定玩家, realm=指定境界)
            target_ids: 目标ID列表（当target_type=specific或realm时必填）
            sender_id: 发送者ID

        Returns:
            创建的通知记录字典
        """
        await self.db.execute(
            """INSERT INTO notifications (title, content, target_type, target_ids, sender_id, status)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                title,
                content,
                target_type,
                json.dumps(target_ids) if target_ids else None,
                sender_id,
                "pending",
            ),
        )
        await self.db.commit()

        notification = await self.db.fetch_one(
            "SELECT * FROM notifications ORDER BY id DESC LIMIT 1"
        )
        return notification

    async def send_notification(
        self,
        title: str,
        content: str,
        target_type: str = "all",
        target_ids: list[str] | None = None,
        sender_id: str = "system",
    ) -> dict[str, Any]:
        """
        发送通知：创建记录并推送给目标玩家

        Args:
            title: 通知标题
            content: 通知内容
            target_type: 目标类型 (all=所有玩家, specific=指定玩家, realm=指定境界)
            target_ids: 目标ID列表（当target_type=specific或realm时必填）
            sender_id: 发送者ID

        Returns:
            发送结果字典，包含成功/失败计数
        """
        notification = await self.create_notification(
            title=title,
            content=content,
            target_type=target_type,
            target_ids=target_ids,
            sender_id=sender_id,
        )
        if not notification:
            return {"success": False, "error": "创建通知记录失败"}

        notification_id = notification["id"]

        await self.db.execute(
            "UPDATE notifications SET status = ? WHERE id = ?",
            ("sending", notification_id),
        )
        await self.db.commit()

        target_user_ids = await self._resolve_targets(target_type, target_ids)
        if target_user_ids is None:
            await self.db.execute(
                "UPDATE notifications SET status = ? WHERE id = ?",
                ("failed", notification_id),
            )
            await self.db.commit()
            return {"success": False, "error": f"不支持的目标类型: {target_type}"}

        sent_count, fail_count = await self._push_to_targets(
            target_user_ids, title, content
        )

        final_status = "completed" if fail_count == 0 else "partial"
        if sent_count == 0:
            final_status = "failed"

        await self.db.execute(
            "UPDATE notifications SET sent_count = ?, fail_count = ?, status = ? WHERE id = ?",
            (sent_count, fail_count, final_status, notification_id),
        )
        await self.db.commit()

        return {
            "success": sent_count > 0,
            "notification_id": notification_id,
            "sent_count": sent_count,
            "fail_count": fail_count,
            "total_targets": len(target_user_ids),
        }

    async def _resolve_targets(
        self,
        target_type: str,
        target_ids: list[str] | None,
    ) -> list[str] | None:
        """
        根据目标类型解析出目标用户ID列表

        Args:
            target_type: 目标类型
            target_ids: 目标ID列表

        Returns:
            用户ID列表，或None表示不支持的目标类型
        """
        if target_type == "all":
            sessions = await self.get_all_sessions()
            return [s["user_id"] for s in sessions]
        elif target_type == "specific":
            if not target_ids:
                return []
            return target_ids
        elif target_type == "realm":
            if not target_ids:
                return []
            realm_id = target_ids[0]
            players = await self.db.fetch_all(
                "SELECT user_id FROM players WHERE realm_id = ?",
                (realm_id,),
            )
            return [p["user_id"] for p in players]
        else:
            return None

    async def _push_to_targets(
        self,
        target_user_ids: list[str],
        title: str,
        content: str,
    ) -> tuple[int, int]:
        """
        向目标用户推送消息

        Args:
            target_user_ids: 目标用户ID列表
            title: 通知标题
            content: 通知内容

        Returns:
            (成功数, 失败数) 元组
        """
        sent_count = 0
        fail_count = 0
        full_message = f"【{title}】\n{content}"

        for user_id in target_user_ids:
            try:
                session_info = await self.get_player_session(user_id)
                if not session_info:
                    logger.warning(f"用户 {user_id} 无会话记录，跳过推送")
                    fail_count += 1
                    continue

                umo = session_info["unified_msg_origin"]
                message_chain = MessageChain([Plain(full_message)])
                result = await self.context.send_message(umo, message_chain)
                if result:
                    sent_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(f"发送通知给用户 {user_id} 失败: {e}")
                fail_count += 1

        return sent_count, fail_count

    # ==================== 通知查询 ====================

    async def get_notification_history(
        self, page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        """
        获取通知历史（分页）

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            分页结果字典
        """
        offset = (page - 1) * page_size

        notifications = await self.db.fetch_all(
            """SELECT * FROM notifications
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?""",
            (page_size, offset),
        )

        total = await self.db.fetch_one("SELECT COUNT(*) as count FROM notifications")

        return {
            "items": notifications,
            "total": total["count"] if total else 0,
            "page": page,
            "page_size": page_size,
        }

    async def get_notification_by_id(self, notification_id: int) -> dict | None:
        """
        根据ID获取通知详情

        Args:
            notification_id: 通知ID

        Returns:
            通知详情字典或None
        """
        return await self.db.fetch_one(
            "SELECT * FROM notifications WHERE id = ?",
            (notification_id,),
        )

    async def delete_notification(self, notification_id: int) -> bool:
        """
        删除通知记录

        Args:
            notification_id: 通知ID

        Returns:
            是否删除成功
        """
        cursor = await self.db.execute(
            "DELETE FROM notifications WHERE id = ?",
            (notification_id,),
        )
        await self.db.commit()
        return cursor.rowcount > 0

    # ==================== 通知模板 ====================

    def render_template(
        self, template_id: str, variables: dict[str, Any]
    ) -> tuple[str | None, str | None]:
        """
        渲染通知模板，用变量替换模板中的占位符

        Args:
            template_id: 模板ID
            variables: 变量字典，用于替换模板中的 {key} 占位符

        Returns:
            (标题, 内容) 元组，如果模板不存在则返回 (None, None)

        Example:
            >>> title, content = svc.render_template("breakthrough_success", {"realm": "金丹期", "username": "张三"})
            >>> # title = "突破成功", content = "恭喜张三突破至金丹期！"
        """
        templates = self.config_manager.get("notification.templates", [])
        for tpl in templates:
            if tpl.get("id") == template_id:
                title = tpl.get("title_template", "")
                content = tpl.get("content_template", "")
                try:
                    title = title.format(**variables)
                    content = content.format(**variables)
                except KeyError as e:
                    logger.warning(f"模板变量缺失: {e}, 模板ID: {template_id}")
                return title, content
        return None, None

    def get_all_templates(self) -> list[dict[str, Any]]:
        """
        获取所有通知模板

        Returns:
            模板列表
        """
        return self.config_manager.get("notification.templates", [])

    async def send_notification_by_template(
        self,
        template_id: str,
        variables: dict[str, Any],
        target_type: str = "all",
        target_ids: list[str] | None = None,
        sender_id: str = "system",
    ) -> dict[str, Any]:
        """
        使用模板发送通知

        Args:
            template_id: 模板ID
            variables: 模板变量字典
            target_type: 目标类型
            target_ids: 目标ID列表
            sender_id: 发送者ID

        Returns:
            发送结果字典
        """
        title, content = self.render_template(template_id, variables)
        if title is None:
            return {"success": False, "error": f"通知模板 {template_id} 不存在"}

        return await self.send_notification(
            title=title,
            content=content,
            target_type=target_type,
            target_ids=target_ids,
            sender_id=sender_id,
        )

    # ==================== 定时通知管理 ====================

    async def create_scheduled_notification(
        self,
        title: str,
        content: str,
        cron_expression: str,
        target_type: str = "all",
        target_ids: list[str] | None = None,
        template_id: str | None = None,
        template_variables: dict[str, Any] | None = None,
        created_by: str = "system",
    ) -> dict[str, Any]:
        """
        创建定时通知

        Args:
            title: 通知标题
            content: 通知内容
            cron_expression: Cron表达式(分 时 日 月 周)
            target_type: 目标类型
            target_ids: 目标ID列表
            template_id: 通知模板ID(可选)
            template_variables: 模板变量(可选)
            created_by: 创建者ID

        Returns:
            创建的定时通知记录字典
        """
        await self.db.execute(
            """INSERT INTO scheduled_notifications
            (title, content, target_type, target_ids, template_id, template_variables,
             cron_expression, enabled, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (
                title,
                content,
                target_type,
                json.dumps(target_ids) if target_ids else None,
                template_id,
                json.dumps(template_variables) if template_variables else None,
                cron_expression,
                created_by,
            ),
        )
        await self.db.commit()

        record = await self.db.fetch_one(
            "SELECT * FROM scheduled_notifications ORDER BY id DESC LIMIT 1"
        )
        return record

    async def get_scheduled_notifications(
        self, page: int = 1, page_size: int = 20
    ) -> dict[str, Any]:
        """
        获取定时通知列表（分页）

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            分页结果字典
        """
        offset = (page - 1) * page_size

        records = await self.db.fetch_all(
            """SELECT * FROM scheduled_notifications
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?""",
            (page_size, offset),
        )

        total = await self.db.fetch_one(
            "SELECT COUNT(*) as count FROM scheduled_notifications"
        )

        return {
            "items": records,
            "total": total["count"] if total else 0,
            "page": page,
            "page_size": page_size,
        }

    async def get_scheduled_notification_by_id(self, schedule_id: int) -> dict | None:
        """
        根据ID获取定时通知

        Args:
            schedule_id: 定时通知ID

        Returns:
            定时通知记录字典或None
        """
        return await self.db.fetch_one(
            "SELECT * FROM scheduled_notifications WHERE id = ?",
            (schedule_id,),
        )

    async def toggle_scheduled_notification(
        self, schedule_id: int, enabled: bool
    ) -> bool:
        """
        启用/禁用定时通知

        Args:
            schedule_id: 定时通知ID
            enabled: 是否启用

        Returns:
            是否操作成功
        """
        cursor = await self.db.execute(
            "UPDATE scheduled_notifications SET enabled = ?, updated_at = ? WHERE id = ?",
            (1 if enabled else 0, bj_now_iso(), schedule_id),
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def update_scheduled_notification(
        self, schedule_id: int, **kwargs
    ) -> dict | None:
        """
        更新定时通知

        Args:
            schedule_id: 定时通知ID
            **kwargs: 要更新的字段

        Returns:
            更新后的记录字典或None
        """
        allowed_fields = {
            "title",
            "content",
            "target_type",
            "target_ids",
            "template_id",
            "template_variables",
            "cron_expression",
        }
        updates = {}
        for field in allowed_fields:
            if field in kwargs:
                value = kwargs[field]
                if field in ("target_ids", "template_variables") and value is not None:
                    value = json.dumps(value)
                updates[field] = value

        if not updates:
            return await self.get_scheduled_notification_by_id(schedule_id)

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [schedule_id]

        await self.db.execute(
            f"UPDATE scheduled_notifications SET {set_clause}, updated_at = ? WHERE id = ?",
            values + [bj_now_iso(), schedule_id],
        )
        await self.db.commit()

        return await self.get_scheduled_notification_by_id(schedule_id)

    async def delete_scheduled_notification(self, schedule_id: int) -> bool:
        """
        删除定时通知

        Args:
            schedule_id: 定时通知ID

        Returns:
            是否删除成功
        """
        cursor = await self.db.execute(
            "DELETE FROM scheduled_notifications WHERE id = ?",
            (schedule_id,),
        )
        await self.db.commit()
        return cursor.rowcount > 0

    async def get_due_scheduled_notifications(self) -> list[dict[str, Any]]:
        """
        获取当前时间应该执行的定时通知

        Returns:
            到期的定时通知列表
        """
        from datetime import datetime

        now = datetime.now()
        current_min = now.minute
        current_hour = now.hour
        current_day = now.day
        current_month = now.month
        current_weekday = now.weekday()

        all_enabled = await self.db.fetch_all(
            "SELECT * FROM scheduled_notifications WHERE enabled = 1"
        )

        due = []
        for record in all_enabled:
            if self._cron_matches(
                record["cron_expression"],
                current_min,
                current_hour,
                current_day,
                current_month,
                current_weekday,
            ):
                last_run = record.get("last_run_at")
                if last_run:
                    try:
                        last_dt = datetime.fromisoformat(str(last_run))
                        if (now - last_dt).total_seconds() < 60:
                            continue
                    except (ValueError, TypeError):
                        pass
                due.append(record)

        return due

    def _cron_matches(
        self,
        cron_expr: str,
        minute: int,
        hour: int,
        day: int,
        month: int,
        weekday: int,
    ) -> bool:
        """
        判断当前时间是否匹配Cron表达式

        Args:
            cron_expr: Cron表达式(分 时 日 月 周)
            minute: 当前分钟
            hour: 当前小时
            day: 当前日
            month: 当前月
            weekday: 当前星期(0=周一)

        Returns:
            是否匹配
        """
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return False

        cron_weekday = weekday + 1 if weekday < 6 else 0

        checks = [
            (parts[0], minute),
            (parts[1], hour),
            (parts[2], day),
            (parts[3], month),
            (parts[4], cron_weekday),
        ]

        for cron_part, value in checks:
            if not self._cron_field_matches(cron_part, value):
                return False
        return True

    @staticmethod
    def _cron_field_matches(field: str, value: int) -> bool:
        """
        判断Cron单个字段是否匹配

        Args:
            field: Cron字段表达式
            value: 当前值

        Returns:
            是否匹配
        """
        if field == "*":
            return True

        for part in field.split(","):
            if "-" in part:
                start, end = part.split("-", 1)
                if int(start) <= value <= int(end):
                    return True
            elif "/" in part:
                base, step = part.split("/", 1)
                base_val = 0 if base == "*" else int(base)
                if value >= base_val and (value - base_val) % int(step) == 0:
                    return True
            else:
                if value == int(part):
                    return True
        return False

    async def execute_scheduled_notification(self, schedule_id: int) -> dict[str, Any]:
        """
        执行定时通知

        Args:
            schedule_id: 定时通知ID

        Returns:
            执行结果字典
        """
        record = await self.get_scheduled_notification_by_id(schedule_id)
        if not record:
            return {"success": False, "error": "定时通知不存在"}

        title = record["title"]
        content = record["content"]

        if record.get("template_id"):
            variables = {}
            if record.get("template_variables"):
                try:
                    variables = json.loads(record["template_variables"])
                except (json.JSONDecodeError, TypeError):
                    pass
            tpl_title, tpl_content = self.render_template(
                record["template_id"], variables
            )
            if tpl_title is not None:
                title = tpl_title
                content = tpl_content

        target_ids = None
        if record.get("target_ids"):
            try:
                target_ids = json.loads(record["target_ids"])
            except (json.JSONDecodeError, TypeError):
                pass

        result = await self.send_notification(
            title=title,
            content=content,
            target_type=record["target_type"],
            target_ids=target_ids,
            sender_id=f"scheduler:{schedule_id}",
        )

        await self.db.execute(
            """UPDATE scheduled_notifications
            SET last_run_at = ?, run_count = run_count + 1, updated_at = ?
            WHERE id = ?""",
            (bj_now_iso(), bj_now_iso(), schedule_id),
        )
        await self.db.commit()

        return result
