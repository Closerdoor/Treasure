# Database

> Purpose: 记录当前 SQLite / Prisma 数据库结构、数据量和表职责。
> Status: active
> Scope: 数据库文件、Prisma schema、核心表、当前数据统计、模块接入状态
> Out of scope: 完整迁移历史、爬虫原始字段、前台 UI 展示规则
> Update triggers: schema 变化、表新增/删除/重命名、记录量显著变化、新模块正式入库
> Priority: 2

## 数据库定位

当前结构化主源：

```text
.local/treasure.db
```

Prisma schema：

```text
prisma/schema.prisma
```

SQLite 只服务本地内容工坊。线上 GitHub Pages 不读取数据库，只读取 `generated/` 和静态资源。

## 当前数据统计

最近核验时间：2026-05-12

| 表 | 记录数 | 说明 |
|---|---:|---|
| `works` | 250 | 电影作品，全部为 `video/movie/published` |
| `person` | 11546 | 公共人物 |
| `category` | 28 | 公共分类/标签 |
| `work_person` | 12999 | 电影演职员关系 |
| `work_category` | 698 | 电影分类关系 |
| `books` | 3 | 书籍草稿 |
| `book_series` | 0 | 书籍系列 |
| `book_person` | 5 | 书籍人物关系 |
| `book_category` | 1 | 书籍分类关系 |

## 当前模块接入状态

### 影视 / 电影

状态：已接入主链路。

```text
works
person
category
work_person
work_category
```

当前电影链路：

```text
SQLite -> tools/db/export-generated.mjs -> generated/entries/video/movie -> Astro
```

### 书籍

状态：数据库草稿阶段。

```text
books
book_series
book_person
book_category
person
category
```

当前已有 3 条 `draft` 书籍记录，但尚未正式导出到 `generated/entries/book/`，也未接入 Astro 页面。

### 音乐 / 游戏

状态：未正式建模接入。

## 表职责

### `works`

通用作品主表，当前实际承载电影数据。

关键职责：

- 作品 ID
- 模块与子模块
- 基础信息
- 简介与剧情
- 外部来源
- 图片/视频元数据
- 评论
- 评分
- 关联作品

### `person`

公共人物表。

关键职责：

- 内部人物编号 `person_id`
- 姓名
- 外部来源 ID
- 头像路径
- 人物简介

人物可被电影、书籍等多个模块复用。

### `category`

公共分类/标签表。

关键职责：

- `type`：类型，如剧情、犯罪、科幻
- `tag`：标签
- 模块作用域
- 子模块作用域

### `work_person`

电影作品与人物关系。

关键职责：

- 导演
- 编剧
- 演员
- 制片
- 角色名
- 排序
- 是否主要人员

### `work_category`

电影作品与分类/标签关系。

### `books`

书籍主表。

关键职责：

- 书籍 ID
- 书名
- ISBN
- 出版年份
- 国家/语言
- 出版社
- 简介
- 评分
- 外部来源
- 封面图片元数据
- 书评
- 相关书籍

### `book_person`

书籍与人物关系。

当前角色：

- `author`
- `translator`

### `book_category`

书籍与分类/标签关系。

## ID 规则

作品 ID 使用：

```text
MMSSNNNNNN
```

- `MM`：一级模块编号
- `SS`：子模块编号
- `NNNNNN`：递增序号

当前示例：

- `0101000001`：影视 / 电影 / 第 1 条
- `0200000001`：书籍 / 无子模块 / 第 1 条

人物 ID 使用：

```text
p000001
```

## JSON 字段策略

当前数据库采用“核心关系拆表，展示型复合信息 JSON 化”的策略。

拆表：

- 人物
- 分类/标签
- 作品-人物关系
- 作品-分类关系

JSON 字段：

- 多平台评分
- 外部来源
- 图片集合
- 视频集合
- 评论
- 关联作品
- 名言/摘录
- 原声带

## 常用命令

```bash
# 查看 Prisma schema
Get-Content prisma/schema.prisma

# 查看表结构
node tools/db/view-schema.mjs Work
node tools/db/view-schema.mjs Person

# 查看数据统计
node tools/db/check-counts.mjs

# 导出 generated
node tools/db/export-generated.mjs
```

## 维护规则

当以下内容变化时，必须更新本文件：

- 表结构变化
- 表名变化
- 新模块正式接入数据库
- 数据量发生阶段性变化
- 字段职责变化
- 数据主源策略变化
