# 书籍数据设计

本文档记录数据库字段设计、字段映射关系、JSON 格式规范。

---

## 一、数据库表结构

| 表名 | 职责 |
|------|------|
| `books` | 书籍主表 |
| `book_series` | 书籍系列表 |
| `person` | 人物主表（作者、译者等，复用） |
| `book_person` | 书籍与人物关系表 |
| `category` | 词项表（类型、标签，复用） |
| `book_category` | 书籍与词项关联表 |

---

## 二、books 表字段

### 2.1 字段列表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | TEXT | 书籍 ID，格式 `0200NNNNNN` |
| `title` | TEXT | 中文书名 |
| `title_original` | TEXT | 原名（英文/源语言） |
| `other_titles` | TEXT | 别名 JSON 数组 |
| `isbn` | TEXT | ISBN（唯一） |
| `year` | INTEGER | 出版年份 |
| `country` | TEXT | 作者国家 |
| `language` | TEXT | 语言 |
| `word_count` | INTEGER | 字数 |
| `publisher` | TEXT | 出版社 |
| `summary` | TEXT | 内容简介 |
| `quotes` | TEXT | 名句摘录 JSON 数组 |
| `series_id` | TEXT | 所属系列 ID |
| `series_order` | INTEGER | 系列内序号 |
| `scores` | TEXT | 评分 JSON（10 分制） |
| `external_source` | TEXT | 外部来源 JSON |
| `images` | TEXT | 封面 JSON |
| `reviews` | TEXT | 书评 JSON（每源 20 条） |
| `related` | TEXT | 相关书籍 JSON |
| `status` | TEXT | 状态（draft/published/archived） |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

### 2.2 字段来源优先级

| 业务字段 | 数据库字段 | 来源优先级 |
|----------|-----------|-----------|
| 书名(中文) | `title` | 豆瓣 |
| 原名 | `title_original` | OpenLibrary > 豆瓣 |
| 别名 | `other_titles` | 豆瓣 + OpenLibrary |
| ISBN | `isbn` | 豆瓣 > OpenLibrary |
| 出版年份 | `year` | 豆瓣 > OpenLibrary |
| 作者国家 | `country` | Wikipedia > 豆瓣 |
| 语言 | `language` | 豆瓣 |
| 字数 | `word_count` | 百度百科 > 当当网 |
| 出版社 | `publisher` | 豆瓣 > 当当网 |
| 内容简介 | `summary` | 豆瓣 > OpenLibrary |
| 名句摘录 | `quotes` | Wikipedia > 百度百科 |

---

## 三、关联表字段

### 3.1 book_series 表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | TEXT | 系列 ID，格式 `0299NNNNNN` |
| `name` | TEXT | 系列名 |
| `name_original` | TEXT | 原名 |
| `book_count` | INTEGER | 书籍数量 |
| `summary` | TEXT | 系列简介 |
| `images` | TEXT | 系列封面 JSON |
| `status` | TEXT | 状态 |

### 3.2 book_person 表

| 字段 | 类型 | 说明 |
|------|------|------|
| `book_id` | TEXT | 书籍 ID |
| `person_id` | INTEGER | 人物 ID（关联 person 表） |
| `role` | TEXT | 角色（author/translator） |
| `order` | INTEGER | 排序 |
| `is_primary` | BOOLEAN | 是否主要 |

### 3.3 person 表

| 字段 | 类型 | 说明 |
|------|------|------|
| `person_id` | TEXT | 人物编码，格式 `p000001` |
| `name` | TEXT | 中文名 |
| `name_en` | TEXT | 英文名 |
| `avatar_path` | TEXT | 头像路径 |
| `profile_link` | TEXT | 外链 |
| `intro` | TEXT | 简介 |

---

## 四、JSON 字段格式

### 4.1 scores（评分）

```json
{
  "avg": 8.9,
  "douban": 9.3,
  "openlibrary": 8.4,
  "goodreads": 8.2
}
```

