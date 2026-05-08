# 目标
- 将命令前置判定统一到一个无入参的装饰器 `@command_policy()`，避免每个命令定义参数。
- 默认行为：除“灵根检测”外，全部命令要求已显灵根；后续扩展动作类型与冲突机制。

# 装饰器行为（无入参）
- 从当前 `event` 解析命令名（首个 token）。
- 灵根判定：若命令名不为“灵根检测”，调用 `has_spiritual_root(user_id)`，未显则直接阻断并提示。
- 闭关/深度闭关：暂不做策略；保留集中函数 `evaluate_command_policy` 以便后续扩展，不在装饰器暴露参数。
- 动作类型与冲突（预留）：
  - 读取 `user_buffs` 中 `buff_type='action'` 的当前动作（如 moving/combat/retreat）。
  - 读取 `system_config.action_conflicts`（JSON），如 `{ "moving": ["moving","combat"], "combat": ["moving","combat"] }`。
  - 若当前动作与本命令的动作类型冲突则阻断（命令动作类型由内部映射表维护，后续可迁移到配置）。

# 代码调整
- 新版 `core/utils/command_policy.py`：移除入参，内部解析命令名并执行默认策略。
- `main.py`：命令使用 `@command_policy()`，不再传参。
- 保持 `on_message` 仅做日志与事件，不做命令 gating。

# 验证
- 未显灵根：除“灵根检测”外命令均阻断，返回一次提示；命令逻辑不执行。
- 显灵根后：“我的信息”等正常执行；未来可在配置中增加动作冲突策略，装饰器自动生效。

确认后，我将实现无入参加装饰器、替换现有命令上的装饰器引用，并保留扩展点以承载后续动作类型冲突机制。