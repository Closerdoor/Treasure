# Status

> Purpose: 记录当前阶段的实际进展、已完成内容、下一步与风险。
> Status: active
> Scope: 当前阶段、已完成、当前待办、下一步、风险与阻塞
> Out of scope: 长期设计正文、细字段规范、完整 workflow 教程
> Update triggers: 阶段推进、关键任务完成、下一步变化、风险变化
> Priority: 5

## 当前阶段

当前阶段是：

- 影视模块电影样板前台第一阶段已落地
- 首页 / 列表页 / 详情页的信息结构已完成首轮确认
- 当前已完成电影 DB-first 数据链路切换，并已进入批量录入前的 workflow 收口阶段

## 已完成内容

### 产品与文档方向

- 项目定位已统一为“精选型个人收藏馆”
- 前台与本地工坊的边界已明确
- 首页 / 影视列表页 / 电影详情页的主结构已确认
- 深色 / 浅色双主题方向已确认
- 当前主文档体系已重建为 `PROJECT / ARCHITECTURE / CONTRACTS / UI-GUIDE / STATUS`
- 旧 numbered 设计文档已归档到 `docs/archive/2026-05-doc-reset/`

### 前台样板落地

- Astro 前台工程已搭建完成，并已具备静态构建能力
- 已落地页面：`/`、`/video`、`/video/movie/[id]`、`/about`、`/search`
- 首页已具备首轮样板结构，但首页视觉细节后续再根据内容量继续优化
- 影视列表页已完成 `卡片 / 列表` 双视图与分页、筛选区、主题切换联动
- 电影详情页已完成顶部信息区、标题索引、sticky 侧栏、媒体 rail、外部来源等主要结构
- 列表页与详情页当前以“信息结构稳定、后续仅做细节微调”为阶段结论

### 数据与 workflow

- 已统一 `synopsis` / `story` / `reviews` 的职责
- 已统一主海报、补充海报、图片总量等规则
- 已统一部分 schema 残留字段命名
- 已收紧 `story` 在已上映 / 未上映作品中的使用边界
- 已完成 SQLite 作为电影结构化主源的导入与导出链路
- 已完成 `generated/entries.json` 驱动前台页面的切换
- 已完成旧 `content/video/movie/*/images` 到 `site/public/assets/` 的资源迁移
- 已完成旧 `data.json` 到 `.local/staging/video/movie/*.json` 的过渡迁移
- 资源检查已通过：当前 `generated/entries.json` 引用资源缺失为 0

### 真实条目验证

当前已录入并对齐的电影条目共 6 部：

- `0101000001` 肖申克的救赎
- `0101000002` 迈克尔·杰克逊：巨星之路
- `0101000003` 阿甘正传
- `0101000004` 霸王别姬
- `0101000005` 肖申克的救赎1
- `0101000006` 星际穿越

已确认：

- 6 部电影已经可以通过 `.local/staging -> SQLite -> generated -> Astro` 完成闭环
- 当前前台构建不再依赖 `content/video/movie/*/data.json`
- movie-entry-workflow 已重写为 DB-first 方向
- `0101000005` 与 `0101000006` 已达到当前高标准样板要求，可作为后续批量录入的质量基线

### 当前高标准样板基线

- `reviews` 当前按 `author / source / date / content / url / title` 统一结构保存
- 已上映电影的高标准评论覆盖基线为：`豆瓣长评 10 + 豆瓣短评 10 + TMDB 10 + 烂番茄 10`
- 主海报优先使用 `TMDB` 高清图
- 评分只记录评分值，不再记录票数或评价人数
- `country` 仅保留单值，并按最早真实公映地区推断；电影节 / 影展 / 首映不作为首发地区依据
- `story.note` 不再进入数据库主字段

## 当前待办

- 收口旧 `content/video/movie/*` 目录的退役与清理策略
- 完善电影批量 intake workflow，使其支持清库后的从头重跑
- 为后续豆瓣电影 TOP250 批量录入补齐去重、续跑和质量报告能力
- 将文档基线与批量 intake 实现同步到“可清库重跑”的状态

## 当前激活任务

当前正在处理：

- 把电影样板从“样板特判”收口为可重复执行的通用 intake 流程
- 为后续清空数据库后重新全量导入做准备
- 持续把 workflow 的阶段性结论回写文档，避免规则漂移

本轮变更要求同步检查：

- `PROJECT.md`
- `CONTRACTS.md`
- `UI-GUIDE.md`
- `STATUS.md`

## 下一步建议

当前建议优先进入以下其一：

1. 完善电影批量 intake workflow，准备豆瓣电影 TOP250 录入
2. 清理旧 `content/video/movie/*` 输入目录，正式完成电影模块的退役切换
3. 准备搜索与索引层，为未来 `/search` 的真实落地做数据基础

## 风险与阻塞

当前无阻塞性问题，但需注意：

- 如果后续继续调整数据字段，必须同步更新 workflow 契约文档
- 如果 UI 结构变化，必须同步更新 `UI-GUIDE.md` 与 `CONTRACTS.md`
- 旧 `content/video/movie/*` 目录仍在仓库中，若要正式删除，必须先完成一次人工确认
- `STATUS.md` 必须保持简洁，避免写成会话流水账

## 最近关键变更

- 完成 6 部电影的 `.local/staging -> SQLite -> generated -> Astro` 闭环验证
- 完成《星际穿越》与《肖申克的救赎1》的高标准评论补齐与前台展示对齐
- 完成当前电影录入基线文档更新并单独提交
- 完成 intake 脚本首轮收口：支持 `new-flow/staging` 双输出模式、写盘前结构校验、`created/skipped` 摘要
- 修复 `0101000001` 缺失 `source.json`
- 修复 raw 报告和 raw JSON 中残留的旧短评语义
- 完成当前主文档体系重建与旧文档归档
- 补回新主文档中遗漏的 ID、标签契约、搜索范围与详情页展示规则
- 进一步补齐 `similar` / `series` / 评分算法 / 卡片字段集 / 文档职责边界
- 明确 `docs/` 为唯一规范来源，并补齐页面路由与未落地模块交互规则
- 完成 Astro 前台样板落地，并接通首页 / 列表页 / 详情页 / About 的静态展示链路
- 完成影视列表页双视图、筛选区、分页与主题切换的首轮实现
- 完成电影详情页顶部信息区、标题索引、媒体 rail、右侧栏与浅色主题扁平化微调
- 精简本地字体资源并确认当前前台构建与测试通过
- 完成电影模块 `SQLite -> generated JSON -> Astro` 的 DB-first 切换
- 完成共享人物头像与作品资源迁移到 `site/public/assets/`
