# 书籍数据字段映射文档

本文档记录书籍数据字段与数据库表结构的对应关系，用于数据导入时参考。

---

## 一、数据库表结构概览

| 表名 | 职责 |
|------|------|
| `books` | 书籍主表 |
| `book_series` | 书籍系列表 |
| `person` | 人物主表（作者、译者等，复用） |
| `book_person` | 书籍与人物关系表 |
| `category` | 词项表（类型、标签，复用） |
| `book_category` | 书籍与词项关联表 |

---

## 二、`books` 表字段映射

### 2.1 普通字段

| 业务字段 | 数据库字段 | 类型 | 来源优先级 | 示例值 |
|----------|-----------|------|-----------|--------|
| 书籍ID | `id` | TEXT | 系统生成 | `0200000001` |
| 书名(中文) | `title` | TEXT | 豆瓣 | `三体` |
| 原名 | `title_original` | TEXT | OpenLibrary > 豆瓣 | `The Three-Body Problem` |
| 别名 | `other_titles` | TEXT | 豆瓣 + OpenLibrary（JSON数组） | `["三体Ⅰ"]` |
| ISBN | `isbn` | TEXT | 豆瓣 > OpenLibrary | `9787536692930` |
| 出版年份 | `year` | INTEGER | 豆瓣 > OpenLibrary | `2008` |
| 作者国家 | `country` | TEXT | Wikipedia > 豆瓣 | `中国` |
| 语言 | `language` | TEXT | 豆瓣 | `简体中文` |
| 字数 | `word_count` | INTEGER | 百度百科 | `880000` |
| 出版社 | `publisher` | TEXT | 豆瓣 | `重庆出版社` |
| 内容简介 | `summary` | TEXT | 豆瓣 > OpenLibrary | `文化大革命如火如荼...` |
| 名句摘录 | `quotes` | TEXT | Wikipedia（JSON数组） | `[{"text": "..."}]` |
| 所属系列ID | `series_id` | TEXT | 豆瓣 | `0299000001` |
| 系列内序号 | `series_order` | INTEGER | 豆瓣 | `1` |
| 评分 | `scores` | TEXT | 各来源（JSON对象） | `{"douban": 9.3}` |
| 外部来源 | `external_source` | TEXT | 各来源（JSON数组） | `[{"name": "豆瓣", ...}]` |
| 封面 | `images` | TEXT | 豆瓣 > OpenLibrary（JSON对象） | `{"cover": "..."}` |
| 书评 | `reviews` | TEXT | 豆瓣（JSON数组） | `[{"author": "...", ...}]` |
| 相关书籍 | `related` | TEXT | 豆瓣（JSON对象） | `{"similar": [...]}` |
| 状态 | `status` | TEXT | 固定值 | `draft`/`published` |

---

## 三、`book_series` 表字段映射

| 业务字段 | 数据库字段 | 类型 | 说明 |
|----------|-----------|------|------|
| 系列ID | `id` | TEXT | 格式：0299NNNNNN |
| 系列名 | `name` | TEXT | 系列名称 |
| 原名 | `name_original` | TEXT | 英文名 |
| 书籍数量 | `book_count` | INTEGER | 系列内书籍数 |
| 系列简介 | `summary` | TEXT | 系列介绍 |
| 系列封面 | `images` | TEXT | JSON对象 |
| 状态 | `status` | TEXT | draft/published/archived |

---

## 四、`book_person` 表字段映射

| 业务字段 | 数据库字段 | 类型 | 说明 |
|----------|-----------|------|------|
| 书籍ID | `book_id` | TEXT | 关联 `books.id` |
| 人物ID | `person_id` | INTEGER | 关联 `person.id` |
| 角色 | `role` | TEXT | `author` / `translator` |
| 排序 | `order` | INTEGER | 显示顺序 |
| 是否主要 | `is_primary` | BOOLEAN | 主作者标记 |

### 角色映射表

| 角色 | `role` 值 |
|------|----------|
| 作者 | `author` |
| 译者 | `translator` |

---

## 五、`person` 表字段映射（复用）

| 业务字段 | 数据库字段 | 类型 | 来源优先级 |
|----------|-----------|------|-----------|
| 人物名(中文) | `name` | TEXT | 豆瓣 > OpenLibrary |
| 人物名(英文) | `name_en` | TEXT | OpenLibrary > 豆瓣 |
| 人物头像 | `avatar_path` | TEXT | OpenLibrary（优先） |
| 人物编码 | `person_id` | TEXT | 系统生成，格式 `p000001` |
| 人物详情页链接 | `profile_link` | TEXT | OpenLibrary > 豆瓣 |
| 作者简介 | `intro` | TEXT | 百度百科 > Wikipedia |

---

## 六、JSON 字段格式规范

### 6.1 `scores`（评分）

```json
{
  "avg": 8.9,
  "douban": 9.3,
  "openlibrary": 8.4
}
```

说明：
- `avg`：综合评分（有值评分的平均值）
- `douban`：豆瓣评分（10分制）
- `openlibrary`：OpenLibrary评分（已转换为10分制）

### 6.2 `external_source`（外部来源）

```json
[
  { "name": "豆瓣", "id": "2567638", "link": "https://book.douban.com/subject/2567638/" },
  { "name": "OpenLibrary", "id": "OL123456M", "link": "https://openlibrary.org/works/OL123456M" },
  { "name": "ISBN", "id": "9787536692930", "link": null },
  { "name": "百度百科", "id": "三体", "link": "https://baike.baidu.com/item/三体" }
]
```

### 6.3 `images`（封面）

