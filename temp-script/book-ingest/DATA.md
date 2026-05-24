# 书籍数据契约

最后更新：2026-05-24

本文记录 `book-ingest` 当前 staging、数据库字段与数据源能力。书籍模块尚未接入 generated / Astro，因此这里不定义前台发布字段契约。

## 数据表

| 表 | 职责 |
|---|---|
| `books` | 书籍主表 |
| `book_series` | 书籍系列表，入库时可由 `_meta.series` 复用或创建 |
| `person` | 公共人物表，作者和译者复用 |
| `book_person` | 书籍与作者 / 译者关系 |
| `category` | 公共分类 / 标签表 |
| `book_category` | 书籍与分类 / 标签关系 |

## books 字段

| DB 字段 | staging 字段 | 说明 |
|---|---|---|
| `id` | `id` | 书籍 ID，格式 `0200NNNNNN` |
| `title` | `title` | 中文展示书名 |
| `title_original` | `titleOriginal` | 原名 / 源语言标题 |
| `other_titles` | `otherTitles` | 别名数组，入库时序列化 |
| `isbn` | `isbn` | ISBN |
| `year` | `year` | 作品首版年份，优先取百度百科首版年 |
| `country` | `country` | 作者国家或作品国家 |
| `language` | `language` | 语言 |
| `word_count` | `wordCount` | 字数 |
| `publisher` | `publisher` | 出版社 |
| `publish_date` | `publishDate` | 完整出版日期，保留来源文本 |
| `pages` | `pages` | 页数 |
| `price` | `price` | 定价，保留币种 / 来源文本 |
| `binding` | `binding` | 装帧 |
| `format` | `format` | 开本 / 版式 |
| `edition` | `edition` | 版本 / 版次 |
| `summary` | `summary` | 内容简介，优先取 Wikipedia “故事大纲” |
| `story` | `story` | 完整剧情 / 内容情节，优先取百度百科“内容情节” |
| `quotes` | `quotes` | 名句数组，入库时序列化 |
| `excerpts` | `excerpts` | 原文摘录数组，优先按豆瓣热度前 20 条取详情页原文，入库时序列化 |
| `series_id` | `seriesId` | 系列 ID，入库时由 `_meta.series` 映射 |
| `series_order` | `seriesOrder` | 系列内排序 |
| `scores` | `scores` | 多平台评分对象，入库时序列化 |
| `external_source` | `externalSource` | 外部来源数组，入库时序列化 |
| `images` | `images` | 本地封面对象，入库时序列化 |
| `reviews` | `reviews` | 评论 / 书评数组，入库时序列化 |
| `related` | `related` | 相关书籍对象，入库时序列化 |
| `status` | `status` | `draft` / `published` / `archived` |

## Staging 结构

staging 中复杂字段必须保持对象 / 数组，不能提前 JSON 字符串化。

```json
{
  "id": "0200000002",
  "title": "围城",
  "titleOriginal": "Fortress Besieged",
  "isbn": "978...",
  "scores": {
    "douban": 9.3,
    "goodreads": 8.1,
    "avg": 8.7
  },
  "images": {
    "cover": "cover-main.jpg",
    "covers": {
      "openlibrary": "covers/openlibrary.jpg",
      "goodreads": "covers/goodreads.jpg"
    },
    "assetDir": "0200000002"
  },
  "externalSource": [
    {
      "name": "豆瓣",
      "id": "1008145",
      "link": "https://book.douban.com/subject/1008145/"
    }
  ],
  "_meta": {
    "fieldSources": {
      "title": "douban",
      "summary": "wikipedia",
      "story": "baike"
    },
    "conflicts": [],
    "authors": ["钱锺书"],
    "translators": [],
    "tags": ["小说", "中国文学"],
    "subjects": [],
    "genres": [],
    "personDetails": [
      {
        "name": "钱锺书",
        "personId": "p4502389",
        "avatarPath": "people/p4502389-avatar.jpg"
      }
    ],
    "series": {
      "name": "三体三部曲",
      "source": "douban"
    },
    "seriesCandidates": []
  }
}
```

`_meta` 不直接写入 `books` 表；入库时用于生成人物、分类和关系表。

## 图片字段

采集阶段：

```text
data/assets/{book_id}/cover-main.jpg
data/assets/{book_id}/cover-001.jpg
```

入库后：

