# Contracts

> Purpose: 记录当前生效的数据契约、模板骨架与变更联动规则。
> Status: active
> Scope: 数据模型职责、关键字段语义、模板化结构、变更影响矩阵
> Out of scope: 视觉样式、阶段进度、具体录入命令教程
> Update triggers: 数据结构变化、模板变化、workflow 联动关系变化
> Priority: 3

## 内容目录单元

以电影为例，当前单条内容目录包含：

```text
content/video/movie/{ID}/
  data.json
  source.json
  index.md
  raw/
  images/
```

各文件职责：

- `data.json`
  - 前台正式结构化数据来源
- `source.json`
  - 字段来源与溯源记录
- `index.md`
  - 审阅与归档材料，不直接进入前台展示链路
- `raw/`
  - 原始抓取材料、对比报告、过程产物
- 图片目录
  - 海报、剧照、头像、视频缩略图等本地资源

## ID 与本地工坊职责

### 内容 ID 规则

当前内容 ID 采用：

```text
MMSSNNNNNN
```

说明：

- `MM` 表示一级模块编号
- `SS` 表示子模块编号
- `NNNNNN` 表示该子模块下的递增序号
- `id` 是稳定主标识，标题变化不影响 `id` 与详情路由

### 本地工坊与 SQLite 职责

SQLite 只用于本地内容工坊，不作为线上数据库。

当前稳定职责包括：

- 导入任务记录
- 待确认条目记录
- 候选匹配缓存
- 来源数据缓存
- 图片与资源记录
- ID 分配记录

## 当前关键字段语义

### `synopsis`

- 用于列表页、首页卡片和详情页顶部短简介
- 不是完整剧情

### `story`

- 用于详情页 `详情介绍` Tab 的完整剧情
- 已上映作品：应能独立阅读，覆盖主要人物、关键转折与结局
- 未上映 / 未公开完整剧情作品：只能整理公开剧情物料，不得补写未公开后续
- 这类条目的 `story.note` 必须明确标注“基于公开剧情物料整理，非完整剧情/非完整人生全程”

### `reviews`

- 只保留精选长评或高质量评语
- 不再用一句话短评或热门短评直接充数
- 来源优先使用豆瓣长评页，并允许人工筛选整理

### `images.poster` 与 `images.posters`

- `images.poster` 永远表示主海报
- `images.posters` 表示补充海报列表，不包含主海报
- `images.postersTotal` 是源站可获取总量元数据，不等于本地数组长度

### `images.stillsTotal`

- 表示源站可获取剧照总量，不等于当前本地已下载文件数量

### `similar`

- 当前采用渐进式站内关系方案
- 已录入站内、且详情页已存在的作品可补 `id` 并支持站内跳转
- 未录入站内的作品允许先以占位状态保留在 `similar` 中
- 未录入站内的摘要结构最小为：`title` / `year`，并可补 `rating`
- 未录入站内时不跳外链

### `series`

- `series` 与 `similar` 采用同样的渐进式站内关系规则
- 已录入站内、且详情页已存在的作品可补 `id` 并支持站内跳转
- 未录入站内时允许先以占位状态展示，不跳外链
- 当前按上映时间排序，不单独维护系列顺序字段

### `genre` 与 `tags`

- `genre` 与 `tags` 是两套不同语义，不得混用
- `genre` 表示外部平台相对标准化的类型分类
- `tags` 同时包含外部平台标签与手动维护标签
- 列表页筛选 UI 中不区分标签来源，统一作为一个标签集合供用户筛选

### `links`

- 外部来源链接统一放在 `links`
- 缺失值统一使用 `null`

### 评分字段

- 前台主评分统一为 10 分制
- 豆瓣 / IMDb / TMDB 直接按原始 10 分值使用
- 烂番茄按百分比换算成 10 分制后参与计算
- 缺失的平台直接跳过，只对有值平台求平均
- 最终展示值保留 1 位小数

### 当前不维护的字段

