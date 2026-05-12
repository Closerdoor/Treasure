# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Language Preference

请使用中文与用户对话。

## 项目概述

这是一个"精选型个人收藏馆"网站，用于收录影视、书籍、音乐、游戏等内容。

**核心理念**：这不是全量资料库，而是"馆长筛选"型收藏站。只收录经过馆长筛选的作品，作品资料以公开社区信息和标准元数据为主。

**当前状态**：数据库已投入使用，已导入豆瓣 Top 250 电影数据（250 部），演职员数据完整（11,546 人）。

---

## 数据库

### 数据库文件

```
.local/treasure.db
```

### Prisma Schema

```
prisma/schema.prisma
```

### 当前数据量

| 表 | 记录数 | 说明 |
|------|--------|------|
| `works` | 250 | 豆瓣 Top 250 电影 |
| `person` | 11546 | 导演/编剧/演员 |
| `category` | 27 | 电影类型 |
| `work_person` | 5660 | 演职关系 |
| `work_category` | 698 | 类型关联 |

### 表名规则

- 表名使用单数形式：`person`（而非 `people`）、`category`（而非 `categories`）
- 关联表命名：`{主表}_{关联表}`，如 `work_person`、`work_category`

### 常用命令

```bash
# 查看 Prisma Schema
cat prisma/schema.prisma

# 查看表结构（带注释）
node tools/db/view-schema.mjs Work
node tools/db/view-schema.mjs Person

# 导出数据到 Astro 站点
node tools/db/export-generated.mjs

# 更新备份
node tools/db/update-backup.mjs

# 查看数据统计
node tools/db/check-counts.mjs
```

---

## 静态资源

### 作品图片

```
.local/assets/video/movie/{id}/
├── poster-main.jpg
└── ...
```

### 人物头像

```
.local/assets/people/tmdb-{id}-avatar.jpg
```

**头像覆盖率**：7,604 人有头像（约 66%），其余人物在 TMDB 无 profile_path。

---

## 数据导出

### 导出命令

```bash
node tools/db/export-generated.mjs
```

### 导出产物

- `generated/entries/video/movie/*.json` - 作品详情（250 个）
- `generated/indexes/video-movie.json` - 电影列表索引
- `generated/persons.json` - 人物数据（11,546 人）
- `site/public/assets/` - 图片资源（作品图片 + 人物头像）

---

## 架构设计

两层系统：

1. **展示站点**（公开）
   - Astro 静态生成
   - 部署到 GitHub Pages
   - 内容来自 `generated/` 目录的 JSON 文件
   - 评论系统使用 Giscus

2. **本地内容工坊**（私有）
   - 内容录入、搜索、补全、确认、整理的工具链
   - SQLite 本地数据库保存草稿、候选结果、待确认数据
   - 支持单条口头录入和 YAML 批量导入
   - 处理搜索匹配、人工确认、自动补全流程

## 模块结构

四个一级模块，各有子模块：

| 模块 | 编号 | 子模块 |
|------|------|--------|
| 影视 | 01 | 电影、电视剧、动漫、纪录片、短片 |
| 书 | 02 | 网络小说、经典文学、名著、散文随笔、漫画 |
| 音乐 | 03 | 专辑、单曲、原声带、演唱会现场、音乐人专题 |
| 游戏 | 04 | 单机游戏、独立游戏、网游、手游、主机游戏 |

## ID 系统

内容 ID 格式：`MMSSNNNNNN`
- `MM`：一级模块编号（01-04）
- `SS`：子模块编号（01-05）
- `NNNNNN`：该子模块下的递增序号

示例：`0101000001` = 影视/电影/第 1 条

## URL 结构

`/{module}/{submodule}/{id}`

示例：
- `/video/movie/0101000001`
- `/book/classic/02020008`
- `/music/single/03020015`

---

## Codex 工作规范

### 规则 1：关键决策必须确认

当涉及以下情况时，必须向用户确认：
- 限制数据范围（如"只下载前N个"）
- 跳过某些数据源
- 降级处理（如"先用低质量数据"）
- 任何可能影响数据完整性的决策

### 规则 2：进度汇报必须量化

汇报完成状态时，必须包含：
- 数据总量
- 实际完成量
- 覆盖率/完成率
- 未完成的原因（如有）

示例：
```
❌ 错误汇报：演职员数据已全部导入
✅ 正确汇报：演职员数据已导入（11,546人），头像已下载（7,604人，约66%）
```

### 规则 3：脚本限制必须标注并汇报

如果脚本中有任何限制性逻辑（如 `[:10]`），必须在代码注释中明确说明，并在运行前向用户汇报。