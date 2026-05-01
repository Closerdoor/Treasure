# 个人收藏馆设计文档 10：电影 data.json 现状审计

## 1. 文档目的

本文档基于当前已录入的 3 部电影数据文件进行现状审计：

- `content/video/movie/0101000001/data.json`
- `content/video/movie/0101000002/data.json`
- `content/video/movie/0101000003/data.json`

本文档的目标不是立刻修改 schema，而是先回答：

- 当前电影 `data.json` 事实标准已经长成什么样
- 哪些字段在现状中是稳定存在的
- 哪些字段是可选字段
- 哪些字段命名或结构还不够统一
- 后续讨论第 11 部分时，哪些地方值得重点关注

## 2. 当前结论

当前电影 `data.json` 已经形成了一套较稳定的事实标准。

结论如下：

- 当前 `data.json` 并不是缺乏结构，而是已经有较清晰的主体结构
- 当前最主要的问题不是“完全不够用”，而是：
  - 某些字段是否必填还没有被正式写清楚
  - 少数字段命名和子结构存在不统一现象
  - 一些字段适合前台直接使用，一些字段更适合作为原始数据保留
- 当前阶段不建议轻易推翻现有结构
- 更合理的方向是：
  - 先确认现有结构
  - 再局部规范化
  - 最后再决定是否补少量字段

## 3. 当前 data.json 的逻辑分组

以下“分组”是逻辑分组，不代表要改成嵌套结构，只是帮助理解现状。

### 3.1 标识与基础信息

当前稳定出现的字段：

- `id`
- `title`
- `originalTitle`
- `year`
- `genre`
- `country`
- `language`
- `runtime`
- `releaseDate`
- `aka`

审计结论：

- 这一组已经比较稳定
- 可以视为当前作品级数据中的核心基础信息层

### 3.2 演职员信息

当前稳定出现的字段：

- `director`
- `writer`
- `cast`
- `otherCast`
- `producer`

审计结论：

- 这一组也是当前结构中最稳定的部分之一
- 人员对象中常见字段包括：
  - `name`
  - `nameEn`
  - `role`
  - `avatar`
  - `avatarSource`
  - `works`
  - `baike`
- 不同子类型人物对象的字段丰富度不同，但整体结构清晰

### 3.3 评分与外部标识

当前出现过的字段：

- `imdbId`
- `doubanId`
- `doubanRating`
- `doubanVotes`
- `imdbRating`
- `imdbVotes`
- `rated`
- `awards`
- `runtimeEn`

审计结论：

- 这一组字段已经存在，但不是每部电影都齐全
- 其中 `doubanRating`、`doubanVotes`、`imdbId`、`doubanId` 出现较稳定
- `imdbRating`、`imdbVotes`、`rated`、`awards`、`runtimeEn` 当前更像可选增强字段

### 3.4 内容资料

当前稳定出现的字段：

- `synopsis`
- `similar`
- `reviews`

审计结论：

- `synopsis` 已稳定采用对象结构：
  - `text`
  - `note`
- `similar` 和 `reviews` 也已形成稳定数组结构
- 这部分已经能很好支撑详情页中的介绍、影评、相似作品等区域

### 3.5 媒体资源

当前稳定出现的字段：

- `videos`
- `images`
- `soundtrack`

审计结论：

- 这一组已经是当前 schema 的重要组成部分
- 能较好支撑详情页中的视频、图片、音乐三个 Tab

### 3.6 外部链接与系统字段

当前稳定出现的字段：

- `links`
- `module`
- `submodule`
- `createdAt`
- `updatedAt`

审计结论：

- 当前这组字段已经稳定存在
- `links` 用于外部来源跳转
- 系统字段用于归档、标识和构建流程

## 4. 当前最稳定的字段集合

基于 3 部电影现状，以下字段可以视为当前电影 `data.json` 的核心稳定集合：

- `id`
- `title`
- `originalTitle`
- `year`
- `director`
- `writer`
- `cast`
- `otherCast`
- `producer`
- `genre`
- `country`
- `language`
- `runtime`
- `releaseDate`
- `aka`
- `imdbId`
- `doubanId`
- `doubanRating`
- `doubanVotes`
- `synopsis`
- `videos`
- `images`
- `soundtrack`
- `similar`
- `reviews`
- `links`
- `module`
- `submodule`
- `createdAt`
- `updatedAt`

说明：

- 这批字段已经足以支撑当前详情页的大多数展示需求
- 后续第 11 部分应优先围绕这批字段定义正式规范

## 5. 当前明确属于可选增强字段的内容

基于现状，这些字段更适合作为“有数据则保留、无数据也不影响主体结构”的增强信息：

- `runtimeEn`
- `rated`
- `awards`
- `imdbRating`
- `imdbVotes`
- `avatarSource`
- `avatarNote`
- `works`
- `baike`

说明：

- 这些字段很有价值
- 但当前并未在全部条目上稳定齐备
- 因此更适合作为可选字段，而不是现阶段硬性要求所有作品都必须补齐

## 6. 当前发现的不一致点

这部分是后续第 11 部分需要重点关注的地方。

### 6.1 `soundtrack` 与 `soundtrack.tracks` 字段命名不统一

