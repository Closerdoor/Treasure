# Wikipedia 数据源获取报告

## 数据源信息

| 项目 | 值 |
|------|-----|
| 数据源 | Wikipedia |
| URL | https://en.wikipedia.org/wiki/Michael_(2026_film) |
| API | https://en.wikipedia.org/api/rest_v1/page/summary/ |
| 获取时间 | 2026-05-01T16:45:00Z |
| 获取方式 | REST API |
| 访问状态 | ✅ 可用（无需认证） |

## 字段获取统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已获取 | 5 | 15.6% |
| ⚠️ 部分获取 | 4 | 12.5% |
| ❌ 无法获取 | 23 | 71.9% |
| **总计** | **32** | **100%** |

## 详细字段列表

### ✅ 已获取（5个字段）

| 字段 | 值 | API字段 |
|------|-----|----------|
| originalTitle | Michael | title |
| year | 2026 | title（提取） |
| genre | Biographical | description |
| synopsis | 英文摘要 | extract |
| wikibaseId | Q116677364 | wikibase_item |

### ⚠️ 部分获取（4个字段）

| 字段 | 已获取 | 未获取 | 原因 |
|------|--------|--------|------|
| director | 英文名、头像 | 中文名、代表作 | 需单独查询演员页面 |
| cast | 英文名、部分头像 | 中文名、角色、完整列表 | 需单独查询演员页面 |
| images | 1张海报缩略图 | 海报列表、剧照、壁纸 | summary仅提供缩略图 |
| links | Wikipedia链接 | 豆瓣、IMDb、TMDB | summary不提供外部链接 |

### ❌ 无法获取（23个字段）

| 字段 | 原因 |
|------|------|
| title | Wikipedia不提供中文标题 |
| id | 系统生成字段 |
| country | summary不提供 |
| language | summary不提供 |
| runtime | summary不提供 |
| releaseDate | summary不提供 |
| aka | Wikipedia不提供别名 |
| imdbId | summary不提供 |
| doubanId | Wikipedia不提供 |
| doubanRating | Wikipedia不提供 |
| doubanVotes | Wikipedia不提供 |
| imdbRating | Wikipedia不提供 |
| imdbVotes | Wikipedia不提供 |
| rated | Wikipedia不提供 |
| awards | Wikipedia不提供 |
| videos | Wikipedia不提供 |
| soundtrack | summary不提供 |
| similar | Wikipedia不提供 |
| reviews | Wikipedia不提供 |
| otherCast | summary不提供 |
| producer | summary不提供 |
| module/submodule | 系统生成字段 |
| createdAt/updatedAt | 系统生成字段 |

## Wikipedia 独有优势

1. **Wikidata ID** - 可用于关联其他数据源（Q116677364）
2. **演职员头像** - 可单独查询每个演员获取头像（8个已获取）
3. **英文摘要** - 官方英文简介
4. **API稳定** - REST API，无需认证
5. **无需登录** - 公开访问
6. **图片无防盗链** - 可直接下载

## Wikipedia 局限性

1. **数据有限** - summary API仅提供基础信息
2. **无中文数据** - 所有文本均为英文
3. **无评分** - 不提供任何评分
4. **无预告片** - 不提供视频信息
5. **无原声带** - 不提供音乐信息
6. **无评论** - 不提供用户评论
7. **无相似推荐** - 不提供相关电影
8. **演员信息不全** - 需单独查询每个演员

## API 端点说明

| 端点 | 说明 |
|------|------|
| /page/summary/{title} | 页面摘要（推荐） |
| /page/html/{title} | 完整HTML |
| /page/plain/{title} | 纯文本 |

## 演员头像获取方法

```
1. 从电影页面获取演员列表
2. 对每个演员查询：/page/summary/{actor_name}
3. 提取 thumbnail.source 字段
4. 直接下载图片（无防盗链）
```

**已获取头像：**
- Jaafar Jackson ✅
- Nia Long ✅
- Laura Harrier ✅
- Jessica Sula ✅
- Mike Myers ✅
- Miles Teller ✅
- Colman Domingo ✅
- Antoine Fuqua ✅

**无法获取头像：**
- Juliano Valdi（无Wikipedia页面）
- KeiLyn Durrel Jones（无Wikipedia页面）

## 访问技术要点

1. **无需认证** - 公开API
2. **CORS支持** - 可从前端直接调用
3. **响应格式** - JSON
4. **图片无防盗链** - 可直接下载
5. **速率限制** - 无明显限制

## 结论

Wikipedia 是**演职员头像的最佳来源**，图片质量高、无防盗链、易于下载。但由于summary API数据有限，不适合作为主数据源。主要价值在于：

1. 获取Wikidata ID用于数据关联
2. 获取演职员头像
3. 获取英文摘要

**推荐作为补充数据源使用，主要获取：wikibaseId、演职员头像。**
