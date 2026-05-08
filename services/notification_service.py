"""
通知推送服务
负责系统通知和公告的推送，以及玩家会话信息的管理
"""

import json
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING

from astrbot.api import logger
from astrbot.core.message.components import Plain
from astrbot.core.message.message_event_result import MessageChain

from ..database import DatabaseManager

if TYPE_CHECKING:
    from ..config import ConfigManager
    from .player_service import PlayerService
    from astrbot.api.star import Context


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
                SET unified_msg_origin = ?, platform_name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?""",
                (unified_msg_origin, platform_name, user_id),
            )
        else:
            await self.db.execute(
                """INSERT INTO player_sessions (user_id, unified_msg_origin, platform_name)
                VALUES (?, ?, ?)""",
                (user_id, unified_msg_origin, platform_name),
            )
        await self.db.commit()

    async def get_player_session(self, user_id: str) -> Optional[Dict[str, Any]]:
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

    async def get_all_sessions(self) -> List[Dict[str, Any]]:
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
        target_ids: Optional[List[str]] = None,
        sender_id: str = "system",
    ) -> Dict[str, Any]:
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
        target_ids: Optional[List[str]] = None,
        sender_id: str = "system",
    ) -> Dict[str, Any]:
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
        target_ids: Optional[List[str]],
    ) -> Optional[List[str]]:
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
        target_user_ids: List[str],
        title: str,
        content: str,
    ) -> Tuple[int, int]:
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
    ) -> Dict[str, Any]:
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

    async def get_notification_by_id(self, notification_id: int) -> Optional[Dict]:
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