当前发现：

- 修改前：`0101000001`、`0101000003` 的 `soundtrack` 顶层名称字段使用 `title`
- 修改前：`0101000001` 的 `soundtrack.tracks[]` 使用 `title`
- 修改前：`0101000002` 与 `0101000003` 的 `soundtrack.tracks[]` 使用 `name`

说明：

- 这代表原声带专辑名和曲目名都曾存在命名不一致
- 现已统一为：
  - `soundtrack.name`
  - `soundtrack.tracks[].name`
- 该调整不改变展示内容，只统一数据字段名
- 对应的 `source.json` 也应同步使用同一字段命名，避免数据与溯源结构脱节

### 6.2 `images.poster` 与 `images.posters` 的语义曾不统一

当前发现：

- 有的条目会把 `poster-main.jpg` 放进 `posters`
- 有的条目则没有明显统一规则

说明：

- 现已统一规则：
  - `images.poster` 永远只表示主海报
  - `images.posters` 只表示补充海报列表，不包含主海报
  - `images.postersTotal` 只统计补充海报数量，不包含主海报
- 当前这轮只统一规则文档，不直接修改已有条目中的图片数组内容

### 6.3 `links.tmdb` 的空值形式不统一

当前发现：

- 修改前：有的条目是完整 URL
- 修改前：有的条目是空字符串

说明：

- 现已统一规则：缺失链接使用 `null`
- 该调整不改变展示内容，只统一空值表达方式
- 对应的 `source.json.links.value` 也应显式保持同样规则

### 6.4 部分人物对象字段丰富度不同

当前发现：

- 有的人物对象包含 `avatarSource`、`works`、`baike`
- 有的人物对象只包含最核心字段

说明：

- 这不一定是问题
- 但后续需要明确“人物对象的最小必需字段”和“可选增强字段”

### 6.5 `videos` 允许为空数组

当前发现：

- 有的电影存在完整视频列表
- 有的电影是空数组

说明：

- 当前这是一种合理设计
- 说明 `videos` 应被视为可选内容区，而不是必定有数据的区块

### 6.6 `postersTotal` / `stillsTotal` 的语义需要正式说明

当前发现：

- 这些数字并不总是等于本地已下载文件数量
- 更像“源站总数量”或“可获取总量”

说明：

- 后续需要明确这个字段的真正含义

### 6.7 `similar` 当前更像内容摘要，而不是站内关系对象

当前发现：

- `similar[]` 目前只有：
  - `title`
  - `year`
  - `rating`
- 当前没有稳定的：
  - `id`
  - `poster`

说明：

- 这意味着它目前更适合用于内容参考或早期展示
- 若未来详情页右栏要稳定跳转到站内详情页，后续需要考虑是否补站内关联标识

## 7. 当前对前台的支撑情况

### 7.1 详情页

当前 `data.json` 已经能够较好支撑电影详情页的主要结构：

- 头部基础信息
- 详情介绍
- 演职员
- 精彩影评
- 视频
- 图片
- 音乐
- 外部来源

说明：

- 详情页当前不是“完全缺字段”状态
- 它更多是“可以用，但部分字段还需规范统一”

### 7.2 列表页与首页

当前 `data.json` 也已经具备支撑列表页和首页的基础能力，因为它已经包含：

- 标题
- 原名
- 年份
- 海报
- 类型
- 地区
- 导演
- 评分原始数据

但说明如下：

- 列表页和首页不会直接使用全量字段
- 它们更适合从作品级 `data.json` 中提取所需字段
- 这一点不代表作品 `data.json` 不够用，而是说明页面层应使用“字段子集”

## 8. 当前不建议做的事

基于现状审计，当前不建议：

- 因为前台页面需求，就把大量站点级配置塞入每个作品的 `data.json`
- 贸然重写现有电影 `data.json` 全部字段命名
- 在没有确认现有工作流影响前，推翻 `movie-entry-workflow` 已经形成的结构

## 9. 当前建议的下一步

完成本次现状审计后，下一步最合理的是继续讨论第 11 部分：

- 正式定义电影 `data.json` 的字段规范

建议讨论顺序：

1. 哪些字段是必需字段
2. 哪些字段是可选字段
3. 哪些字段命名需要统一
4. 哪些字段适合作为派生字段保留在页面聚合层，而不是作品层

## 10. 与 movie-entry-workflow 的关系

当前电影 `data.json` 并不是单纯为了前台而存在，它同时是现有 `movie-entry-workflow` 的核心产物。

这意味着：

- 不能只从前台展示角度看待字段设计
- 需要同时考虑录入脚本、字段映射、`index.md` 生成模板和未来批量录入成本
- 因此后续对 schema 的处理原则应是：
  - 尽量保持顶层结构稳定
  - 尽量减少破坏性改名
  - 优先统一少量明显不一致的字段
  - 明确哪些字段属于前台派生需求，而不是作品原始数据必须承担的职责

## 11. 本次审计的结论一句话版

当前电影 `data.json` 已经基本够用，重点不是大改，而是：

- 先承认现有事实标准
- 再补清必填/可选边界
- 再局部统一少量不一致字段