- `rated`（MPAA 分级）不再纳入当前主契约
- `awards`（获奖信息）不再纳入当前主契约

### 保留但不在前台展示的字段

- `imdbId` 继续保留在数据层，用于跨平台对齐、补数与外部来源关联
- `imdbId` 当前不作为前台界面展示字段

## 当前稳定模板骨架

### 电影录入模板

电影条目当前必须维护：

- `data.json`
- `source.json`
- `index.md`
- 必要图片资源

`.opencode/skills/movie-entry-workflow/` 下文档继续作为电影录入执行参考存在，但不得高于当前 `docs/` 主文档体系。

### 页面派生数据契约

首页与列表页不直接消费作品全量数据，而使用稳定的页面字段子集。

#### 首页模块预览卡片最小展示契约

- 海报
- 标题
- 年份
- 类型
- 地区
- 综合评分
- 时长
- 悬停简介

#### 影视列表页列表卡片最小展示契约

- 海报
- 标题
- 原名
- 年份
- 地区
- 类型
- 导演
- 综合评分
- 简介
- 主演
- 四个平台原始评分

补充约束：

- 标签不进入卡片展示，只用于搜索与筛选
- 原始评分只显示分数，不显示人数或额外说明
- 原始评分只显示有值的平台
- 网格 / 卡片视图中的主演只展示一行，溢出隐藏
- 列表视图中的主演展示前 3 位

#### `similar` / `series` 占位卡最小展示契约

- 标题
- 年份
- 海报（如有）
- 综合评分（如有）
- `暂未收录` 状态标记
- 不可点击

#### 电影详情页 `音乐` Tab 数据契约

- `音乐` Tab 当前主要读取 `soundtrack`
- 最小展示骨架包括：原声带名称、作者 / 作曲、年份、曲目列表
- 当 `soundtrack` 缺失或曲目为空时，允许隐藏 `音乐` Tab，而不是强制展示空白区块

## 变更影响矩阵

### 当 `data.json` 字段语义或结构变化时

必须同步检查并更新：

- `CONTRACTS.md`
- `.opencode/skills/movie-entry-workflow/SKILL.md`
- `.opencode/skills/movie-entry-workflow/FIELD-SOURCE-MAPPING.md`
- `.opencode/skills/movie-entry-workflow/FIELD-VALIDATION.md`
- `.opencode/skills/movie-entry-workflow/DATA-TO-MD-MAPPING.md`
- `.opencode/skills/movie-entry-workflow/INDEX-MD-TEMPLATE.md`
- 对应真实条目的 `source.json`
- 未来前台读取逻辑

### 当详情页 Tab 结构变化时

必须同步检查并更新：

- `UI-GUIDE.md`
- `CONTRACTS.md`
- `PROJECT.md`（如果影响 V1 范围或主共识）
- `.opencode/skills/movie-entry-workflow/INDEX-MD-TEMPLATE.md` 与映射文档（如受影响）

### 当列表页卡片骨架变化时

必须同步检查并更新：

- `UI-GUIDE.md`
- `CONTRACTS.md`
- 首页模块预览卡片相关说明

### 当录入 workflow 规则变化时

必须同步检查并更新：

- `.opencode/skills/movie-entry-workflow/` 下执行细则
- 本文档中的契约摘要
- `STATUS.md` 中最近关键变更（如会影响当前阶段判断）

## 与 workflow 文档的边界

当前约定如下：

- `docs/CONTRACTS.md` 负责讲“当前项目采用什么数据与模板契约”，并且是当前规范来源
- `.opencode/skills/movie-entry-workflow/` 负责讲“电影具体如何录入、如何校验、如何生成产物”

如果只是电影录入执行细节变化，不需要把全部细节复制进 `docs/`。

如果 workflow 文档与主文档冲突，应优先修正 workflow 文档以与主文档保持一致。

## 当前约束总结

- 不推翻当前 workflow 重来
- 以“承认现有事实标准，再局部统一”为原则
- 模板变化必须配套更新变更影响范围
