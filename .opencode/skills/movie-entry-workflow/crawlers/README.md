# 爬虫脚本说明

本目录包含电影数据录入所需的爬虫脚本。

## 脚本列表

| 脚本 | 用途 | 输入 | 输出 |
|------|------|------|------|
| `douban-movie.js` | 豆瓣电影爬虫 | 豆瓣电影 ID | raw-douban.json |
| `imdb.js` | IMDb 爬虫 | IMDb ID | raw-imdb.json |
| `baidu-baike.js` | 百度百科爬虫 | 电影名称 | raw-baike.json |

## 通用参数

所有脚本支持以下通用参数：

```
--output <file>     输出文件路径（默认：raw-{source}.json）
--cookie <string>   登录 cookie（豆瓣需要）
--timeout <ms>      超时时间（默认：30000）
--verbose           详细日志
```

## 输出格式

所有爬虫输出统一格式：

```json
{
  "source": "douban",
  "sourceUrl": "https://movie.douban.com/subject/1292052/",
  "crawledAt": "2026-05-01T15:30:00Z",
  "crawlerScript": "douban-movie.js",
  "data": {
    "title": "肖申克的救赎",
    "year": 1994,
    ...
  },
  "errors": [],
  "warnings": []
}
```

## 错误处理

- 网络错误：记录到 `errors` 数组，脚本继续执行
- 数据缺失：记录到 `warnings` 数组
- 登录失效：返回错误码 401，需要重新提供 cookie

## 使用示例

```bash
# 豆瓣爬虫
node douban-movie.js --id 1292052 --cookie "bid=xxx; dbcl2=xxx"

# IMDb 爬虫
node imdb.js --id tt0111161

# 百度百科爬虫
node baidu-baike.js --title "肖申克的救赎"
```

## 注意事项

1. **豆瓣需要登录**：部分页面需要登录才能访问，请提供有效 cookie
2. **请求频率**：脚本内置延迟，避免被封
3. **数据验证**：爬取后检查 `errors` 和 `warnings`
