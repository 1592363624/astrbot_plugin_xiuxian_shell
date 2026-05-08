## 目标
- 将 `core/api/game.py` 重构为统一门面（Facade），对外只导入 `api.game` 即可，内部按领域委托到 `api.player`、`api.inventory`、`api.items`、`api.chat`。
- 完全移除旧的兼容导出，所有调用迁移到 `api.game.*`。
- 保持顶层 import 规范与中文注释；不改数据库表结构；不硬编码，配置由后台管理读取。

## 门面设计（game 统一入口）
- `game.init_api(db_path)`：顺序初始化 `player`、`inventory`、`items`、`chat`。
- `game` 提供统一接口并纯委托，不写 SQL：
  - 玩家领域：`has_spiritual_root`、`detect_spiritual_root`、`get_user_profile`、`set_dao_name`、`add_xp`、`add_gold`、`add_stability`、`check_and_update_realm`、`get_spiritual_root_effects`、`get_spiritual_roots_catalog`、`get_spiritual_roots_weights`、`purge_user_data` → 委托 `player`
  - 背包领域：`get_user_inventory`、`give_item`、`adjust_value(target="item")` → 委托 `inventory`
  - 物品领域：`use_item`、`buy_item` → 委托 `items`
  - 命令策略：如后续需要，保留在 `player` 或新建 `policy` 模块，`game` 仅转发
- `game.adjust_value(user_id, target, delta, **kwargs)` 改为编排型：
  - `xp`→`player.add_xp`；`gold`→`player.add_gold`；`stability`→`player.add_stability`；`item`→`inventory.adjust_item_quantity`

## 分类模块调整
- `api.player`：承载现有 `game` 中的玩家档案/灵根/修为/境界/删除档案等全部逻辑与 SQL；保持灵根系数与修为增益联动。
- `api.inventory`：
  - 封装 `get_user_inventory`（委托 `items` 的查询实现，领域归类）。
  - 新增 `adjust_item_quantity(user_id, item_id, delta)`：统一正负增减、0 清理；供 `game.adjust_value` 和 `items.use_item/buy_item` 调用。
  - 保留 `give_item(user_id, item_name, count)`（迁移自原 `game.give_item`）。
- `api.items`：
  - 移除对 `game.adjust_value` 的直接依赖；改为调用 `inventory.adjust_item_quantity` 与 `player.add_gold`。
  - `use_item`：扣背包→执行效果（保持原注册的效果执行流程）。
  - `buy_item`：读取商店配置→扣灵石（`player.add_gold`，负数）→加物品（`inventory.adjust_item_quantity`）。
- `api.chat`：保持现状。

## 导出聚合
- 更新 `core/api/__init__.py`：
  - 仅导出 `init_api` 与 `game`（内部仍保留分类模块导入用于初始化），移除旧的函数平铺导出。
  - 说明注释：对外统一入口为 `api.game`。

## Handlers 迁移
- 统一改为只使用 `api.game`：
  - `basic_handlers`：`has_spiritual_root`、`get_user_inventory`、`handle_linggen_detect` 内部触发检测使用 `game.detect_spiritual_root`。
  - `inventory_handlers`：`list_inventory`、`list_inventory_page` 使用 `game.get_user_inventory`。
  - `item_handlers`：`use_item`、`trade_item`、`craft_item` 占位不改逻辑，但实际执行改为 `game.use_item`、`game.buy_item`。
  - `player_handlers`：`profile_info`、`spiritual_root_info` 使用 `game.get_user_profile`。
- 移除所有 `api.items` 与直接 SQL 调用的引用（改为 `api.game`）。

## 兼容移除
- 删除 `core/api/__init__.py` 中的旧式平铺导出（如 `give_item`, `add_xp` 等），统一通过 `api.game` 访问。
- 移除 `items.py` 中 `from .game import adjust_value` 旧调用，改为 `from .inventory import adjust_item_quantity` 与 `from .player import add_gold`。

## 注释与风格
- 顶部 import 统一；方法中文注释（用途、参数、返回）；方法内部小模块加中文注释。
- 返回信息遵循修真语境提示格式；关键信息加【】。

## 验证步骤
- 初始化：`api.init_api(DB_PATH)`。
- 灵根检测：`await api.game.detect_spiritual_root(user_id)` → 绑定灵根、道号为昵称。
- 修为增益：`await api.game.add_xp(user_id, 100)` → `users.xp` 增长≈`100 * xp_gain_mult`。
- 背包查询：`await api.game.get_user_inventory(user_id, 1, 20)` → 返回列表。
- 物品使用：`await api.game.use_item(user_id, item_id, 1)` → 扣库存并执行效果。
- 购买物品：`await api.game.buy_item(user_id, shop_id, item_id, 2)` → 扣灵石并加物品。
- 删除数据：`await api.game.purge_user_data(user_id)` → 返回删除计数。

## 改动文件清单（示意）
- 重构：`core/api/game.py`（门面化、纯委托、移除 SQL）
- 新增/完善：`core/api/player.py`、`core/api/inventory.py`（已存在基础，补充 `adjust_item_quantity` 与缺口）
- 调整：`core/api/items.py`（依赖迁移）、`core/api/__init__.py`（导出与初始化）、`core/handlers/*.py`（统一改为 `api.game`）

请确认以上方案，我将按此实施重构与迁移，并完成代码、注释与验证。