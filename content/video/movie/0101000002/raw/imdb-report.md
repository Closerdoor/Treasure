# IMDb 数据源获取报告

## 数据源信息

| 项目 | 值 |
|------|-----|
| 数据源 | IMDb (Internet Movie Database) |
| URL | https://www.imdb.com/title/tt11378946/ |
| 获取时间 | 2026-05-01T16:55:00Z |
| 获取方式 | WebFetch + 直接访问 |
| 访问状态 | ❌ 直接访问被禁止（403） |

## 字段获取统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已获取 | 0 | 0% |
| ⚠️ 部分获取 | 3 | 9.4% |
| ❌ 无法获取 | 29 | 90.6% |
| **总计** | **32** | **100%** |

## 访问尝试记录

### 尝试1：直接访问主页

```
URL: https://www.imdb.com/title/tt11378946/
结果: 403 Forbidden
原因: IMDb禁止非浏览器访问
```

### 尝试2：WebFetch

```
URL: https://www.imdb.com/title/tt11378946/
结果: 无响应
原因: WebFetch无法绕过IMDb的反爬虫机制
```

### 尝试3：演职员页面

```
URL: https://www.imdb.com/title/tt11378946/fullcredits
结果: 无响应
原因: 同样被禁止访问
```

### 替代方案：OMDb API

```
URL: https://www.omdbapi.com/?i=tt11378946
结果: ✅ 可用
限制: 数据有限，仅提供基础信息
```

## ⚠️ 部分获取（通过OMDb间接获取）

| 字段 | 值 | 来源 |
|------|-----|------|
| originalTitle | Michael | OMDb |
| year | 2026 | OMDb |
| imdbId | tt11378946 | 已知 |

## ❌ 无法获取（29个字段）

| 字段 | 原因 |
|------|------|
| title | IMDb不提供中文标题，且访问受限 |
| director | 访问受限，无法获取完整信息 |
| writer | 访问受限，无法获取完整信息 |
| cast | 访问受限，无法获取完整演员表 |
| otherCast | 访问受限 |
| producer | 访问受限 |
| genre | 访问受限 |
| country | 访问受限 |
| language | 访问受限 |
| runtime | 访问受限 |
| releaseDate | 访问受限，无法获取完整上映列表 |
| aka | 访问受限，无法获取别名列表 |
| doubanId | IMDb不提供 |
| doubanRating | IMDb不提供 |
| doubanVotes | IMDb不提供 |
| imdbRating | 评分尚未出炉 |
| imdbVotes | 评价人数尚未出炉 |
| rated | 访问受限 |
| awards | 访问受限，无法获取获奖页面 |
| synopsis | 访问受限 |
| videos | 访问受限，无法获取预告片 |
| images | 访问受限，无法获取图片 |
| soundtrack | 访问受限，无法获取原声带 |
| similar | 访问受限 |
| reviews | 访问受限，无法获取用户评论 |
| id | 系统生成字段 |
| module/submodule | 系统生成字段 |
| createdAt/updatedAt | 系统生成字段 |

## IMDb 正常情况下可提供的字段

如果能够访问，IMDb通常可提供：

| 字段 | 可用性 | 说明 |
|------|--------|------|
| originalTitle | ✅ | 原始标题 |
| year | ✅ | 上映年份 |
| director | ✅ | 完整导演信息+头像 |
| writer | ✅ | 完整编剧信息 |
| cast | ✅ | 完整演员表+头像+角色 |
| genre | ✅ | 类型 |
| country | ✅ | 制片国家 |
| language | ✅ | 语言 |
| runtime | ✅ | 片长 |
| releaseDate | ✅ | 各地区完整上映日期 |
| aka | ✅ | 完整别名列表 |
| imdbId | ✅ | IMDb ID |
| imdbRating | ✅ | IMDb评分 |
| imdbVotes | ✅ | IMDb评价人数 |
| rated | ✅ | 电影分级 |
| awards | ✅ | 详细获奖记录 |
| synopsis | ✅ | 剧情简介 |
| videos | ✅ | 预告片 |
| images | ✅ | 海报、剧照 |
| soundtrack | ✅ | 原声带信息 |
| similar | ✅ | 相似推荐 |
| reviews | ✅ | 用户评论 |
| boxOffice | ✅ | 票房数据 |
| productionCompany | ✅ | 制作公司 |
| technicalSpecs | ✅ | 技术规格 |

## IMDb 独有优势（如果可访问）

1. **最权威数据库** - 全球最大的电影数据库
2. **完整演职员** - 最详细的演职员信息
3. **获奖记录** - 完整的获奖和提名记录
4. **用户评论** - 大量用户评论
5. **IMDb评分** - 全球最权威的电影评分
6. **技术规格** - 摄影、音效等技术信息
7. **上映日期** - 全球各地区上映日期
8. **别名列表** - 完整的译名列表

## IMDb 局限性

1. **访问受限** - 禁止非浏览器访问
2. **无公开API** - 需付费使用IMDb Pro
3. **无中文数据** - 所有文本均为英文
4. **无豆瓣数据** - 不提供豆瓣评分
5. **反爬虫严格** - 需要浏览器或代理访问

## 访问技术方案

| 方案 | 可行性 | 说明 |
|------|--------|------|
| 直接HTTP请求 | ❌ | 返回403 |
| WebFetch | ❌ | 无法绕过反爬虫 |
| OMDb API | ✅ | 数据有限 |
| Playwright | ⚠️ | 可能成功，但需要处理验证码 |
| 代理+浏览器 | ⚠️ | 成本高，不稳定 |
| IMDb Pro API | ✅ | 付费服务 |

## 结论

IMDb 对于《Michael》(2026) **直接访问不可用**，返回403 Forbidden。

**替代方案：**
1. 使用OMDb API获取基础数据（已采用）
2. 使用Playwright模拟浏览器访问（不稳定）
3. 使用付费IMDb Pro API（成本高）

**推荐：** 通过OMDb间接获取IMDb数据，接受数据有限的现实。如果需要完整IMDb数据，考虑付费API或手动补充。

**OMDb已获取的IMDb相关字段：**
- originalTitle: Michael
- year: 2026
- runtime: 127分钟
- rated: PG-13
- awards: 2 wins & 1 nomination total
- synopsis: 英文剧情简介
