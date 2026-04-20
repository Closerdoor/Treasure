# 个人收藏馆设计文档 03：数据模型与内容生产链路

## 1. 设计目标

本设计文档用于定义以下问题：

- 内容如何录入
- 输入一个标题后，系统如何搜索和确认目标条目
- 自动补全哪些信息，哪些信息必须由馆长确认
- 正式内容文件如何组织
- 本地 SQLite 数据库承担什么职责
- 图片如何命名、存放和关联
- 数字 ID 如何分配和维护

该文档与前两份文档共同构成当前阶段的完整基础设计。

## 2. 总体流程

新增一条内容时，整体链路分为 7 个阶段：

1. 输入
2. 解析
3. 搜索候选
4. 人工确认
5. 自动补全
6. 馆长补充少量人工字段
7. 生成正式内容文件和页面索引

对应的基本流程如下：

```text
输入标题/导入 YAML
  -> 解析基础线索
  -> 搜索候选条目
  -> 若有歧义则人工确认
  -> 自动补全基础元数据
  -> 下载并整理图片
  -> 馆长补充少量人工字段
  -> 分配正式 ID
  -> 生成 Markdown 内容文件
  -> 构建时生成列表/搜索/标签索引
```

## 3. 录入入口设计

支持两种入口。

### 3.1 单条录入

适用场景：

- 临时新增一条内容
- 只知道标题，先让系统搜索
- 手头只有少量补充信息

示例：

```text
新增电影：星际穿越
新增电影：星际穿越 2014 导演诺兰
新增书籍：百年孤独
新增单曲：夜空中最亮的星
```

### 3.2 YAML 批量录入

适用场景：

- 一次性录入多条内容
- 从笔记迁移一批待整理条目
- 先粗录标题，后续统一补全

建议目录：

- `ingest/batches/*.yaml`

建议文件结构：

```yaml
batch_id: 2026-04-18-movie-import-01
module: video
submodule: movie
items:
  - title: 星际穿越
  - title: 盗梦空间
    year: 2010
    director:
      - 克里斯托弗·诺兰
  - title: 沙丘
    year: 2021
    country:
      - 美国
```

说明：

- `batch_id` 用于标识本次导入任务
- `module` 和 `submodule` 可写在批次级别，也可由每个条目单独覆盖
- `items` 中允许只写标题

## 4. 录入卡片模板

馆长手动补充或修正信息时，建议使用统一录入卡片格式。

最简模板：

```yaml
type: movie
title: 星际穿越
```

增强模板：

```yaml
type: movie
title: 星际穿越
original_title: Interstellar
year: 2014
country:
  - 美国
director:
  - 克里斯托弗·诺兰
cast:
  - 马修·麦康纳
  - 安妮·海瑟薇
source_hint:
  - imdb
  - douban
summary: 
my_note: 
tags:
  - 站长精选
curator_rating: 
status: draft
```

字段说明：

- `type`：录入类型，简写字段，供导入器快速识别
- `title`：标题，必填
- `source_hint`：仅作为搜索线索，不是正式展示字段
- `my_note`：馆长临时备注，默认不直接进入前端页面
- `status`：草稿状态

## 5. 录入状态机

每条内容在进入正式库之前，建议经过明确状态流转。

状态定义：

- `draft`：初始草稿
- `searching`：正在搜索候选内容
- `pending_confirm`：存在歧义，等待馆长确认
- `enriching`：已确认目标，正在自动补全
- `pending_editorial`：等待馆长补充少量人工字段
- `ready`：可生成正式内容文件
- `published`：已生成正式内容文件并进入站点
- `archived`：归档，不再公开展示

状态流转：

```text
draft -> searching -> pending_confirm -> enriching -> pending_editorial -> ready -> published
```

说明：

- 如果搜索结果唯一且置信度足够高，可跳过 `pending_confirm`
- 只要存在重名或关键字段冲突，必须进入 `pending_confirm`
- `published` 后如仅修改评论或标签，不重新分配 ID

## 6. 数据来源与可信度规则

