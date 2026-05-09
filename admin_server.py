"""
独立后台管理HTTP服务器
提供不经过AstrBot认证中间件的后台管理页面和API访问
"""

import secrets
from pathlib import Path
from typing import Any

from aiohttp import web

from astrbot.api import logger


class AdminServer:
    """独立后台管理HTTP服务器"""

    def __init__(
        self,
        admin_api: Any,
        checkin_api: Any,
        notification_api: Any,
        host: str = "0.0.0.0",
        port: int = 0,
        password: str = "",
    ):
        """
        初始化独立管理服务器

        Args:
            admin_api: 后台管理API实例
            checkin_api: 签到API实例
            notification_api: 通知API实例
            host: 监听地址
            port: 监听端口，0表示自动分配
            password: 管理后台密码
        """
        self.admin_api = admin_api
        self.checkin_api = checkin_api
        self.notification_api = notification_api
        self.host = host
        self.port = port
        self.password = password or "xiuxian_admin"
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._sessions: dict[str, bool] = {}
        self._session_secret = secrets.token_hex(32)

    async def start(self) -> int:
        """
        启动独立管理服务器

        Returns:
            实际监听的端口号
        """
        self._app = web.Application()
        self._setup_routes()

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, self.host, self.port)
        await self._site.start()

        # 获取实际分配的端口
        if self.port == 0:
            self.port = self._site._server.sockets[0].getsockname()[1]

        logger.info(f"修仙后台管理服务器已启动: http://{self.host}:{self.port}")
        return self.port

    async def stop(self):
        """停止独立管理服务器"""
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        logger.info("修仙后台管理服务器已停止")

    def _setup_routes(self):
        """设置路由"""
        self._app.router.add_get("/", self._handle_index)
        self._app.router.add_get("/api/xiuxian/stats", self._handle_stats)
        # 玩家管理
        self._app.router.add_get("/api/xiuxian/players", self._handle_players)
        self._app.router.add_get(
            "/api/xiuxian/players/{player_id}", self._handle_player_detail
        )
        self._app.router.add_post(
            "/api/xiuxian/players/{player_id}", self._handle_update_player
        )
        self._app.router.add_post(
            "/api/xiuxian/players/{player_id}/delete", self._handle_delete_player
        )
        self._app.router.add_post(
            "/api/xiuxian/players/{player_id}/reset", self._handle_reset_player
        )
        self._app.router.add_post(
            "/api/xiuxian/players/{player_id}/ban", self._handle_ban_player
        )
        self._app.router.add_post(
            "/api/xiuxian/players/{player_id}/unban", self._handle_unban_player
        )
        # 物品管理
        self._app.router.add_get("/api/xiuxian/items", self._handle_items)
        self._app.router.add_post("/api/xiuxian/items", self._handle_create_item)
        self._app.router.add_post(
            "/api/xiuxian/items/{item_id}", self._handle_update_item
        )
        self._app.router.add_post(
            "/api/xiuxian/items/{item_id}/delete", self._handle_delete_item
        )
        # 功法管理
        self._app.router.add_get("/api/xiuxian/skills", self._handle_skills)
        self._app.router.add_post("/api/xiuxian/skills", self._handle_create_skill)
        self._app.router.add_post(
            "/api/xiuxian/skills/{skill_id}", self._handle_update_skill
        )
        self._app.router.add_post(
            "/api/xiuxian/skills/{skill_id}/delete", self._handle_delete_skill
        )
        # 境界管理
        self._app.router.add_get("/api/xiuxian/realms", self._handle_realms)
        self._app.router.add_post("/api/xiuxian/realms", self._handle_create_realm)
        self._app.router.add_post(
            "/api/xiuxian/realms/{realm_id}", self._handle_update_realm
        )
        self._app.router.add_post(
            "/api/xiuxian/realms/{realm_id}/delete", self._handle_delete_realm
        )
        # 事件管理
        self._app.router.add_get("/api/xiuxian/events", self._handle_events)
        self._app.router.add_post("/api/xiuxian/events", self._handle_create_event)
        self._app.router.add_post(
            "/api/xiuxian/events/{event_id}", self._handle_update_event
        )
        self._app.router.add_post(
            "/api/xiuxian/events/{event_id}/delete", self._handle_delete_event
        )
        # 配置管理
        self._app.router.add_get("/api/xiuxian/config", self._handle_get_config)
        self._app.router.add_post("/api/xiuxian/config", self._handle_update_config)
        # 闭关修炼
        self._app.router.add_get(
            "/api/xiuxian/seclusion/{player_id}/status", self._handle_seclusion_status
        )
        self._app.router.add_get(
            "/api/xiuxian/seclusion/{player_id}/records", self._handle_seclusion_records
        )
        # 丹毒管理
        self._app.router.add_get(
            "/api/xiuxian/pill/{player_id}/toxicity", self._handle_toxicity_status
        )
        # 签到管理
        self._app.router.add_get(
            "/api/xiuxian/checkin/records", self._handle_checkin_records
        )
        self._app.router.add_get(
            "/api/xiuxian/checkin/ranking", self._handle_checkin_ranking
        )
        self._app.router.add_get(
            "/api/xiuxian/checkin/{player_id}/status", self._handle_checkin_status
        )
        self._app.router.add_get(
            "/api/xiuxian/checkin/{player_id}/records",
            self._handle_checkin_player_records,
        )
        # 通知管理
        self._app.router.add_post(
            "/api/xiuxian/notifications/send", self._handle_notification_send
        )
        self._app.router.add_get(
            "/api/xiuxian/notifications/history", self._handle_notification_history
        )
        self._app.router.add_get(
            "/api/xiuxian/notifications/{notification_id}",
            self._handle_notification_detail,
        )
        self._app.router.add_post(
            "/api/xiuxian/notifications/{notification_id}/delete",
            self._handle_notification_delete,
        )
        self._app.router.add_get(
            "/api/xiuxian/notifications/sessions", self._handle_notification_sessions
        )
        self._app.router.add_post(
            "/api/xiuxian/notifications/send-template",
            self._handle_notification_send_template,
        )
        self._app.router.add_get(
            "/api/xiuxian/notifications/templates", self._handle_notification_templates
        )
        self._app.router.add_post(
            "/api/xiuxian/notifications/scheduled",
            self._handle_notification_create_scheduled,
        )
        self._app.router.add_get(
            "/api/xiuxian/notifications/scheduled",
            self._handle_notification_get_scheduled,
        )
        self._app.router.add_post(
            "/api/xiuxian/notifications/scheduled/{schedule_id}/toggle",
            self._handle_notification_toggle_scheduled,
        )
        self._app.router.add_post(
            "/api/xiuxian/notifications/scheduled/{schedule_id}/delete",
            self._handle_notification_delete_scheduled,
        )
        # 发言日志管理
        self._app.router.add_get("/api/xiuxian/chat-logs", self._handle_chat_logs)
        # 突破条件管理
        self._app.router.add_get(
            "/api/xiuxian/breakthrough-conditions",
            self._handle_breakthrough_conditions_list,
        )
        self._app.router.add_get(
            "/api/xiuxian/breakthrough-conditions/{condition_id}",
            self._handle_breakthrough_condition_detail,
        )
        self._app.router.add_put(
            "/api/xiuxian/breakthrough-conditions/{condition_id}",
            self._handle_breakthrough_condition_update,
        )
        # 认证
        self._app.router.add_post("/api/xiuxian/auth/login", self._handle_login)
        self._app.router.add_post("/api/xiuxian/auth/logout", self._handle_logout)
        self._app.router.add_post(
            "/api/xiuxian/auth/change-password", self._handle_change_password
        )

    def _check_auth(self, request: web.Request) -> bool:
        """检查请求是否已认证"""
        session_cookie = request.cookies.get("xiuxian_session")
        if session_cookie and session_cookie in self._sessions:
            logger.debug(f"Auth via cookie: {session_cookie[:8]}...")
            return True
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if token in self._sessions:
                logger.debug(f"Auth via Bearer token: {token[:8]}...")
                return True
            else:
                logger.warning(f"Invalid token: {token[:8]}...")
        return False

    def _json_response(self, data: dict[str, Any], status: int = 200) -> web.Response:
        """返回JSON响应"""
        return web.json_response(data, status=status)

    def _ok(self, data: Any = None) -> web.Response:
        """返回成功响应"""
        return self._json_response({"code": 0, "data": self._serialize(data)})

    def _serialize(self, obj: Any) -> Any:
        """序列化对象，将模型对象转换为字典"""
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if isinstance(obj, list):
            return [self._serialize(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}
        return obj

    def _error(self, message: str, code: int = -1) -> web.Response:
        """返回错误响应"""
        return self._json_response({"code": code, "message": message})

    def _require_auth(self, request: web.Request) -> web.Response | None:
        """检查认证，未认证返回错误响应"""
        if not self._check_auth(request):
            return self._error("未登录或登录已过期", 401)
        return None

    async def _handle_index(self, request: web.Request) -> web.Response:
        """返回管理页面HTML"""
        html_path = Path(__file__).parent / "pages" / "admin" / "index.html"
        if not html_path.exists():
            return web.Response(text="页面文件未找到", status=404)
        html_content = html_path.read_text(encoding="utf-8")
        return web.Response(
            text=html_content,
            status=200,
            headers={"Content-Type": "text/html; charset=utf-8"},
        )

    async def _handle_login(self, request: web.Request) -> web.Response:
        """处理登录请求"""
        try:
            data = await request.json()
        except Exception:
            return self._error("请求格式错误")

        username = data.get("username", "")
        password = data.get("password", "")

        if not username or not password:
            return self._error("用户名和密码不能为空")

        # 简单密码验证
        if password != self.password:
            return self._error("密码错误")

        # 生成session
        session_id = secrets.token_hex(32)
        self._sessions[session_id] = True

        # 返回token，前端通过Authorization header传递
        return self._ok({"token": session_id, "username": username})

    async def _handle_logout(self, request: web.Request) -> web.Response:
        """处理登出请求"""
        session_cookie = request.cookies.get("xiuxian_session")
        if session_cookie and session_cookie in self._sessions:
            del self._sessions[session_cookie]
        return self._ok()

    async def _handle_change_password(self, request: web.Request) -> web.Response:
        """修改管理员密码"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        try:
            data = await request.json()
        except Exception:
            return self._error("请求格式错误")
        old_password = data.get("old_password", "")
        new_password = data.get("new_password", "")
        if not old_password or not new_password:
            return self._error("原密码和新密码不能为空")
        if old_password != self.password:
            return self._error("原密码错误")
        if len(new_password) < 6:
            return self._error("新密码长度不能少于6位")
        self.password = new_password
        # 更新配置中的密码
        self.admin_api.config_manager.update({"admin_password": new_password})
        # 使所有现有会话失效，强制重新登录
        self._sessions.clear()
        logger.info("密码已修改，所有会话已清除")
        return self._ok({"message": "密码修改成功，请使用新密码重新登录"})

    async def _handle_stats(self, request: web.Request) -> web.Response:
        """获取游戏统计"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error

        player_count = await self.admin_api.player_service.db.fetch_one(
            "SELECT COUNT(*) as count FROM players"
        )
        total_stones = await self.admin_api.player_service.db.fetch_one(
            "SELECT SUM(spirit_stone) as total FROM players"
        )

        players = await self.admin_api.player_service.get_all_players(page=1, page_size=10000)
        realm_stats = {}
        realms_cache = {r.level: r.name for r in await self.admin_api.cultivation_service.get_all_realms()}

        for player_data in players.get("players", []):
            realm_level = player_data.get("realm_level", 1)
            realm_name = realms_cache.get(realm_level, "未知")
            realm_stats[realm_name] = realm_stats.get(realm_name, 0) + 1

        realm_distribution = [{"name": name, "count": count} for name, count in realm_stats.items()]

        return self._ok(
            {
                "player_count": player_count["count"] if player_count else 0,
                "realm_distribution": realm_distribution,
                "total_spirit_stones": total_stones["total"] if total_stones else 0,
            }
        )

    async def _handle_players(self, request: web.Request) -> web.Response:
        """获取玩家列表"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        page = int(request.query.get("page", 1))
        page_size = int(request.query.get("page_size", 20))
        result = await self.admin_api.player_service.get_all_players(page, page_size)
        return self._ok(result)

    async def _handle_player_detail(self, request: web.Request) -> web.Response:
        """获取玩家详情"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        player_id = request.match_info["player_id"]
        player = await self.admin_api.player_service.get_player_by_id(player_id)
        return self._ok(player.to_dict() if player else None)

    async def _handle_update_player(self, request: web.Request) -> web.Response:
        """更新玩家信息"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        player_id = request.match_info["player_id"]
        try:
            data = await request.json()
        except Exception:
            return self._error("请求格式错误")
        result = await self.admin_api.player_service.update_player(player_id, **data)
        return self._ok(result)

    async def _handle_delete_player(self, request: web.Request) -> web.Response:
        """删除玩家"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        player_id = request.match_info["player_id"]
        result = await self.admin_api.delete_player(player_id)
        return self._ok(result)

    async def _handle_reset_player(self, request: web.Request) -> web.Response:
        """重置玩家数据"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        player_id = request.match_info["player_id"]
        result = await self.admin_api.reset_player(player_id)
        return self._ok(result)

    async def _handle_ban_player(self, request: web.Request) -> web.Response:
        """封禁玩家"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        player_id = request.match_info["player_id"]
        result = await self.admin_api.ban_player(player_id)
        return self._ok(result)

    async def _handle_unban_player(self, request: web.Request) -> web.Response:
        """解封玩家"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        player_id = request.match_info["player_id"]
        result = await self.admin_api.unban_player(player_id)
        return self._ok(result)

    async def _handle_items(self, request: web.Request) -> web.Response:
        """获取物品列表"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        result = await self.admin_api.inventory_service.get_all_items()
        return self._ok(result)

    async def _handle_create_item(self, request: web.Request) -> web.Response:
        """创建物品"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        try:
            data = await request.json()
        except Exception:
            return self._error("请求格式错误")
        result = await self.admin_api.inventory_service.create_item(data)
        return self._ok(result)

    async def _handle_update_item(self, request: web.Request) -> web.Response:
        """更新物品"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        item_id = request.match_info["item_id"]
        try:
            data = await request.json()
        except Exception:
            return self._error("请求格式错误")
        result = await self.admin_api.inventory_service.update_item(item_id, **data)
        return self._ok(result)

    async def _handle_delete_item(self, request: web.Request) -> web.Response:
        """删除物品"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        item_id = request.match_info["item_id"]
        result = await self.admin_api.inventory_service.delete_item(item_id)
        return self._ok(result)

    async def _handle_skills(self, request: web.Request) -> web.Response:
        """获取功法列表"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        result = await self.admin_api.cultivation_service.get_all_skills()
        return self._ok(result)

    async def _handle_create_skill(self, request: web.Request) -> web.Response:
        """创建功法"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        try:
            data = await request.json()
        except Exception:
            return self._error("请求格式错误")
        result = await self.admin_api.cultivation_service.create_skill(data)
        return self._ok(result)

    async def _handle_update_skill(self, request: web.Request) -> web.Response:
        """更新功法"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        skill_id = request.match_info["skill_id"]
        try:
            data = await request.json()
        except Exception:
            return self._error("请求格式错误")
        result = await self.admin_api.cultivation_service.update_skill(skill_id, **data)
        return self._ok(result)

    async def _handle_delete_skill(self, request: web.Request) -> web.Response:
        """删除功法"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        skill_id = request.match_info["skill_id"]
        result = await self.admin_api.cultivation_service.delete_skill(skill_id)
        return self._ok(result)

    async def _handle_realms(self, request: web.Request) -> web.Response:
        """获取境界列表"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        result = await self.admin_api.cultivation_service.get_all_realms()
        return self._ok(result)

    async def _handle_create_realm(self, request: web.Request) -> web.Response:
        """创建境界"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        try:
            data = await request.json()
        except Exception:
            return self._error("请求格式错误")
        result = await self.admin_api.cultivation_service.create_realm(data)
        return self._ok(result)

    async def _handle_update_realm(self, request: web.Request) -> web.Response:
        """更新境界"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        realm_id = request.match_info["realm_id"]
        try:
            data = await request.json()
        except Exception:
            return self._error("请求格式错误")
        result = await self.admin_api.cultivation_service.update_realm(realm_id, **data)
        return self._ok(result)

    async def _handle_delete_realm(self, request: web.Request) -> web.Response:
        """删除境界"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        realm_id = request.match_info["realm_id"]
        result = await self.admin_api.cultivation_service.delete_realm(realm_id)
        return self._ok(result)

    async def _handle_events(self, request: web.Request) -> web.Response:
        """获取事件列表"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        result = await self.admin_api.event_service.get_all_events()
        return self._ok(result)

    async def _handle_create_event(self, request: web.Request) -> web.Response:
        """创建事件"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        try:
            data = await request.json()
        except Exception:
            return self._error("请求格式错误")
        result = await self.admin_api.event_service.create_event(data)
        return self._ok(result)

    async def _handle_update_event(self, request: web.Request) -> web.Response:
        """更新事件"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        event_id = request.match_info["event_id"]
        try:
            data = await request.json()
        except Exception:
            return self._error("请求格式错误")
        result = await self.admin_api.event_service.update_event(event_id, **data)
        return self._ok(result)

    async def _handle_delete_event(self, request: web.Request) -> web.Response:
        """删除事件"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        event_id = request.match_info["event_id"]
        result = await self.admin_api.event_service.delete_event(event_id)
        return self._ok(result)

    async def _handle_get_config(self, request: web.Request) -> web.Response:
        """获取配置"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        result = self.admin_api.config_manager.get_all()
        return self._ok(result)

    async def _handle_update_config(self, request: web.Request) -> web.Response:
        """更新配置"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        try:
            data = await request.json()
        except Exception:
            return self._error("请求格式错误")
        self.admin_api.config_manager.update(data)
        return self._ok()

    # ==================== 闭关修炼 ====================

    async def _handle_seclusion_status(self, request: web.Request) -> web.Response:
        """获取玩家闭关状态"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        player_id = request.match_info["player_id"]
        status = await self.admin_api.cultivation_service.get_seclusion_status(
            player_id
        )
        return self._ok(status)

    async def _handle_seclusion_records(self, request: web.Request) -> web.Response:
        """获取玩家闭关记录"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        player_id = request.match_info["player_id"]
        limit = int(request.query.get("limit", 10))
        records = await self.admin_api.cultivation_service.get_seclusion_records(
            player_id, limit
        )
        return self._ok(records)

    # ==================== 丹毒管理 ====================

    async def _handle_toxicity_status(self, request: web.Request) -> web.Response:
        """获取玩家丹毒状态"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        player_id = request.match_info["player_id"]
        status = await self.admin_api.inventory_service.get_toxicity_status(player_id)
        return self._ok(status)

    # ==================== 签到管理 ====================

    async def _handle_checkin_records(self, request: web.Request) -> web.Response:
        """获取所有签到记录"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        page = int(request.query.get("page", 1))
        page_size = int(request.query.get("page_size", 20))
        result = await self.checkin_api.checkin_service.get_all_checkin_records(
            page, page_size
        )
        return self._ok(result)

    async def _handle_checkin_ranking(self, request: web.Request) -> web.Response:
        """获取签到排行"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        limit = int(request.query.get("limit", 10))
        result = await self.checkin_api.checkin_service.get_checkin_ranking(limit)
        return self._ok(result)

    async def _handle_checkin_status(self, request: web.Request) -> web.Response:
        """获取玩家签到状态"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        player_id = request.match_info["player_id"]
        status = await self.checkin_api.checkin_service.get_checkin_status(player_id)
        return self._ok(status)

    async def _handle_checkin_player_records(
        self, request: web.Request
    ) -> web.Response:
        """获取玩家签到记录"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        player_id = request.match_info["player_id"]
        limit = int(request.query.get("limit", 30))
        records = await self.checkin_api.checkin_service.get_player_checkin_records(
            player_id, limit
        )
        return self._ok(records)

    # ==================== 通知管理 ====================

    async def _handle_notification_send(self, request: web.Request) -> web.Response:
        """发送通知"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        try:
            data = await request.json()
        except Exception:
            return self._error("请求格式错误")
        title = data.get("title")
        content = data.get("content")
        if not title or not content:
            return self._error("title和content为必填字段")
        result = await self.notification_api.send_notification(
            title=title,
            content=content,
            target_type=data.get("target_type", "all"),
            target_ids=data.get("target_ids"),
            sender_id=data.get("sender_id", "system"),
        )
        if not result.get("success", False):
            return self._error(result.get("error", "发送失败"))
        return self._ok(result)

    async def _handle_notification_history(self, request: web.Request) -> web.Response:
        """获取通知历史"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        page = int(request.query.get("page", 1))
        page_size = int(request.query.get("page_size", 20))
        result = await self.notification_api.get_notification_history(
            page=page, page_size=page_size
        )
        return self._ok(result)

    async def _handle_notification_detail(self, request: web.Request) -> web.Response:
        """获取通知详情"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        try:
            notification_id = int(request.match_info["notification_id"])
        except ValueError:
            return self._error("notification_id必须为数字")
        result = await self.notification_api.get_notification_detail(notification_id)
        if not result.get("success", False):
            return self._error(result.get("error", "通知不存在"), 404)
        return self._ok(result.get("data"))

    async def _handle_notification_delete(self, request: web.Request) -> web.Response:
        """删除通知"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        try:
            notification_id = int(request.match_info["notification_id"])
        except ValueError:
            return self._error("notification_id必须为数字")
        result = await self.notification_api.delete_notification(notification_id)
        if not result.get("success", False):
            return self._error(result.get("error", "删除失败"))
        return self._ok(result)

    async def _handle_notification_sessions(self, request: web.Request) -> web.Response:
        """获取所有玩家会话信息"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        result = await self.notification_api.get_all_player_sessions()
        return self._ok(result)

    async def _handle_notification_send_template(
        self, request: web.Request
    ) -> web.Response:
        """使用模板发送通知"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        try:
            data = await request.json()
        except Exception:
            return self._error("请求格式错误")
        template_id = data.get("template_id")
        target_type = data.get("target_type", "all")
        target_ids = data.get("target_ids")
        variables = data.get("variables", {})
        if not template_id:
            return self._error("template_id为必填字段")
        result = await self.notification_api.send_notification_by_template(
            template_id=template_id,
            target_type=target_type,
            target_ids=target_ids,
            variables=variables,
        )
        if not result.get("success", False):
            return self._error(result.get("error", "发送失败"))
        return self._ok(result)

    async def _handle_notification_templates(
        self, request: web.Request
    ) -> web.Response:
        """获取所有通知模板"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        result = await self.notification_api.get_notification_templates()
        return self._ok(result)

    async def _handle_notification_create_scheduled(
        self, request: web.Request
    ) -> web.Response:
        """创建定时通知"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        try:
            data = await request.json()
        except Exception:
            return self._error("请求格式错误")
        title = data.get("title")
        content = data.get("content")
        cron_expression = data.get("cron_expression")
        if not title or not content or not cron_expression:
            return self._error("title、content和cron_expression为必填字段")
        result = await self.notification_api.create_scheduled_notification(
            title=title,
            content=content,
            cron_expression=cron_expression,
            created_by=data.get("created_by", "admin"),
        )
        if not result.get("success", False):
            return self._error(result.get("error", "创建失败"))
        return self._ok(result.get("data"))

    async def _handle_notification_get_scheduled(
        self, request: web.Request
    ) -> web.Response:
        """获取定时通知列表"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        result = await self.notification_api.get_scheduled_notifications()
        return self._ok(result)

    async def _handle_notification_toggle_scheduled(
        self, request: web.Request
    ) -> web.Response:
        """启用/禁用定时通知"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        try:
            schedule_id = int(request.match_info["schedule_id"])
        except ValueError:
            return self._error("schedule_id必须为数字")
        try:
            data = await request.json()
        except Exception:
            data = {}
        enabled = data.get("enabled", True)
        result = await self.notification_api.toggle_scheduled_notification(
            schedule_id, enabled
        )
        if not result.get("success", False):
            return self._error(result.get("error", "操作失败"))
        return self._ok(result)

    async def _handle_notification_delete_scheduled(
        self, request: web.Request
    ) -> web.Response:
        """删除定时通知"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        try:
            schedule_id = int(request.match_info["schedule_id"])
        except ValueError:
            return self._error("schedule_id必须为数字")
        result = await self.notification_api.delete_scheduled_notification(schedule_id)
        if not result.get("success", False):
            return self._error(result.get("error", "删除失败"))
        return self._ok(result)

    # ==================== 发言日志管理 ====================

    async def _handle_chat_logs(self, request: web.Request) -> web.Response:
        """获取发言日志列表"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        page = int(request.query.get("page", 1))
        page_size = int(request.query.get("page_size", 100))
        sort_field = request.query.get("sort_field", "created_at")
        sort_order = request.query.get("sort_order", "DESC")
        keyword = request.query.get("keyword", None)

        result = await self.admin_api.player_service.get_chat_logs(
            page=page,
            page_size=page_size,
            sort_field=sort_field,
            sort_order=sort_order,
            keyword=keyword,
        )
        return self._ok(result)

    # ==================== 突破条件管理 ====================

    async def _handle_breakthrough_conditions_list(
        self, request: web.Request
    ) -> web.Response:
        """获取突破条件列表"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        result = await self.admin_api.get_breakthrough_conditions()
        return web.json_response(result)

    async def _handle_breakthrough_condition_detail(
        self, request: web.Request
    ) -> web.Response:
        """获取单个突破条件详情"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        condition_id = request.match_info.get("condition_id")
        result = await self.admin_api.get_breakthrough_condition(condition_id)
        return web.json_response(result)

    async def _handle_breakthrough_condition_update(
        self, request: web.Request
    ) -> web.Response:
        """更新突破条件"""
        auth_error = self._require_auth(request)
        if auth_error:
            return auth_error
        condition_id = request.match_info.get("condition_id")
        result = await self.admin_api.update_breakthrough_condition(condition_id)
        return web.json_response(result)
