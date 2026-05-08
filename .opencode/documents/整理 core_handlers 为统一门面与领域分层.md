## 目标
- 将 `core/handlers` 也整理成“门面 + 领域分层”的架构：外部只与一个统一门面交互，内部按玩家/背包/物品/任务/社交等领域细分；所有处理逻辑只调用 `api.game`，不直接访问数据库。

## 现状观察
- 已有领域文件：`basic_handlers.py`、`player_handlers.py`、`inventory_handlers.py`、`item_handlers.py`、`task_handlers.py`、`social_handlers.py`。
- 存在重复与越界：部分处理器直接查库或与其他领域逻辑重复，已在上轮把部分调用改为 `api.game`。

## 拟定新结构
- `core/handlers/gateway.py`（门面统一入口）
  - 职责：统一初始化与聚合所有领域处理器；提供统一的 `route_command(event)` 或按功能暴露方法；内部固定依赖 `api.game`。
  - 内容：
    - `class HandlersGateway`: 构造注入 `db_path`、`config`；聚合属性：`player`、`inventory`、`items`、`tasks`、`social`。
    - 命令路由表：`COMMAND_MAP = {"我的信息": player.profile_info, "灵根检测": player.spiritual_root_info, "背包": inventory.list_inventory, "使用": items.use_item, ...}`；支持扩展、后台可配置（占位：从 `system_config` 读取路由覆盖）。
    - 统一工具方法：参数解析、错误兜底、统一文案输出（修真语境）。
- 领域处理器文件保留但约束职责
  - `player_handlers.py`: 档案、灵根信息、境界突破、改道号等（全部调用 `api.game`）。
  - `inventory_handlers.py`: 背包列表、分页列表（调用 `api.game.get_user_inventory`）。
  - `item_handlers.py`: 使用、购买（调用 `api.game.use_item`、`api.game.buy_item`）。
  - `task_handlers.py`: 任务查询与接取（预留，统一用 `api.game` 相关API或新增 `api.tasks` 后再接入）。
  - `social_handlers.py`: 社交类展示与交互（仅适配层）。
  - 移除所有直接 SQL；公共校验一律走 `api.game`（如 `has_spiritual_root`）。
- 统一导出
  - `core/handlers/__init__.py` 只导出 `HandlersGateway`，避免平铺多处理器实例。

## 与主服务衔接
- 在 `core/plugin_service.py` 中：
  - 用 `HandlersGateway(self.db_path, self.config)` 代替分散的 `BasicHandlers/PlayerHandlers/...` 多实例字段。
  - 注册与分发命令时，统一从 `gateway.COMMAND_MAP` 或 `gateway`暴露的方法调用；减少主服务类的路由散落。

## 迁移细节（不留兼容）
- 移除处理器中的直接 `aiosqlite` 查询，统一改为 `api.game`。
- 将 `basic_handlers` 中与玩家/背包重叠的逻辑分别迁移到 `player_handlers` / `inventory_handlers`，`basic_handlers` 可以并入 `gateway` 或仅保留基础工具。
- 更新所有引用：将 `api.items.*`、`api.inventory.*` 的直接调用改为 `api.game.*`。
- `__all__` 更新：仅导出 `HandlersGateway`。

## 注释与规范
- 顶部 import 统一放置；所有方法中文注释（用途、参数、返回）；方法内部模块化分段也加中文注释。
- 提示语符合修真语境，关键信息用【】标注；不硬编码，路由表支持后台配置覆盖（从 `system_config.command_routes` 读取，若存在）。

## 验证步骤
- 初始化：`api.init_api(DB_PATH)`；实例化 `HandlersGateway`。
- 命令测试：
  - “灵根检测”→ `gateway.player.spiritual_root_info` 或路由触发 `api.game.detect_spiritual_root`
  - “我的信息”→ `gateway.player.profile_info`
  - “背包”/“背包 第2页”→ `gateway.inventory.list_inventory(…)`
  - “使用 清灵草种子 1”→ `gateway.items.use_item(…)`
- 确认所有处理器均不直接查库；日志无 ImportError 或兼容残留。

## 改动文件清单（实施时）
- 新增：`core/handlers/gateway.py`
- 更新：`core/handlers/__init__.py`（只导出门面）；`basic_handlers.py`（逻辑迁出或保留工具）；`player_handlers.py`、`inventory_handlers.py`、`item_handlers.py`（去除直接 SQL 与统一依赖 `api.game`）；`core/plugin_service.py`（使用门面）。

请确认，我将按该方案重构 handlers 并同步路由到门面，保证对外只需使用统一入口，内部领域职责清晰。