### 6.1 数据来源策略

自动补全采用多来源交叉校验。

原则：

- 优先选择结构化程度高、稳定性强的数据源
- 同时参考中文站点与国际站点
- 若核心字段冲突，则等待人工确认

### 6.2 可自动采用的字段

以下字段可由系统自动补全后直接进入草稿：

- 标题
- 原名
- 发布时间
- 国家 / 地区
- 作者 / 导演 / 艺术家 / 开发商
- 类型
- 简介
- 外部站点 ID
- 海报或封面链接

### 6.3 必须由馆长确认或填写的字段

以下字段不应由外部数据自动作为正式值：

- 馆长评分
- 馆藏标签
- 是否馆长精选
- 少量人工备注
- 是否公开展示

### 6.4 冲突处理规则

当多个来源出现以下冲突时，应进入人工确认：

- 同名不同作品
- 发布时间不一致
- 作者 / 导演不一致
- 国家 / 地区不一致
- 海报明显不一致

## 7. 正式内容数据分层

每条正式内容建议拆成四层字段。

### 7.1 标识层

用于唯一识别和路由。

字段建议：

- `id`
- `module`
- `submodule`
- `title`
- `originalTitle`
- `slug`
- `status`
- `publishedAt`

说明：

- 正式 URL 使用数字 `id`
- `slug` 仍然保留，用于搜索、SEO、图片命名或备用场景
- `slug` 不作为主路由唯一键

### 7.2 基础元数据层

字段建议：

- `releaseDate`
- `countries`
- `genres`
- `creators`
- `cast`
- `platforms`
- `duration`
- `episodes`
- `publisher`
- `isbn`
- `label`
- `developer`
- `series`
- `externalIds`

说明：

- 不是所有模块都需要全部字段
- 由模块模板决定实际启用的字段集合

### 7.3 馆长编辑层

字段建议：

- `curatorRating`
- `briefNote`
- `introNote`
- `isFeatured`
- `consumedAt`
- `contentStatus`

### 7.4 展示增强层

字段建议：

- `cover`
- `gallery`
- `tags`
- `relatedEntries`
- `soundtracks`
- `awards`
- `quotes`
- `communityHighlights`
- `relatedNotes`

## 8. 正式内容文件格式

### 8.1 存放目录

建议结构：

- `content/video/movie/*.md`
- `content/video/tv/*.md`
- `content/video/anime/*.md`
- `content/book/classic/*.md`
- `content/music/single/*.md`
- `content/game/indie/*.md`

### 8.2 文件命名规则

正式内容文件建议命名为：

`{id}.md`

示例：

- `content/video/movie/01010001.md`
- `content/book/classic/02020008.md`

这样可避免标题变化导致文件名变化。

### 8.3 内容文件示例

以电影为例：

```md
---
id: 01010001
module: video
submodule: movie
title: 星际穿越
originalTitle: Interstellar
slug: interstellar
status: published
publishedAt: 2026-04-18

releaseDate: 2014-11-07
countries:
  - 美国
genres:
  - 科幻
  - 冒险
director:
  - 克里斯托弗·诺兰
writers:
  - 乔纳森·诺兰
  - 克里斯托弗·诺兰
cast:
  - 马修·麦康纳
  - 安妮·海瑟薇
duration: 169

externalIds:
  imdb: tt0816692
  douban: "1889243"

cover: /assets/video/movie/01010001/cover.jpg
gallery:
  - /assets/video/movie/01010001/still-01.jpg
  - /assets/video/movie/01010001/still-02.jpg

tags:
  content:
    - 科幻
    - 太空
    - 时间
  editorial:
    - 站长精选
  owners:
    - 馆长

curatorRating: 9.5
isFeatured: true
briefNote: 一部兼具宇宙尺度与情感重量的科幻电影。
introNote: 适合完整沉浸观看。
giscus: true
---

## 简介

未来的地球已经难以生存，一组宇航员通过虫洞寻找人类的新家园。

## 馆长备注

这里放少量补充说明，使用 Markdown 书写。

## 延伸信息

- 配乐：Hans Zimmer
- 适合标签：太空、亲情、科幻史诗
```

