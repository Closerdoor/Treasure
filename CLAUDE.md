# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language Preference

请使用中文与用户对话。

## 项目概述

这是一个"精选型个人收藏馆"网站，用于收录影视、书籍、音乐、游戏等内容。项目目前处于设计阶段，仅有设计文档，尚未开始编码。

**核心理念**：这不是全量资料库，而是"馆长筛选"型收藏站。只收录经过馆长筛选的作品，作品资料以公开社区信息和标准元数据为主。

## 架构设计

两层系统：

1. **展示站点**（公开）
   - Astro 静态生成
   - 部署到 GitHub Pages
   - 内容来自仓库内的 Markdown 文件
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
- `/video/movie/01010001`
- `/book/classic/02020008`
- `/music/single/03020015`

## 内容存储

- **格式**：Markdown 文件 + YAML frontmatter
- **位置**：`content/{module}/{submodule}/*.md`
- **命名**：`{id}.md`（如 `01010001.md`）
- **图片**：`public/assets/{module}/{submodule}/{id}/`

## 构建产物

Astro 构建时生成 JSON 索引：
- `generated/entries.json`
- `generated/modules/{module}.json`
- `generated/submodules/{module}-{submodule}.json`
- `generated/tags.json`
- `generated/search-index.json`
- `generated/recent.json`

## UI 方向

根据设计文档：
- 深色主题（"深色资料馆"）配合极简结构
- 资料馆/档案馆气质，不是博客风格
- 强调策展和目录浏览
- 封面/海报驱动的视觉呈现
- 结构化信息展示，而非大段长评

## V1 范围

第一版以影视 > 电影为样板优先落地：
- 首页
- 影视模块首页
- 电影列表页
- 电影详情页
- 标签聚合页
- 关于页

## 设计文档

设计文档位于 `docs/`：
- `01-information-architecture.md` - 总体架构、模块划分、ID/URL 规则
- `02-module-template-draft.md` - 各模块模板设计
- `03-data-pipeline-and-content-model.md` - 内容录入流程、数据模型
- `04-ui-style-directions.md` - UI 风格方案与建议
- `05-wireframes-home-and-video.md` - 首页与影视模块线框图