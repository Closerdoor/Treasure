# 豆瓣 TOP250 电影录入工作流 - 2026-05-04 会话总结

## 一、当前进度

### 已完成
1. **DB-first 架构落地**
   - SQLite 作为唯一结构化数据主源
   - `generated/*.json` 作为前台消费层
   - 完整的导入/导出/校验工具链

2. **样板数据**
   - 6 部电影已完成闭环验证
   - 2 部高标准样板（`0101000005` 肖申克的救赎1、`0101000006` 星际穿越）
   - 现有样板位于：
     - `.local/staging/video/movie/*.json`
     - `.local/field-sources/video/movie/*.json`

3. **质量门禁工具**
   - `tools/db/check-movie-ingest-quality.mjs`
   - 支持两层检查：
     - 结构校验（必需字段、来源覆盖）
     - 高标准样板检查（40 条评论、TMDB 海报等）
   - 可选 `--enforce-high-standard` 硬拦截

4. **批量工作流入口**
   - `tools/db/generate-douban-top250-tasks.mjs` - 从 Top250 列表生成任务
   - `tools/db/run-movie-intake-from-tasks.mjs` - 通用电影录入
   - `tools/db/run-movie-batch-workflow.mjs` - 批量执行入口

5. **通用录入能力**
   - 不再依赖少数样板注册表
   - 自动组合：豆瓣详情页 + 豆瓣短评 + OMDb
   - 已验证：`0101000007 泰坦尼克号` 成功生成

### 待完成
- 通用 builder 目前是"轻量评论标准"，不是 40 条高标准
- TMDB / 烂番茄评论还未接入通用 builder
- 人物头像、海报画廊、剧照等资源补齐
- Top250 任务文件里的 `countries/genres` 列表字段解析有噪音

---

## 二、已确定的设计规范

### 2.1 数据流向

```
豆瓣 Top250 列表
       ↓
  任务文件 (.tasks.json)
       ↓
  通用录入 builder
       ↓
  staging JSON + field-sources JSON
       ↓
     SQLite
       ↓
  generated/*.json
       ↓
    Astro 站点
```

### 2.2 目录结构

| 路径 | 用途 |
|------|------|
| `.local/batches/*.tasks.json` | 批量任务文件 |
| `.local/staging/video/movie/*.json` | 正式录入 JSON |
| `.local/field-sources/video/movie/*.json` | 字段来源追溯 |
| `.local/new-flow/video/movie/*.json` | 新流程样板（可选） |
| `.local/treasure.db` | SQLite 主库 |
| `generated/*.json` | 前台消费层 |
| `site/public/assets/video/movie/{id}/` | 作品静态资源 |
| `site/public/assets/people/` | 共享人物头像 |

### 2.3 电影 ID 规则

- 格式：`MMSSNNNNNN`
- `MM`：模块编号（01=影视）
- `SS`：子模块编号（01=电影）
- `NNNNNN`：递增序号

示例：
- `0101000001` = 影视/电影/第 1 条
- `0101000007` = 影视/电影/第 7 条

### 2.4 字段规则

**必需字段**（`movie-ingest-contract.mjs`）：
- id, title, originalTitle, year
- director, writer, cast, otherCast, producer
- genre, country, language, runtime
- releaseDate, aka
- imdbId, doubanId, doubanRating
- synopsis, story
- images, videos, soundtrack, similar, reviews, links
- module, submodule, createdAt, updatedAt

**可选字段**：
- rated, awards, imdbRating, rottenTomatoes, metascore

**扩展字段**：
- schemaType, status, publishCompany, tags, series, tmdbId, quotes

**特殊规则**：
- `story.note` 不进数据库主字段
- `reviews` 结构：`author / source / date / content / url / title`
- `soundtrack` 结构：`albums[]`
- 评分只保留评分值，不保留票数

### 2.5 地区推断规则

- 只保留单一地区值
- 按"最早真实公映地区"推断
- 电影节、影展、首映场次不作为首发地区依据

### 2.6 评论标准

**高标准样板基线**（当前仅用于质量报告，不阻塞录入）：
- 总量 ≥ 40 条
- 豆瓣长评 ≥ 10
- 豆瓣短评 ≥ 10
- TMDB ≥ 10
- 烂番茄 ≥ 10

**轻量录入标准**（当前通用 builder）：
- 少量豆瓣短评即可
- 不阻塞 TOP250 批量推进
- 后续可人工补充

---

## 三、下一步：使用工作流录入数据

### 3.1 最短链路

