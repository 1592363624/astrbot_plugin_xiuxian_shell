# 方案概述

## 目标
- 用集中式“命令访问策略”替代各命令内二次校验，避免新增指令时重复逻辑。
- 支持灵根未检测的统一 gating、闭关/深度闭关的状态 gating，以及后续扩展（如稳固值阈值）。

## 配置
- 在 `system_config` 增加 `command_policies`（JSON）：每个命令的策略与默认策略，例如：
  - `default`: `{ require_root: true, allow_during: "any" }`
  - `灵根检测`: `{ require_root: false, allow_during: "any" }`
  - `我的信息`: `{ require_root: true, allow_during: "any" }`
- 状态定义采用 `user_buffs`（`buff_type='status'`）：`retreat_normal`、`retreat_deep`，用 `duration/expires_at` 表示有效期。

## 实现点（框架级）
- 在 `core/api/game.py` 提供：
  - `get_command_policies()`：读取 `system_config.command_policies`。
  - `has_spiritual_root(user_id)`：判断是否已显灵根。
  - `has_active_status(user_id, status_name)`：判断状态 buff 是否有效。
  - `evaluate_command_policy(user_id, command)`：按策略统一判定（灵根/状态），返回 `(ok, message)`。
- 在 `PluginService.handle_message` 开头调用 `evaluate_command_policy`，若不通过直接返回提示，后续不再执行任何命令逻辑或事件系统。
- 移除命令方法内的二次校验，使命令处理保持纯净（仅负责业务输出）。

## 状态 gating 规则
- `allow_during`: `any`（任意状态允许）、`normal`（仅普通闭关允许）、`none`（闭关期间禁止）。
- 例如：战斗类命令设置 `none`，日常查询设置 `any`，轻量修炼设置 `normal`。

## 验证
- 未显灵根→除“灵根检测”外统一被阻断。
- 开启 `retreat_deep` 状态→仅策略 `any` 的命令可执行；其余阻断。
- 关闭状态后→命令恢复可执行。

确认后，我将：
1) 在 `game.py` 实现策略读取与统一判定；
2) 在 `PluginService.handle_message` 切换为集中式 gating；
3) 移除命令里的二次校验；
4) 提供示例状态设置事件与默认策略示例。