```text
.local/assets/book/{book_id}/cover-main.jpg
.local/assets/book/{book_id}/cover-001.jpg
```

`images` 示例：

```json
{
  "cover": "cover-main.jpg",
  "covers": {
    "douban_0": "covers/douban_0.jpg",
    "openlibrary": "covers/openlibrary.jpg",
    "goodreads": "covers/goodreads.jpg",
    "dangdang": "covers/dangdang.jpg",
    "wikipedia": "covers/wikipedia.jpg"
  },
  "assetDir": "0200000002"
}
```

`cover` 与 `covers` 都必须是本地文件名，不允许远程 URL。`covers` 是数据源到本地文件名的映射，用于保留多源封面并支持人工挑选主封面。

作者头像在采集阶段位于：

```text
data/assets/{book_id}/people/{person_id}-avatar.jpg
```

入库后复制到：

```text
.local/assets/book/{book_id}/people/{person_id}-avatar.jpg
```

## 评分字段

```json
{
  "douban": 9.3,
  "openlibrary": 8.4,
  "goodreads": 8.2,
  "avg": 8.6
}
```

评分换算：

| 来源 | 原始范围 | 当前规则 |
|---|---|---|
| 豆瓣 | 0-10 | 直接使用 |
| OpenLibrary | 通常 0-5 | 爬虫 / 合并层应换算到 10 分制 |
| Goodreads | 通常 0-5 | 爬虫 / 合并层应换算到 10 分制 |

## 评论字段

当前数量限制来自 `config.REVIEWS_PER_SOURCE = 20`。

```json
[
  {
    "author": "读者A",
    "source": "豆瓣短评",
    "date": "2024-01-01",
    "content": "评论内容",
    "rating": "5",
    "votes": 100,
    "url": null,
    "title": null
  }
]
```

当前不是全量评论采集。修改为全量前需要确认排序、页数和反爬风险。

## 相关书籍字段

```json
{
  "series": [
    { "title": "三体II：黑暗森林", "year": 2008, "rating": 9.3, "bookId": null }
  ],
  "similar": [
    { "title": "基地", "year": 1951, "rating": 9.0, "bookId": null }
  ],
  "sameAuthor": [
    { "title": "球状闪电", "year": 2005, "rating": 8.6, "bookId": null }
  ]
}
```

当前 `bookId` 多数为空，后续需要在更多书籍入库后做站内匹配。真正的系列关系应写入 `book_series` 与 `books.series_id`；`related.series` 只保留来源候选和展示补充。

## 数据源能力

| 字段 | 豆瓣 | OpenLibrary | 百度百科 | Wikipedia | Goodreads | 当当 | 起点 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 标题 | 主 | 补 | 补 | 补 | 补 | 补 | 补 |
| 原名 | 补 | 补 | 补 | 主 | 补 | - | - |
| 别名 | 主 | - | 补 | 补 | - | - | - |
| ISBN | 主 | 补 | - | - | 补 | 补 | - |
| 年份 | 主 | 补 | 补 | 补 | 补 | 补 | - |
| 国家 | 补 | - | 主 | 补 | - | - | - |
| 语言 | 补 | - | 主 | 补 | - | - | - |
| 字数 | - | - | 主 | - | - | 补 | 主 |
| 出版社 | 主 | 补 | 补 | 补 | 补 | 补 | - |
| 简介 | 主 | 补 | 补 | 补 | 补 | 补 | 补 |
| 评分 | 主 | 补 | - | - | 补 | - | - |
| 作者 | 主 | 补 | 补 | 补 | 补 | 补 | 主 |
| 译者 | 主 | - | - | 补 | 补 | 补 | - |
| 标签 / 主题 | 主 | 补 | - | - | 补 | - | 补 |
| 封面 | 主 | 补 | - | 补 | 补 | 补 | 补 |
| 评论 / 书评 | 主 | - | - | - | 补 | - | - |
| 名句 / 摘录 | 摘录 | - | - | 名句 | - | - | - |
| 系列 / 相关 | 主 | - | - | - | 补 | 补 | - |

## ID 规则

| 类型 | 格式 | 示例 |
|---|---|---|
| 书籍 ID | `0200NNNNNN` | `0200000001` |
| 书籍系列 ID | `0299NNNNNN` | `0299000001` |
| 人物编码 | `pNNNNNN` 或外部源派生 ID | `p000001` |
