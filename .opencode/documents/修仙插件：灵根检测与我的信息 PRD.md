# 项目背景与目标
- 目标：在 `astrbot_plugin_re_xiuxian` 中实现可长期扩展的“灵根体系”与“我的信息”查询，首期落地功能为【检测灵根】与【我的信息】，并为后续所有玩法提供稳定的底层架构。
- 约束：遵循 AstrBot ≥ v4.5 插件规范；异步、事件驱动；不硬编码；数据均可在后台管理编辑；使用 SQLite（WAL + External Comments SQL）。

# 范畴与不做事项
- 本期仅提供架构与数据设计及交互流程，不含代码实现与具体数值设定。
- 不实现战斗、闭关等完整玩法逻辑，仅保留事件 Hook 位与属性来源接口。

# 术语定义
- 玩家（Player）：用户在游戏中的资料载体，仅保存数据结果，不含计算逻辑。
- 灵根（Root）：影响多系统的可插拔加成模板，包含倍率、属性、事件 Hook。
- 属性（Attribute）：可合成的玩家能力数值，来源于多个 Provider 的叠加。
- 行为（Action）：玩家触发的业务流程，如【检测灵根】、【我的信息】。
- 事件总线（EventBus）：公开 Hook 点，供灵根、宗门、装备、功法等挂接。

# 架构设计总览
- Player
  - 基础信息、境界、灵根 `root_id`、属性缓存/视图。
- RootSystem
  - 灵根模板表、加成计算、事件 Hooks。
- AttributeSystem
  - 多来源 Provider 汇总：基础、灵根、宗门、装备、功法、临时 Buff。
- ActionSystem
  - DetectRoot（检测灵根）、ViewProfile（我的信息）。
- EventBus
  - on_cultivation_gain, on_breakthrough_check, on_player_attack 等关键 Hook。
- 参考现有事件引擎：`core/event_system/engine.py:13-58`，命令触发器：`core/event_system/triggers/command_trigger.py:10-17`。

# 数据模型设计
- 新增表（建议字段，均可后台管理）：
  - `roots`：灵根模板
    - `id`，`name`，`rarity`，`description`，`base_additions`（JSON），`cultivation_multiplier`（REAL），`combat_multiplier`（REAL），`hooks`（JSON），`enabled`，`created_at`，`updated_at`。
  - `user_roots`：玩家的灵根绑定
    - `user_id`（FK `users.user_id`），`root_id`（FK `roots.id`），`acquired_at`，`status`（active/locked/...）。
  - `attribute_keys`：属性键注册中心
    - `key`（如 `attack`、`defense`、`cultivation_speed`）、`label`、`type`（int/float）、`min`、`max`、`description`、`enabled`。
  - `attribute_providers`：属性来源插件注册
    - `id`，`name`，`provider_key`（唯一），`params_schema`（JSON），`enabled`，`priority`（整合顺序）。
  - `user_attribute_overrides`：玩家特例或临时 Buff 来源
    - `user_id`，`provider_key`，`value_json`（JSON），`expires_at`。
  - 视图：
    - `v_user_profile`：聚合 `users` + `user_roots` + 当前地图/宗门等快照。
    - `v_user_attributes_final`：合并所有 Provider 计算结果的只读视图（由服务端填充/缓存）。
- 兼容现有表：沿用 `users`、`items`、`event_*` 等（见 `core/database/schema.sql`）。
- SQLite 配置：
  - WAL 模式：启动时 `PRAGMA journal_mode=WAL;`。
  - 外部注释：在表/列设计时以 `--` 保留注释，供管理端解析与展示。

# 配置与可扩展性
- `_conf_schema.json` 新增配置域：
  - `root_system`：随机生成策略（权重/保底/混合灵根比例）、默认倍率上限（如 1.00–1.10）。
  - `attribute_system`：合并策略（加法/乘法/优先级）、浮点精度、上限保护。
  - `message_style`：世界观输出模板、重点信息高亮规则（【】() 等）。

# 事件总线与 Hook 点
- 公共事件（可拓展）：
  - `on_cultivation_gain`：修为获取时倍率调整（示例：木系 +10%）。
  - `on_breakthrough_check`：突破判定前后（示例：土系稳定性提升）。
  - `on_player_attack` / `on_player_defense`：战斗属性倍率叠加。
  - `on_seclusion_begin` / `on_seclusion_end`：闭关周期与收益变动。
  - `on_mission_reward`：任务奖励倍率调整。
- 灵根 Hooks 以数据驱动：`roots.hooks` JSON 列描述触点与参数，无需改代码即可生效。

# AttributeSystem 接口规范
- Provider 抽象：`provide_attributes(player) -> {key: delta}`。
- 汇总规则：
  - 归一：所有 Provider 输出同一属性键集合，缺失按 0 处理。
  - 顺序：按 `priority` 升序应用；同类可分组（基础→灵根→宗门→装备→功法→Buff）。
  - 合并：
    - 标量：加法叠加后应用倍率上限保护（防止变态数值）。
    - 倍率：乘法叠加但限定范围（例如 0.95–1.10）。
  - 结果缓存：写入 `user_attributes_cache`（可选）以加速查询；更新事件触发时失效。