```json
{
  "cover": "cover-main.jpg",
  "covers": ["cover-002.jpg", "cover-003.jpg"],
  "assetDir": "book/0200000001"
}
```

### 6.4 `reviews`（书评）

```json
[
  {
    "author": "读者A",
    "source": "豆瓣短评",
    "date": "2024-01-01",
    "content": "书评内容...",
    "rating": "5",
    "votes": 100,
    "url": null,
    "title": null
  },
  {
    "author": "读者B",
    "source": "豆瓣长评",
    "date": "2024-01-02",
    "content": "长评内容...",
    "url": "https://book.douban.com/review/123456/",
    "title": "三体读后感"
  }
]
```

数量要求：每源严格 20 条

### 6.5 `related`（相关书籍）

```json
{
  "series": [
    { "title": "三体Ⅱ·黑暗森林", "year": 2008, "rating": 9.3, "bookId": "0200000002" }
  ],
  "similar": [
    { "title": "基地", "year": 1951, "rating": 9.0, "bookId": "0200000050" }
  ],
  "sameAuthor": [
    { "title": "球状闪电", "year": 2005, "rating": 8.6, "bookId": "0200000100" }
  ]
}
```

### 6.6 `quotes`（名句）

```json
[
  { "text": "给岁月以文明，而不是给文明以岁月。", "source": "三体" }
]
```

---

## 七、字段冲突处理规则

| 字段 | 冲突处理 |
|------|----------|
| `title` | 豆瓣优先 |
| `title_original` | OpenLibrary 优先 |
| `year` | 豆瓣优先 |
| `summary` | 豆瓣优先，OpenLibrary 补充 |
| `word_count` | 百度百科优先 |
| `country` | Wikipedia 优先 |
| 评分 | 各来源独立存储，不合并 |

---

## 八、数据来源汇总

| 来源 | 提供数据 | 爬取方式 | 优先级 |
|------|----------|----------|--------|
| 豆瓣读书 | 基本信息、评分、书评、封面、标签、系列 | Playwright | 最高 |
| OpenLibrary | 英文信息、作者、封面、ISBN | REST API | 高 |
| Goodreads | 英文评分、获奖、系列、书评 | Playwright | 高 |
| 当当网 | 字数、获奖、系列、简介 | Playwright | 中 |
| 百度百科 | 作者简介、字数、名句 | Playwright | 中 |
| Wikipedia | 获奖、经典语录、国家 | Playwright | 低 |
| 中国图书网 | 字数补充、出版社详情 | Playwright | 低 |

---

## 九、各来源字段覆盖

| 字段 | 豆瓣 | OpenLibrary | Goodreads | 当当网 | 百度百科 | Wikipedia | 中国图书网 |
|------|:----:|:-----------:|:---------:|:------:|:--------:|:---------:|:----------:|
| 标题 | ✅ | ✅ | ✅ | ✅ | ✅ | - | - |
| 原名 | ✅ | ✅ | ✅ | - | - | - | - |
| 作者 | ✅ | ✅ | ✅ | ✅ | ✅ | - | - |
| 译者 | ✅ | - | - | ✅ | - | - | - |
| ISBN | ✅ | ✅ | ✅ | ✅ | - | - | ✅ |
| 出版社 | ✅ | ✅ | - | ✅ | ✅ | - | ✅ |
| 出版日期 | ✅ | ✅ | ✅ | ✅ | - | - | ✅ |
| 页数 | ✅ | ✅ | - | ✅ | - | - | ✅ |
| 字数 | - | - | - | ✅ | ✅ | - | ✅ |
| 评分 | ✅ | ✅ | ✅ | - | - | - | - |
| 简介 | ✅ | ✅ | ✅ | ✅ | ✅ | - | - |
| 作者简介 | - | ✅ | ✅ | - | ✅ | ✅ | - |
| 封面 | ✅ | ✅ | ✅ | ✅ | - | - | ✅ |
| 标签 | ✅ | ✅ | ✅ | - | - | - | - |
| 书评 | ✅ | - | ✅ | - | - | - | - |
| 获奖 | - | - | ✅ | ✅ | ✅ | ✅ | - |
| 系列 | ✅ | ✅ | ✅ | ✅ | - | - | - |
| 名句 | - | - | - | - | ✅ | ✅ | - |

---

## 十、数据导入注意事项

1. **ID 生成规则**：`0200NNNNNN`（02=书模块，00=无子模块）
2. **系列ID规则**：`0299NNNNNN`（02=书模块，99=系列）
3. **人物编码生成规则**：`p{NNNNNN}`（6位序号）
4. **封面存储路径**：`.local/assets/book/{id}/`
5. **人物头像存储路径**：`.local/assets/people/{person_id}-avatar.jpg`
6. **JSON 字段解析**：使用 SQLite JSON 函数或应用层解析
7. **作者去重**：按 `name` + `name_en` 去重

---

---

## 十一、评分换算规则

| 来源 | 原始分数范围 | 换算公式 |
|------|-------------|----------|
| 豆瓣 | 0-10 | 直接使用 |
| OpenLibrary | 0-5 | `value = raw * 2` |
| Goodreads | 0-5 | `value = raw * 2` |

---

## 十二、数据来源标识

| 来源 | 标识符 |
|------|--------|
| 豆瓣读书 | `douban` |
| OpenLibrary | `openlibrary` |
| Goodreads | `goodreads` |
| 当当网 | `dangdang` |
| 百度百科 | `baike` |
| Wikipedia | `wikipedia` |
| 中国图书网 | `bookchina` |

---

文档版本：v3.0
更新日期：2026-05-10
基于：新书籍表设计（books/book_series/book_person/book_category）
新增：Goodreads、当当网、中国图书网数据源