说明：

- 结构化字段放在 Frontmatter
- 长文、评论、专题式内容放在 Markdown 正文
- 列表页与搜索页主要消费 Frontmatter 和构建生成的 JSON

## 9. 构建索引数据

构建时从正式内容文件生成索引数据，供站点使用。

建议生成以下索引：

- `generated/entries.json`
- `generated/modules/{module}.json`
- `generated/submodules/{module}-{submodule}.json`
- `generated/tags.json`
- `generated/search-index.json`
- `generated/recent.json`

用途：

- 列表页加载
- 搜索页检索
- 标签聚合页统计
- 首页最近新增区块

## 10. SQLite 本地数据库职责

SQLite 用于本地内容工坊，不作为线上运行数据库。

### 10.1 建议数据表

建议至少包含以下逻辑表：

- `ingest_jobs`
- `ingest_items`
- `candidate_matches`
- `source_records`
- `asset_records`
- `id_registry`

### 10.2 表职责

#### ingest_jobs

记录一批导入任务。

字段示例：

- `job_id`
- `source_type`
- `source_file`
- `status`
- `created_at`

#### ingest_items

记录每一条待入库内容。

字段示例：

- `item_id`
- `job_id`
- `module`
- `submodule`
- `raw_input`
- `parsed_title`
- `parsed_year`
- `status`
- `confirmed_candidate_id`

#### candidate_matches

记录搜索返回的候选条目。

字段示例：

- `candidate_id`
- `item_id`
- `source_name`
- `source_entry_id`
- `title`
- `original_title`
- `year`
- `score`
- `payload_json`

#### source_records

记录已确认采用的外部来源信息。

字段示例：

- `record_id`
- `item_id`
- `source_name`
- `external_id`
- `normalized_json`

#### asset_records

记录图片与媒体资源。

字段示例：

- `asset_id`
- `item_id`
- `asset_type`
- `source_url`
- `local_path`
- `checksum`
- `status`

#### id_registry

记录各子模块当前已分配到的最大编号。

字段示例：

- `module_code`
- `submodule_code`
- `current_seq`

## 11. ID 分配规则细则

### 11.1 正式 ID 组成

正式 ID 格式为：

`MMSSNNNNNN`

示例：

- `0101000001`：影视 / 电影 / 第 1 条
- `0101000025`：影视 / 电影 / 第 25 条
- `0203000007`：书 / 名著 / 第 7 条

### 11.2 分配时机

建议在内容进入 `ready` 状态时分配正式 ID。

原因：

- 避免草稿阶段大量占用正式编号
- 减少候选误录导致的编号浪费

### 11.3 分配规则

- 根据 `module + submodule` 查找当前最大序号
- 将 `NNNNNN` 递增 1
- 生成正式 ID 并写入内容文件
- 同步记录到 `id_registry`

### 11.4 回收规则

- 已发布内容删除后，ID 不回收
- 草稿阶段若尚未进入 `ready`，不分配正式 ID
- 若生成正式文件后撤销发布，该 ID 仍视为已使用

## 12. 图片目录与命名规范

### 12.1 目录结构

建议统一放在：

- `public/assets/video/movie/{id}/`
- `public/assets/book/classic/{id}/`
- `public/assets/music/single/{id}/`
- `public/assets/game/indie/{id}/`

例如：

- `public/assets/video/movie/01010001/cover.jpg`
- `public/assets/video/movie/01010001/still-01.jpg`
- `public/assets/video/movie/01010001/still-02.jpg`

### 12.2 命名规则

建议命名：

- 主封面：`cover.ext`
- 剧照：`still-01.ext`、`still-02.ext`
- 书内图：`page-01.ext`
- 游戏截图：`shot-01.ext`
- 音乐封面补图：`art-01.ext`

说明：

- 文件名不使用标题
- 避免标题修改带来的重命名问题
- 所有图片按内容 ID 管理

### 12.3 数量建议

