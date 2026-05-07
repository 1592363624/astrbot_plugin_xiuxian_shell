# 目标
- 去掉“系统API”左侧列表的折叠箭头与展开动画，改为纯点击选择高亮；右侧显示详情。

# 改动范围
- 仅修改 `admin/frontend/index.html` 左侧“系统API”卡片内的列表组件与少量样式，保持现有搜索与右侧详情逻辑不变。

# 实施要点
- 用自定义列表替换 `<el-collapse>`：
  - 模板：`<div class="api-item" @click="activeApiName=api.name">`，内含 `api.name` 与首行简介。
  - 选中态：基于 `activeApiName` 添加 `.active` 高亮，不再有箭头/动画。
- 样式：
  - `.api-item` 单行布局、hover 背景、边框分隔、圆角；标题/简介采用省略显示。
  - 保留现有 `.api-title/.api-subtitle` 省略与配色，新增 `.api-item.active` 高亮。
- 逻辑：
  - 点击项：仅设置 `activeApiName`，右侧详情通过既有 `selectedApi/selectedApiMetadata` 计算显示。
  - 搜索：沿用 `filteredApis`；无需改动。

# 验证
- 打开“事件api”菜单：左侧不再出现箭头，点击切换右侧详情；无展开/收起动画。
- 搜索后列表正确筛选；首次加载默认选择第一项。

# 风险与兼容
- 不改动后端 API；不影响其他菜单。
- 仅对前端单页做轻量替换，回滚简易。