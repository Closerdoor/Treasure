# AI Index

> 给 AI / Codex / Claude 使用的全局导航。目标是快速定位上下文，不替代详细文档。

## 先读这份

如果你刚进入项目，只读三步：

1. 读本文件，确定要找哪类信息。
2. 读 `STATUS.md`，确认当前真实状态和已知风险。
3. 按下面的任务类型跳转到对应文档。

## 当前一句话

Treasure 是一个精选型个人收藏馆。当前主线是：

```text
.local/treasure.db
  -> tools/db/export-generated.mjs
  -> generated/
  -> site/
  -> GitHub Pages
```

前台 Astro 不直接读数据库，只读 `generated/` 和 `site/public/assets/`。

## 当前事实快照

最近核验时间：2026-05-12

```text
电影：250 / 250 已导出
书籍：3 条 draft，尚未接入前台
Astro 构建：254 页面成功
主海报：249 / 250 存在
人物头像：9072 / 12999 存在，约 69.8%
```

已知问题只记录，尚未修复：

- `0101000178`《绿里奇迹》缺主海报。
- `0101000001`《肖申克的救赎》部分图片字段混入 TMDB 外链对象。
- 人物头像仍有 3927 次引用缺实体文件。

## 按任务找文档

| 你要做什么 | 先读 |
|---|---|
| 快速了解项目 | `PROJECT.md`、`STATUS.md` |
| 判断当前进度 | `STATUS.md` |
| 理解目录结构 | `ARCHITECTURE.md` |
| 跑导出/构建流程 | `WORKFLOW.md` |
| 改 generated 或资源路径 | `GENERATED-DATA.md`、`CONTRACTS.md` |
| 改数据库 / Prisma | `DATABASE.md`、`prisma/schema.prisma` |
| 改前台页面 | `ARCHITECTURE.md`、`CONTRACTS.md`、`UI-GUIDE.md` |
| 接入书籍模块 | `WORKFLOW.md`、`DATABASE.md`、`GENERATED-DATA.md` |
| 判断是否要更新文档 | `DOCS-MAINTENANCE.md` |

## 关键目录

```text
.local/                  私有数据库、资源、缓存，不进 Git
prisma/                  Prisma schema
tools/db/                稳定数据库/导出脚本
temp-script/             实验脚本和调试产物
generated/               数据库导出的前台 JSON
site/                    Astro 静态站
site/public/assets/      前台可发布静态资源
content/                 历史内容目录，目前不是正式前台数据源
docs/                    当前项目文档
```

## 常用命令

```bash
# 导出数据库到 generated/
node tools/db/export-generated.mjs

# 查看数据库统计
node tools/db/check-counts.mjs

# 同步资源并导出数据
cd site
npm.cmd run sync

# 构建 Astro 静态站
cd site
npm.cmd run build
```

Windows PowerShell 下优先使用 `npm.cmd`，避免执行策略拦截 `npm.ps1`。

## 不要误读

- 不要把 `temp-script/` 当成稳定工作流。
- 不要把 `content/` 当成当前前台正式数据源。
- 不要把 `docs/archive/` 当成当前规范。
- 不要只根据旧截图或旧生成文件判断当前状态。
- 不要在未确认数据完整性时做批量删除、跳过数据源、限制数据范围等决定。

## 当前推荐下一步

优先新增：

```text
tools/db/check-generated-integrity.mjs
```

把当前手动校验固化为脚本，输出：

- 数据库总量
- generated 完成量
- 资源引用总量
- 资源存在量
- 覆盖率
- 缺失样本
- 是否阻断发布