```powershell
# 1. 生成豆瓣 Top250 任务文件
node "tools/db/generate-douban-top250-tasks.mjs"

# 2. 生成标准录入 JSON（先写入 new-flow 验证）
node "tools/db/run-movie-intake-from-tasks.mjs" --input ".local/batches/douban-top250.tasks.json"

# 3. 确认无误后，写入正式 staging
node "tools/db/run-movie-intake-from-tasks.mjs" --input ".local/batches/douban-top250.tasks.json" --output-mode staging"

# 4. 导入 SQLite
node "tools/db/import-movies.mjs"

# 5. 导出前台 JSON
node "tools/db/export-generated.mjs"

# 6. 检查静态资源
node "tools/db/check-assets.mjs"

# 7. 构建站点（在 site 目录下）
cd site
npm run build
```

### 3.2 可选参数

```powershell
# 限制条数
node "tools/db/generate-douban-top250-tasks.mjs" --limit 25

# 指定输出路径
node "tools/db/generate-douban-top250-tasks.mjs" --output ".local/batches/my-top250.tasks.json"

# 质量检查（不强制高标准）
node "tools/db/check-movie-ingest-quality.mjs" --ids "0101000007,0101000008" --mode staging

# 质量检查（强制高标准）
node "tools/db/check-movie-ingest-quality.mjs" --ids "0101000007" --mode staging --enforce-high-standard
```

### 3.3 批量执行入口

```powershell
# 完整流水线（intake -> validate -> import -> export -> check-assets -> build）
node "tools/db/run-movie-batch-workflow.mjs" --input ".local/batches/douban-top250.tasks.json" --output-mode staging --full-pipeline
```

---

## 四、数据源站点

当前通用 builder 使用的数据源：

| 数据源 | 用途 | 获取方式 |
|--------|------|----------|
| 豆瓣 Top250 列表 | 任务生成 | `https://movie.douban.com/top250` |
| 豆瓣电影详情页 | 基础元数据 | `https://movie.douban.com/subject/{id}/` |
| 豆瓣短评页 | 用户评论 | `https://movie.douban.com/subject/{id}/comments?status=P` |
| OMDb API | 补充元数据、评分 | `https://www.omdbapi.com/?apikey=trilogy&i={imdbId}` |

**待接入**：
- TMDB API（海报、剧照、评论）
- 烂番茄 API（评论）
- 维基百科（剧情简介、人物信息）

**已知限制**：
- 豆瓣详情页/短评页会被反爬拦截，需要算力校验
- IMDb 站点返回 403 Forbidden
- 豆瓣 CDN 原图直拉返回 418

---

## 五、后续优化方向

1. **数据源补全**
   - 接入 TMDB API 获取高清海报、剧照
   - 接入烂番茄 API 获取评论
   - 接入维基百科获取更完整的剧情简介

2. **评论质量提升**
   - 从"轻量标准"逐步提升到"高标准"
   - 补齐豆瓣长评全文抓取
   - 补齐 TMDB / 烂番茄评论

3. **资源补齐**
   - 人物头像自动补全
   - 海报画廊、剧照自动下载
   - 静态资源完整性校验

4. **工作流增强**
   - 断点续跑
   - 失败原因汇总
   - 清库后全量重建入口

---

## 六、关键文件索引

| 文件 | 用途 |
|------|------|
| `tools/db/generate-douban-top250-tasks.mjs` | Top250 任务生成 |
| `tools/db/run-movie-intake-from-tasks.mjs` | 通用电影录入 |
| `tools/db/run-movie-batch-workflow.mjs` | 批量执行入口 |
| `tools/db/check-movie-ingest-quality.mjs` | 质量门禁 |
| `tools/db/import-movies.mjs` | 导入 SQLite |
| `tools/db/export-generated.mjs` | 导出前台 JSON |
| `tools/db/check-assets.mjs` | 静态资源校验 |
| `tools/db/validate-movie-record.mjs` | 记录结构校验 |
| `tools/db/movie-ingest-contract.mjs` | 字段契约定义 |
| `tools/db/movie-intake-registry.mjs` | 样板注册表 |
| `tools/db/README.md` | 工具链说明 |
| `docs/MOVIE-INGEST-CONTRACT.md` | 录入规则文档 |
| `docs/MOVIE-INGEST-ACCEPTANCE.md` | 验收文档 |
| `docs/IMPORT-SUMMARY.md` | 导入摘要规范 |

---

## 七、会话结论

- 已具备"豆瓣 TOP250 批量录入"的基础能力
- 当前是"轻量评论标准"，可先推进入库，后续再补充质量
- 下一步由你自行研究数据源获取方式
- 再次启动时，直接使用上述工作流命令即可

---

*文档生成时间：2026-05-04*
