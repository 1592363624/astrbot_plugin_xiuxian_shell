# 实施计划

## 逻辑与 gating（不使用 users.joined）
- 新增 API：
  - `has_spiritual_root(user_id)`：查询 `user_buffs(buff_type=spiritual_root)` 是否存在，用作加入判定。
  - `detect_spiritual_root(user_id)`：读取 `spiritual_roots_catalog` 与权重，抽取灵根，写入 `user_buffs`，返回结果文案。
  - `get_user_profile(user_id)`：汇总用户信息（users + 灵根 + 视图统计），格式化给“我的信息”。
- gating：在命令处理处，如未检测灵根且命令不是“灵根检测”，直接提示先进行灵根检测。

## 配置
- 在 `init` 默认加入 `spiritual_roots_catalog` 与 `spiritual_roots_weights`（按你之前的设定与 1.x 乘数）。

## 命令
- main.py 注册：
  - `灵根检测`：委托到服务层 `handle_linggen_detect`。
  - `我的信息`：委托到服务层 `handle_my_info`。

## 服务层
- `PluginService`：
  - `handle_linggen_detect(event)`：调用 API 抽取灵根；返回修真语境提示。
  - `handle_my_info(event)`：调用 API 汇总档案；返回格式化文本。
  - `handle_message`：加入 gating（基于 `has_spiritual_root`）。

## 验证
- 首次发送“灵根检测”→ 返回抽取结果并写入 buff；随后“我的信息”显示完整数据；未检测灵根时尝试其他命令将被提示。