# RootSystem 接口规范
- `random_generate(user_id) -> root_id`：按权重/保底/混合策略生成，幂等（已有则返回现有并提示）。
- `get_root_template(root_id) -> Dict`：读取 `roots` 行，解析 `hooks` 与倍率。
- `apply_root_bonus(player) -> Dict[str, delta]`：返回灵根基础加成（小幅数值）。
- `calculate_bonus(type, player) -> float|Dict`：按场景返回倍率或属性增量（如 `type="cultivation"`）。

# Action 设计
- DetectRoot（检测灵根）：
  - 入口：命令 `/检测灵根`（或别名如 `/探测灵根`）。
  - 流程：
    - 读取 `user_roots` 判断是否已有灵根；若有，返回提示与简述。
    - 调用 `RootSystem.random_generate()` 生成灵根并绑定。
    - 生成道号（NameGenerator，可配置前后缀与概率），默认不硬编码。
    - 初始化境界到“炼气一层”（可配置），写入 `users.level/xp`。
    - 调用 `AttributeSystem` 汇总初始属性并返回描述。
  - 返回消息（修仙世界观）：
    - 示例：“灵气涌动，你的【灵根：木】已显，修行之路自此启程。修炼加成【+10%】（可随缘波动）。”
  - 幂等与冷却：已有灵根时不重复生成；冷却与次数由事件引擎控制（见 `engine.py:216-267`）。
- ViewProfile（我的信息）：
  - 入口：命令 `/我的信息`（或 `/修仙档案`）。
  - 流程：
    - 读取 `v_user_profile` 基本信息与 `user_roots`。
    - 请求 `AttributeSystem` 计算最终属性与来源拆解。
    - 请求 `RootSystem` 获取灵根描述与 Hooks 摘要。
    - 返回档案模版：
      - 关键信息高亮：【用户ID】【道号】【境界】【灵根】【修炼倍率】【当前地图】等。
      - 属性展示：`attack/defense/hp/crit/cultivation_speed` 等，数值均为小幅加成范围。

# 命令注册
- 在 `main.py` 中仅注册命令与路由，不编写业务逻辑：
  - `/检测灵根` → 调用 ActionDetectRoot。
  - `/我的信息` → 调用 ActionViewProfile。
- 交由现有事件引擎的命令触发器处理：`command_trigger.py:13-51`。

# 后台管理（Admin）
- API 设计：
  - `GET /roots` / `POST /roots` / `PUT /roots/{id}` / `DELETE /roots/{id}`：管理灵根模板。
  - `GET /attribute-keys` / `POST /attribute-keys`：注册新属性键。
  - `GET /attribute-providers` / `POST /attribute-providers`：注册/配置 Provider。
  - `GET /users/{user_id}/profile`：统一档案查询（前后台共享）。
- 前端页面：
  - 菜单新增“灵根模板”“属性键”“属性来源 Provider”。
  - 表单按 `params_schema` 动态生成；所有字段支持启停与注释。

# 文本输出规范
- 世界观语气：
  - 成功：“灵气循脉而动，你的【道号】映照苍穹。”
  - 提示：“你的【清灵草种子】数量不足！(需要:11,拥有:7)”
- 重点信息高亮：【用户ID】【道号】【灵根】【所需时间】【道具】。

# 验证与发布
- 单元测试要点：
  - DetectRoot 幂等；随机生成遵循权重与保底；倍率在安全范围；事件 Hook 调用次序正确。
  - ViewProfile 聚合正确；属性来源拆解与总值一致；缓存失效策略正确。
- 手动验证步骤：
  - 初始化 DB（WAL）；后台录入 3–5 个灵根模板与若干属性键/Provider；
  - 执行 `/检测灵根` → 返回灵根与简述；
  - 执行 `/我的信息` → 返回档案与属性拆解；
  - 修改灵根模板 → `/我的信息` 数值同步变化。
- 回滚与兼容：新增表与 API 均为向前兼容；不改动原有功能；失败时不影响 `users` 基表。

# 性能与安全
- 读多写少场景下使用视图 + 缓存；事件触发时按需失效。
- 严禁日志中输出隐私；所有外部调用使用 `aiohttp/httpx`；遵循 PEP8。
- 数值上限保护防止变态加成；所有倍率默认落入 0.95–1.10 范围。

# 里程碑
- M1：数据表与 Admin 表单。
- M2：Root/Attribute 核心服务与 Provider 框架。
- M3：ActionDetectRoot / ActionViewProfile 流程接入命令触发器。
- M4：事件 Hook 首批点与示例灵根模板。

# 未来扩展
- 灵根重塑/夺舍/变异/觉醒；宗门 Buff；功法/天赋系统；战斗与闭关；任务与机缘事件——均以新增模板/Provider/Hook 实现，无需改核心逻辑。