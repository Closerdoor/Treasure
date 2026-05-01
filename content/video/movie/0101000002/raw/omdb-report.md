# OMDb 数据源获取报告

## 数据源信息

| 项目 | 值 |
|------|-----|
| 数据源 | OMDb API |
| URL | https://www.omdbapi.com/ |
| 获取时间 | 2026-05-01T16:35:00Z |
| 获取方式 | REST API |
| 访问状态 | ✅ 可用（需API Key） |
| API Key | trilogy（免费版） |

## 字段获取统计

| 状态 | 数量 | 占比 |
|------|------|------|
| ✅ 已获取 | 11 | 34.4% |
| ⚠️ 部分获取 | 6 | 18.8% |
| ❌ 无法获取 | 15 | 46.8% |
| **总计** | **32** | **100%** |

## 详细字段列表

### ✅ 已获取（11个字段）

| 字段 | 值 | API字段 |
|------|-----|----------|
| originalTitle | Michael | Title |
| year | 2026 | Year |
| genre | Biography, Drama, History | Genre |
| country | United Kingdom, United States | Country |
| language | English | Language |
| runtime | 127分钟 | Runtime |
| imdbId | tt11378946 | imdbID |
| rated | PG-13 | Rated |
| awards | 2 wins & 1 nomination total | Awards |
| synopsis | 英文剧情简介 | Plot |
| images.poster | Amazon海报链接 | Poster |

### ⚠️ 部分获取（6个字段）

| 字段 | 已获取 | 未获取 | 原因 |
|------|--------|--------|------|
| director | 英文名 | 中文名、头像、代表作 | OMDb仅提供英文名 |
| writer | 英文名 | 中文名、角色 | OMDb仅提供英文名 |
| cast | 3位主演英文名 | 中文名、角色、头像、完整列表 | OMDb仅提供3位主演 |
| releaseDate | 美国上映日期 | 其他地区 | OMDb仅提供美国日期 |
| images | 主海报链接 | 海报列表、剧照、壁纸 | OMDb仅提供1张海报 |
| links | IMDb链接 | 豆瓣、TMDB | OMDb不提供其他链接 |

### ❌ 无法获取（15个字段）

| 字段 | 原因 |
|------|------|
| title | OMDb不提供中文标题 |
| otherCast | OMDb不提供完整演员表 |
| producer | OMDb不提供制片人信息 |
| aka | OMDb不提供别名/译名 |
| doubanId | OMDb不提供豆瓣ID |
| doubanRating | OMDb不提供豆瓣评分 |
| doubanVotes | OMDb不提供豆瓣评价人数 |
| videos | OMDb不提供预告片信息 |
| soundtrack | OMDb不提供原声带信息 |
| similar | OMDb不提供相似推荐 |
| reviews | OMDb不提供用户评论 |
| id | 系统生成字段 |
| module | 系统生成字段 |
| submodule | 系统生成字段 |
| createdAt/updatedAt | 系统生成字段 |

### ⚠️ 暂无数据（API返回N/A）

| 字段 | 原因 |
|------|------|
| imdbRating | IMDb评分尚未出炉 |
| imdbVotes | IMDb评价人数尚未出炉 |
| metascore | Metacritic评分尚未出炉 |
| tomatoMeter | 烂番茄评分尚未出炉 |

## OMDb 独有优势

1. **MPAA评级** - 电影分级信息（PG-13, R等）
2. **获奖信息** - 获奖和提名汇总
3. **英文剧情简介** - 官方英文简介
4. **IMDb ID** - 可用于关联IMDb数据
5. **烂番茄链接** - 烂番茄页面URL
6. **API稳定** - REST API，易于集成
7. **无需登录** - 仅需API Key

## OMDb 局限性

1. **数据有限** - 仅提供基础信息
2. **无中文数据** - 所有文本均为英文
3. **演员信息不全** - 仅提供3位主演
4. **无预告片** - 不提供视频信息
5. **无原声带** - 不提供音乐信息
6. **无评论** - 不提供用户评论
7. **无相似推荐** - 不提供相关电影
8. **图片有限** - 仅提供1张海报

## API 参数说明

| 参数 | 说明 |
|------|------|
| i | IMDb ID（推荐） |
| t | 电影标题 |
| y | 年份（可选） |
| plot | full/short |
| tomatoes | true（包含烂番茄数据） |
| apikey | API密钥 |

## 访问技术要点

1. **API Key** - 免费版有限制，付费版无限制
2. **请求限制** - 免费版每日1000次请求
3. **响应格式** - JSON
4. **无需认证** - 仅需API Key

## 结论

OMDb 是**英文基础数据的补充来源**，特别适合获取MPAA评级和获奖信息。由于数据有限，不适合作为主数据源，但可以作为豆瓣的补充，获取豆瓣没有的字段。

**推荐作为补充数据源使用，主要获取：rated、awards、imdbId。**