虽然当前不强制压缩，但建议仍设置上限：

- 海报 / 封面：1 张主图
- 补充图：建议 3 到 8 张
- 超过上限时优先保留最具展示价值的图片

## 13. 搜索与确认流程

### 13.1 搜索输入

系统优先使用以下线索搜索：

- 标题
- 原名
- 年份
- 导演 / 作者 / 艺术家
- 国家 / 地区
- 模块与子模块

### 13.2 候选输出

候选结果建议展示：

- 标题
- 原名
- 年份
- 主要创作者
- 国家 / 地区
- 来源站点
- 置信度

### 13.3 确认规则

以下情况必须向馆长确认：

- 搜索到多个高相似候选
- 同名跨年份
- 同名跨国家
- 同一标题存在电影版和剧集版

### 13.4 自动确认条件

同时满足以下条件时，可视为高置信唯一命中：

- 标题高度匹配
- 年份匹配或无冲突
- 模块与子模块一致
- 主要创作者一致或未冲突

## 14. 模块通用字段与专属字段

### 14.1 通用字段

建议所有模块都保留：

- `id`
- `module`
- `submodule`
- `title`
- `originalTitle`
- `slug`
- `status`
- `cover`
- `tags`
- `curatorRating`
- `briefNote`
- `isFeatured`
- `publishedAt`

### 14.2 影视专属字段

- `director`
- `writers`
- `cast`
- `duration`
- `episodes`
- `seasonCount`
- `soundtracks`
- `awards`

### 14.3 图书专属字段

- `authors`
- `publisher`
- `isbn`
- `translator`
- `pages`
- `quotes`
- `edition`

### 14.4 音乐专属字段

- `artists`
- `label`
- `tracklist`
- `highlightTracks`
- `relatedWork`

### 14.5 游戏专属字段

- `platforms`
- `developer`
- `publisher`
- `gameModes`
- `playtime`
- `dlc`

## 15. 标签模型

为避免不同标签混用，建议沿用三层标签结构：

```yaml
tags:
  content:
    - 科幻
    - 太空
  editorial:
    - 站长精选
    - 年度推荐
  owners:
    - 馆长
```

说明：

- `content`：描述作品内容特征
- `editorial`：描述馆藏视角或策展属性
- `owners`：为多用户扩展预留

## 16. 评分与评论字段预留

### 16.1 当前启用

- `curatorRating`
- `giscus`

### 16.2 预留字段

```yaml
community:
  userScoreEnabled: false
  finalScoreMode: curator_only
  commentProvider: giscus
```

说明：

- V1 仅展示馆长评分
- 用户评分后续再接入外部服务
- 评论系统当前统一走 Giscus

## 17. 构建与发布边界

### 17.1 本地阶段

本地内容工坊负责：

- 接收输入
- 搜索候选
- 确认条目
- 自动补全
- 下载图片
- 分配 ID
- 生成正式内容文件

### 17.2 构建阶段

Astro 构建过程负责：

- 读取内容目录
- 生成列表页和详情页
- 生成标签页和搜索索引
- 输出静态站点到 GitHub Pages 可部署产物

### 17.3 线上阶段

GitHub Pages 负责：

- 托管静态页面
- 提供公开访问

Giscus 负责：

- 提供评论能力

说明：

- 线上不依赖 SQLite
- 线上不直接写入仓库中的内容数据

## 18. 当前设计结论

这一阶段已经明确了以下关键约束：

- 正式内容文件采用 Markdown + Frontmatter
- 本地工作数据库采用 SQLite
- 新增内容支持单条录入和 YAML 批量导入
- 歧义条目必须先人工确认
- 正式 ID 使用 `MMSSNNNNNN` 数字结构
- URL 使用 `/{module}/{submodule}/{id}`
- 图片以内容 ID 为目录组织并统一入仓库
- 构建时生成 JSON 索引供列表页与搜索页使用

下一阶段应继续设计：

- 各模块详细字段 schema
- 首页和影视模块的 UI 风格方案
- 页面线框图
- 本地工具命令设计
