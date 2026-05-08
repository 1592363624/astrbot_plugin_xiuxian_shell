"""
通知推送API
提供系统通知和公告推送的HTTP接口，同时供命令调用共享
HTTP处理方法兼容AstrBot Dashboard(Quart)路由分发机制
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING

from quart import jsonify, request

if TYPE_CHECKING:
    from ..services.notification_service import NotificationService


class NotificationAPI:
    """通知推送API类，前后端共享同一套接口"""

    def __init__(self, notification_service: "NotificationService"):
        """
        初始化通知推送API

        Args:
            notification_service: 通知推送服务
        """
        self.notification_service = notification_service

    # ==================== 通用业务方法（前后端共享） ====================

    async def send_notification(
        self,
        title: str,
        content: str,
        target_type: str = "all",
        target_ids: Optional[List[str]] = None,
        sender_id: str = "system",
    ) -> Dict[str, Any]:
        """
        发送通知（通用方法，HTTP和命令共用）

        Args:
            title: 通知标题
            content: 通知内容
            target_type: 目标类型 (all/specific/realm)
            target_ids: 目标ID列表
            sender_id: 发送者ID

        Returns:
            发送结果字典

        Example:
            >>> result = await api.send_notification("公告", "内容", target_type="all")
            >>> result = await api.send_notification("通知", "内容", target_type="specific", target_ids=["user1"])
        """
        if not title or not content:
            return {"success": False, "error": "标题和内容不能为空"}

        if target_type == "specific" and not target_ids:
            return {"success": False, "error": "指定目标类型时必须提供target_ids"}

        if target_type == "realm" and not target_ids:
            return {"success": False, "error": "境界目标类型时必须提供target_ids(境界ID)"}

        return await self.notification_service.send_notification(
            title=title,
            content=content,
            target_type=target_type,
            target_ids=target_ids,
            sender_id=sender_id,
        )

    async def get_notification_history(
        self, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取通知历史（通用方法，HTTP和命令共用）

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            通知历史字典
        """
        return await self.notification_service.get_notification_history(
            page=page, page_size=page_size
        )

    async def get_notification_detail(self, notification_id: int) -> Dict[str, Any]:
        """
        获取通知详情（通用方法，HTTP和命令共用）

        Args:
            notification_id: 通知ID

        Returns:
            通知详情字典
        """
        notification = await self.notification_service.get_notification_by_id(
            notification_id
        )
        if not notification:
            return {"success": False, "error": "通知不存在"}
        return {"success": True, "data": notification}

    async def delete_notification(self, notification_id: int) -> Dict[str, Any]:
        """
        删除通知记录（通用方法，HTTP和命令共用）

        Args:
            notification_id: 通知ID

        Returns:
            删除结果字典
        """
        deleted = await self.notification_service.delete_notification(notification_id)
        if not deleted:
            return {"success": False, "error": "通知不存在或删除失败"}
        return {"success": True, "message": "通知已删除"}

    async def send_notification_by_template(
        self,
        template_id: str,
        variables: Dict[str, Any],
        target_type: str = "all",
        target_ids: Optional[List[str]] = None,
        sender_id: str = "system",
    ) -> Dict[str, Any]:
        """
        使用模板发送通知（通用方法，HTTP和命令共用）

        Args:
            template_id: 模板ID
            variables: 模板变量字典
            target_type: 目标类型
            target_ids: 目标ID列表
            sender_id: 发送者ID

        Returns:
            发送结果字典

        Example:
            >>> result = await api.send_notification_by_template(
            ...     "system_maintenance", {"time": "今晚8点", "duration": "2小时"}
            ... )
        """
        if not template_id:
            return {"success": False, "error": "模板ID不能为空"}

        return await self.notification_service.send_notification_by_template(
            template_id=template_id,
            variables=variables,
            target_type=target_type,
            target_ids=target_ids,
            sender_id=sender_id,
        )

    async def get_templates(self) -> Dict[str, Any]:
        """
        获取所有通知模板（通用方法，HTTP和命令共用）

        Returns:
            模板列表字典
        """
        templates = self.notification_service.get_all_templates()
        return {"success": True, "data": templates}

    # ==================== 定时通知通用方法（前后端共享） ====================

    async def create_scheduled_notification(
        self,
        title: str,
        content: str,
        cron_expression: str,
        target_type: str = "all",
        target_ids: Optional[List[str]] = None,
        template_id: Optional[str] = None,
        template_variables: Optional[Dict[str, Any]] = None,
        created_by: str = "system",
    ) -> Dict[str, Any]:
        """
        创建定时通知（通用方法，HTTP和命令共用）

        Args:
            title: 通知标题
            content: 通知内容
            cron_expression: Cron表达式
            target_type: 目标类型
            target_ids: 目标ID列表
            template_id: 通知模板ID
            template_variables: 模板变量
            created_by: 创建者ID

        Returns:
            创建结果字典

        Example:
            >>> result = await api.create_scheduled_notification(
            ...     "每日提醒", "记得修炼", "0 8 * * *", target_type="all"
            ... )
        """
        if not title or not content:
            return {"success": False, "error": "标题和内容不能为空"}
        if not cron_expression:
            return {"success": False, "error": "Cron表达式不能为空"}

        parts = cron_expression.strip().split()
        if len(parts) != 5:
            return {"success": False, "error": "Cron表达式格式错误，需要5个字段(分 时 日 月 周)"}

        record = await self.notification_service.create_scheduled_notification(
            title=title,
            content=content,
            cron_expression=cron_expression,
            target_type=target_type,
            target_ids=target_ids,
            template_id=template_id,
            template_variables=template_variables,
            created_by=created_by,
        )
        return {"success": True, "data": record}

    async def get_scheduled_notifications(
        self, page: int = 1, page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取定时通知列表（通用方法，HTTP和命令共用）

        Args:
            page: 页码
            page_size: 每页数量

        Returns:
            定时通知列表字典
        """
        result = await self.notification_service.get_scheduled_notifications(
            page=page, page_size=page_size
        )
        return {"success": True, "data": result}

    async def toggle_scheduled_notification(
        self, schedule_id: int, enabled: bool
    ) -> Dict[str, Any]:
        """
        启用/禁用定时通知（通用方法，HTTP和命令共用）

        Args:
            schedule_id: 定时通知ID
            enabled: 是否启用

        Returns:
            操作结果字典
        """
        success = await self.notification_service.toggle_scheduled_notification(
            schedule_id, enabled
        )
        if not success:
            return {"success": False, "error": "定时通知不存在"}
        return {"success": True, "message": f"已{'启用' if enabled else '禁用'}定时通知"}

    async def delete_scheduled_notification(self, schedule_id: int) -> Dict[str, Any]:
        """
        删除定时通知（通用方法，HTTP和命令共用）

        Args:
            schedule_id: 定时通知ID

        Returns:
            删除结果字典
        """
        success = await self.notification_service.delete_scheduled_notification(
            schedule_id
        )
        if not success:
            return {"success": False, "error": "定时通知不存在或删除失败"}
        return {"success": True, "message": "定时通知已删除"}

    # ==================== HTTP路由处理方法（Quart兼容） ====================

    async def handle_send_notification(self, **kwargs) -> Dict[str, Any]:
        """
        HTTP接口：发送通知
        POST /api/xiuxian/notifications/send
        请求体:
        {
            "title": "通知标题",
            "content": "通知内容",
            "target_type": "all|specific|realm",
            "target_ids": ["user1", "user2"],
            "sender_id": "system"
        }
        """
        try:
            data = await request.get_json()

            title = data.get("title")
            content = data.get("content")
            if not title or not content:
                return jsonify({"code": -1, "message": "title和content为必填字段"}), 400

            target_type = data.get("target_type", "all")
            target_ids = data.get("target_ids")
            sender_id = data.get("sender_id", "system")

            result = await self.send_notification(
                title=title,
                content=content,
                target_type=target_type,
                target_ids=target_ids,
                sender_id=sender_id,
            )

            if not result.get("success", False):
                return jsonify({"code": -1, "message": result.get("error", "发送失败")}), 400

            return jsonify({"code": 0, "data": result})

        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 500

    async def handle_get_history(self, **kwargs) -> Dict[str, Any]:
        """HTTP接口：获取通知历史 GET /api/xiuxian/notifications/history"""
        try:
            page = int(request.args.get("page", 1))
            page_size = int(request.args.get("page_size", 20))

            result = await self.get_notification_history(page=page, page_size=page_size)
            return jsonify({"code": 0, "data": result})

        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 500

    async def handle_get_detail(self, notification_id=None, **kwargs) -> Dict[str, Any]:
        """HTTP接口：获取通知详情 GET /api/xiuxian/notifications/{notification_id}"""
        try:
            if notification_id is None:
                return jsonify({"code": -1, "message": "缺少notification_id"}), 400

            notification_id = int(notification_id)
            result = await self.get_notification_detail(notification_id)

            if not result.get("success", False):
                return jsonify({"code": -1, "message": result.get("error", "通知不存在")}), 404

            return jsonify({"code": 0, "data": result["data"]})

        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 500

    async def handle_delete_notification(self, notification_id=None, **kwargs) -> Dict[str, Any]:
        """HTTP接口：删除通知 DELETE /api/xiuxian/notifications/{notification_id}"""
        try:
            if notification_id is None:
                return jsonify({"code": -1, "message": "缺少notification_id"}), 400

            notification_id = int(notification_id)
            result = await self.delete_notification(notification_id)

            if not result.get("success", False):
                return jsonify({"code": -1, "message": result.get("error", "删除失败")}), 400

            return jsonify({"code": 0, "data": result})

        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 500

    async def handle_get_sessions(self, **kwargs) -> Dict[str, Any]:
        """HTTP接口：获取所有玩家会话 GET /api/xiuxian/notifications/sessions"""
        try:
            sessions = await self.notification_service.get_all_sessions()
            return jsonify({"code": 0, "data": sessions})
        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 500

    async def handle_send_by_template(self, **kwargs) -> Dict[str, Any]:
        """
        HTTP接口：使用模板发送通知
        POST /api/xiuxian/notifications/send-template
        请求体:
        {
            "template_id": "system_maintenance",
            "variables": {"time": "今晚8点", "duration": "2小时"},
            "target_type": "all",
            "target_ids": [],
            "sender_id": "system"
        }
        """
        try:
            data = await request.get_json()

            template_id = data.get("template_id")
            variables = data.get("variables", {})
            if not template_id:
                return jsonify({"code": -1, "message": "template_id为必填字段"}), 400

            target_type = data.get("target_type", "all")
            target_ids = data.get("target_ids")
            sender_id = data.get("sender_id", "system")

            result = await self.send_notification_by_template(
                template_id=template_id,
                variables=variables,
                target_type=target_type,
                target_ids=target_ids,
                sender_id=sender_id,
            )

            if not result.get("success", False):
                return jsonify({"code": -1, "message": result.get("error", "发送失败")}), 400

            return jsonify({"code": 0, "data": result})

        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 500

    async def handle_get_templates(self, **kwargs) -> Dict[str, Any]:
        """HTTP接口：获取所有通知模板 GET /api/xiuxian/notifications/templates"""
        try:
            result = await self.get_templates()
            return jsonify({"code": 0, "data": result["data"]})
        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 500

    # ==================== 定时通知HTTP接口 ====================

    async def handle_create_scheduled(self, **kwargs) -> Dict[str, Any]:
        """
        HTTP接口：创建定时通知
        POST /api/xiuxian/notifications/scheduled
        请求体:
        {
            "title": "每日提醒",
            "content": "记得修炼",
            "cron_expression": "0 8 * * *",
            "target_type": "all",
            "target_ids": [],
            "template_id": null,
            "template_variables": {},
            "created_by": "system"
        }
        """
        try:
            data = await request.get_json()

            result = await self.create_scheduled_notification(
                title=data.get("title", ""),
                content=data.get("content", ""),
                cron_expression=data.get("cron_expression", ""),
                target_type=data.get("target_type", "all"),
                target_ids=data.get("target_ids"),
                template_id=data.get("template_id"),
                template_variables=data.get("template_variables"),
                created_by=data.get("created_by", "system"),
            )

            if not result.get("success", False):
                return jsonify({"code": -1, "message": result.get("error", "创建失败")}), 400

            return jsonify({"code": 0, "data": result["data"]})

        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 500

    async def handle_get_scheduled(self, **kwargs) -> Dict[str, Any]:
        """HTTP接口：获取定时通知列表 GET /api/xiuxian/notifications/scheduled"""
        try:
            page = int(request.args.get("page", 1))
            page_size = int(request.args.get("page_size", 20))

            result = await self.get_scheduled_notifications(page=page, page_size=page_size)
            return jsonify({"code": 0, "data": result["data"]})

        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 500

    async def handle_toggle_scheduled(self, schedule_id=None, **kwargs) -> Dict[str, Any]:
        """
        HTTP接口：启用/禁用定时通知
        PUT /api/xiuxian/notifications/scheduled/{schedule_id}/toggle
        请求体: {"enabled": true}
        """
        try:
            if schedule_id is None:
                return jsonify({"code": -1, "message": "缺少schedule_id"}), 400

            data = await request.get_json()
            enabled = data.get("enabled", True)

            result = await self.toggle_scheduled_notification(int(schedule_id), enabled)

            if not result.get("success", False):
                return jsonify({"code": -1, "message": result.get("error", "操作失败")}), 400

            return jsonify({"code": 0, "data": result})

        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 500

    async def handle_delete_scheduled(self, schedule_id=None, **kwargs) -> Dict[str, Any]:
        """HTTP接口：删除定时通知 DELETE /api/xiuxian/notifications/scheduled/{schedule_id}"""
        try:
            if schedule_id is None:
                return jsonify({"code": -1, "message": "缺少schedule_id"}), 400

            result = await self.delete_scheduled_notification(int(schedule_id))

            if not result.get("success", False):
                return jsonify({"code": -1, "message": result.get("error", "删除失败")}), 400

            return jsonify({"code": 0, "data": result})

        except Exception as e:
            return jsonify({"code": -1, "message": str(e)}), 500
