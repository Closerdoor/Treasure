# 霸王别姬 录入摘要

## 基本信息

- 片名：霸王别姬 / Farewell My Concubine
- 系统 ID：`0101000004`
- 豆瓣 ID：`1291546`
- IMDb ID：`tt0106332`
- TMDB ID：`10997`

## 数据源可用性

| 数据源 | 状态 | 备注 |
|--------|------|------|
| 豆瓣 | ✅ 可用 | 通过 Playwright 读取主页面、演职员页、短评页 |
| OMDb | ✅ 可用 | 成功获取英文标题、IMDb 评分、评级、获奖 |
| TMDB | ✅ 可用 | 成功获取主海报、补充海报、剧照、头像、Trailer |
| Wikipedia | ⚠️ 失败 | 本次请求出现 transport error |
| 百度百科 | ⚠️ 失败 | 目标词条 URL 404，未纳入本次正式数据 |

## 本次落地产物

- `data.json`
- `source.json`
- `index.md`
- `images/poster-main.jpg`
- `images/poster-01.jpg` ~ `poster-05.jpg`
- `images/still-01.jpg` ~ `still-05.jpg`
- `images/avatar-*.jpg`
- `images/video-trailer-01.jpg`

## 缺失字段

| 字段 | 状态 | 原因 | 后续方案 |
|------|------|------|----------|
| soundtrack | ⚠️ 暂缺 | 未获取到稳定可追溯的专辑/曲目来源 | 后续补百度百科或其他稳定来源 |
| images.wallpapers | ⚠️ 暂缺 | 本次未获取到可确认壁纸来源 | 保持空数组 |

## 说明

- 本次录入优先验证 `movie-entry-workflow` 在真实新条目上的可执行性。
- 由于豆瓣反爬和外部站点可用性波动，本次采用 `豆瓣 + OMDb + TMDB` 的组合完成正式条目。
- 所有正式字段均已在 `source.json` 中标注来源。