- `avg`：综合评分（有值评分的平均值）
- 各平台评分均为 10 分制

### 4.2 external_source（外部来源）

```json
[
  { "name": "豆瓣", "id": "2567638", "link": "https://book.douban.com/subject/2567638/" },
  { "name": "OpenLibrary", "id": "OL123456M", "link": "https://openlibrary.org/works/OL123456M" },
  { "name": "ISBN", "id": "9787536692930", "link": null },
  { "name": "百度百科", "id": "三体", "link": "https://baike.baidu.com/item/三体" }
]
```

### 4.3 images（封面）

```json
{
  "cover": "cover-main.jpg",
  "covers": ["cover-002.jpg", "cover-003.jpg"],
  "assetDir": "book/0200000001"
}
```

- `cover`：主封面文件名
- `covers`：补充封面列表
- `assetDir`：资源目录路径

### 4.4 reviews（书评）

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

### 4.5 related（相关书籍）

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

### 4.6 quotes（名句）

```json
[
  { "text": "给岁月以文明，而不是给文明以岁月。", "source": "三体" }
]
```

---

## 五、数据来源字段覆盖

| 字段 | 豆瓣 | OpenLibrary | Goodreads | 当当网 | 百度百科 | Wikipedia |
|------|:----:|:-----------:|:---------:|:------:|:--------:|:---------:|
| 标题 | ✅ | ✅ | ✅ | ✅ | ✅ | - |
| 原名 | ✅ | ✅ | ✅ | - | - | - |
| 作者 | ✅ | ✅ | ✅ | ✅ | ✅ | - |
| 译者 | ✅ | - | - | ✅ | - | - |
| ISBN | ✅ | ✅ | ✅ | ✅ | - | - |
| 出版社 | ✅ | ✅ | - | ✅ | ✅ | - |
| 出版日期 | ✅ | ✅ | ✅ | ✅ | - | - |
| 页数 | ✅ | ✅ | - | ✅ | - | - |
| 字数 | - | - | - | ✅ | ✅ | - |
| 评分 | ✅ | ✅ | ✅ | - | - | - |
| 简介 | ✅ | ✅ | ✅ | ✅ | ✅ | - |
| 封面 | ✅ | ✅ | ✅ | ✅ | - | - |
| 标签 | ✅ | ✅ | ✅ | - | - | - |
| 书评 | ✅ | - | ✅ | - | - | - |
| 获奖 | - | - | ✅ | ✅ | ✅ | ✅ |
| 系列 | ✅ | ✅ | ✅ | ✅ | - | - |
| 名句 | - | - | - | - | ✅ | ✅ |

---

## 六、评分换算规则

| 来源 | 原始分数范围 | 换算公式 |
|------|-------------|----------|
| 豆瓣 | 0-10 | 直接使用 |
| OpenLibrary | 0-5 | `value = raw * 2` |
| Goodreads | 0-5 | `value = raw * 2` |

---

## 七、数据来源标识

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

## 八、ID 生成规则

| 类型 | 格式 | 示例 |
|------|------|------|
| 书籍 ID | `0200NNNNNN` | `0200000001` |
| 系列 ID | `0299NNNNNN` | `0299000001` |
| 人物编码 | `pNNNNNN` | `p000001` |

---

## 九、存储路径

### 9.1 book-ingest 内部路径（临时存储）

| 类型 | 路径 |
|------|------|
| 原始数据 | `data/raw/{book_id}/{source}.json` |
| 合并数据 | `data/staging/{book_id}.json` |
| 书籍封面 | `data/assets/{book_id}/cover-main.jpg` |

### 9.2 最终存储路径（录入数据库后）

| 类型 | 路径 |
|------|------|
| 书籍封面 | `.local/assets/book/{book_id}/` |
| 人物头像 | `.local/assets/people/{person_id}-avatar.jpg` |

**说明**：封面在 book-ingest 内临时存储，导出到 generated 或发布时复制到 `.local/assets/book/`

---

**最后更新**：2026-05-12
