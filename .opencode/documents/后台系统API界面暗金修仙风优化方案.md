## 目标

* 优化左侧“系统API”模块的美观度，避免文字换行，移除展开箭头与展开动画，改为纯列表点击选中。

* 优化右侧“参数列表”表格与详情区域，统一使用暗金修仙炫酷风格。(整体风格可多参考凡人修仙传动漫)

* 保持现有数据加载与交互逻辑不变，仅调整结构与样式。

## 改动范围

* 全局统一风格

## 视觉方案（暗金修仙风）

* 新增主题变量（CSS 变量）：背景深色、面板暗黑、金色描边与辉光、淡紫点缀。

* 左右卡片标题加入细金边与柔光阴影；列表项悬浮与选中态采用金色高亮；表格头部暗金渐变、网格线金色半透明。

* 字体保持现状，增强可读性对比与层次（标题略微加粗、内容正常权重）。

## 交互调整

* 左侧取消折叠：将 `el-collapse` 改为可滚动的点击列表（不展开、不显示箭头）。

* 点击列表项仅改变右侧 `selectedApi`（沿用现有 `activeApiName`/`selectedApi` 逻辑）。

* 禁止展开动画与箭头：若保留组件壳，隐藏 `.el-collapse-item__arrow`，并移除高度过渡。

## 具体修改点

* 左侧列表结构（替换折叠为纯列表）：`index.html:345–352`

  * 用 `<el-scrollbar>` 包裹一个 `v-for` 的列表项容器（如 `<div class="api-item">`），每项 `@click="activeApiName=api.name"`。

  * 列表项样式：单行展示、`white-space: nowrap; text-overflow: ellipsis;`，选中态金色边与背景辉光。

* 隐藏箭头与动画（若临时保留 `el-collapse` 壳）：`index.html:<style>` 末尾

  * `.el-collapse-item__arrow { display: none; }`

  * `.el-collapse-item__wrap { transition: none !important; height: auto !important; }`

* 文本换行优化（避免断行）：

  * 左侧标题行：`white-space: nowrap; overflow: hidden; text-overflow: ellipsis;`

  * 右侧表格单元格：为 `name`/`annotation`/`default` 列设置 `white-space: nowrap;` 与最大宽度 + 省略号。

* 表格暗金风格：`index.html:367–373`

  * 覆盖 `el-table` 主题变量（表头背景、边框色、行悬浮背景等）与网格线为半透明金色。

* 右侧详情卡片与说明块：`index.html:356–366`

  * 卡片背景改为深色、边框金色、投影柔光；`api-doc` 文本块采用暗金分割线与更清晰的段落行距。

## 主题变量示例（放置于 `index.html` 的 `<style>` 顶部或末尾）

* `--xiuxian-bg`, `--xiuxian-panel`, `--xiuxian-gold`, `--xiuxian-gold-weak`, `--xiuxian-purple`, `--xiuxian-shadow` 等，用于背景、描边、悬浮态与阴影统一控制。

* 用变量为 `.api-list`、`.api-detail`、`.el-card`、`.el-table`、列表项与按钮统一着色，便于后续在后台调整。

## 代码引用

* 左侧“系统API”列表与搜索：`e:\AstrBot\data\plugins\astrbot_plugin_re_xiuxian\admin\frontend\index.html:339–352`

* 右侧详情与参数表：`e:\AstrBot\data\plugins\astrbot_plugin_re_xiuxian\admin\frontend\index.html:356–373`

* 数据与计算属性：

  * `data()`：`512–546`

  * `filteredApis`/`selectedApi`：`559–569`

  * `loadSystemApis()`：`609–618`

##

确认后我将按以上步骤实施，并保证不改动现有功能，只做结构与样式优化。
