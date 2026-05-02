# 字段验证规则

本文档定义电影数据的必填字段、验证规则和缺失处理策略。

## 必填字段

### 基本信息（必须）

| 字段 | 类型 | 验证规则 | 缺失处理 |
|------|------|----------|----------|
| id | string | 格式 `MMSSNNNNNN` | 系统自动生成 |
| title | string | 非空，中文名 | ❌ 必须有，否则无法录入 |
| originalTitle | string | 非空，通常英文 | 从豆瓣/OMDb获取 |
| year | number | 1900-2030 | 从豆瓣/OMDb获取 |
| genre | array | 非空数组 | 从豆瓣获取 |
| country | string | 非空 | 从豆瓣获取 |
| runtime | number | 60-300 分钟 | 从豆瓣获取 |

### 标识符（必须）

| 字段 | 类型 | 验证规则 | 缺失处理 |
|------|------|----------|----------|
| imdbId | string | 格式 `ttXXXXXXX` | 从豆瓣获取 |
| doubanId | string | 数字字符串 | 从豆瓣 URL 提取 |

### 演职员（必须）

| 字段 | 类型 | 验证规则 | 缺失处理 |
|------|------|----------|----------|
| director | array | 至少 1 位 | 从豆瓣获取 |
| cast | array | 至少 1 位 | 从豆瓣获取 |

### 内容（必须）

| 字段 | 类型 | 验证规则 | 缺失处理 |
|------|------|----------|----------|
| synopsis.text | string | 非空，30-200 字优先 | 从豆瓣/百度百科获取 |
| story.text | string | 非空，> 120 字符 | 从百度百科/维基百科/人工整理获取 |

## 推荐字段

### 评分（推荐）

| 字段 | 类型 | 验证规则 | 缺失处理 |
|------|------|----------|----------|
| doubanRating | number | 0-10 | 标记为 null，记录原因 |
| doubanVotes | number | > 0 | 标记为 null |
| imdbRating | number | 0-10 | 可能未出炉，标记为 null |

### 媒体（推荐）

| 字段 | 类型 | 验证规则 | 缺失处理 |
|------|------|----------|----------|
| images.poster | string | 文件存在且 > 200KB | 必须下载高清版本 |
| images.posters | array | 至少 1 张 | 可后续补充 |
| images.postersTotal | number | >= images.posters.length | 允许缺失，但建议记录源站总量 |
| images.stills | array | 至少 1 张 | 可后续补充 |
| images.stillsTotal | number | >= images.stills.length | 允许缺失，但建议记录源站总量 |

说明：

- `images.postersTotal` / `images.stillsTotal` 是源站可获取总量元数据
- 它们不要求等于当前本地已下载文件数量，也不要求等于当前数组长度

### 其他（推荐）

| 字段 | 类型 | 验证规则 | 缺失处理 |
|------|------|----------|----------|
| writer | array | 至少 1 位 | 从豆瓣获取 |
| releaseDate | array | 至少 1 条 | 从豆瓣获取 |
| language | string | 非空 | 从豆瓣获取 |
| aka | array | 可为空 | 从豆瓣获取 |
| videos | array | 可为空 | 从豆瓣获取 |
| similar | array | 可为空 | 从豆瓣获取 |
| reviews | array | 可为空，但如有数据应为长评摘录 | 从豆瓣长评页获取 |

## 可选字段

| 字段 | 说明 | 来源 |
|------|------|------|
| otherCast | 其他演员 | 豆瓣 |
| producer | 制片人 | 豆瓣 |
| rated | MPAA评级 | OMDb |
| awards | 获奖信息 | OMDb |
| soundtrack | 原声带 | 百度百科 |
| boxOffice | 票房 | 百度百科 |
| tmdbId | TMDB ID | TMDB（可能无） |
| wikibaseId | Wikidata ID | Wikipedia |

## 验证流程

### 1. 数据完整性验证

```javascript
function validateData(data) {
  const errors = [];
  const warnings = [];
  
  // 必填字段检查
  const required = ['id', 'title', 'originalTitle', 'year', 'genre', 'country', 'runtime', 'imdbId', 'doubanId', 'director', 'cast', 'synopsis'];
  
  for (const field of required) {
    if (!data[field] || (Array.isArray(data[field]) && data[field].length === 0)) {
      errors.push(`缺少必填字段: ${field}`);
    }
  }
  
  // 年份验证
  if (data.year < 1900 || data.year > 2030) {
    errors.push(`年份异常: ${data.year}`);
  }
  
  // 片长验证
  if (data.runtime < 60 || data.runtime > 300) {
    warnings.push(`片长异常: ${data.runtime} 分钟`);
  }
  
  // 评分验证
  if (data.doubanRating && (data.doubanRating < 0 || data.doubanRating > 10)) {
    errors.push(`豆瓣评分异常: ${data.doubanRating}`);
  }
  
  return { errors, warnings };
}
```

### 2. 图片质量验证

```powershell
function Validate-Images($imagesDir) {
  $issues = @()
  
  # 主海报必须 > 200KB
  $posterMain = Join-Path $imagesDir "poster-main.jpg"
  if (Test-Path $posterMain) {
    $size = (Get-Item $posterMain).Length / 1KB
    if ($size -lt 200) {
      $issues += "主海报质量不合格: $([math]::Round($size, 1)) KB < 200 KB"
    }
  } else {
    $issues += "缺少主海报"
  }
  
  # 海报数量检查
  $posters = Get-ChildItem $imagesDir -Filter "poster-*"
  if ($posters.Count -lt 5) {
    $issues += "海报数量不足: $($posters.Count) < 5"
  }
  
  # 剧照数量检查
  $stills = Get-ChildItem $imagesDir -Filter "still-*"
  if ($stills.Count -lt 5) {
    $issues += "剧照数量不足: $($stills.Count) < 5"
  }
  
  return $issues
}
```

### 3. 数据源覆盖验证

```javascript
function validateSourceCoverage(source) {
  const coverage = {
    total: 0,
    bySource: {}
  };
  
  for (const [field, info] of Object.entries(source)) {
    if (info.source !== 'system') {
      coverage.total++;
      const src = info.source === 'merged' ? 'merged' : info.source;
      coverage.bySource[src] = (coverage.bySource[src] || 0) + 1;
    }
  }
  
  // 警告：豆瓣覆盖率应 > 60%
  const doubanCoverage = coverage.bySource['douban'] / coverage.total;
  if (doubanCoverage < 0.6) {
    console.warn(`豆瓣覆盖率过低: ${doubanCoverage * 100}%`);
  }
  
  return coverage;
}
```

## 缺失字段处理

### 标记方式

在 `source.json` 中记录缺失原因：

```json
{
  "imdbRating": {
    "value": null,
    "status": "⚠️ 暂无数据",
    "note": "IMDb评分尚未出炉（电影刚上映）",
    "retryAfter": "2026-06-01"
  },
  "tmdbId": {
    "value": null,
    "status": "❌ 无法获取",
    "note": "TMDB数据库未收录此电影"
  },
  "cast[2].avatar": {
    "value": null,
    "status": "⚠️ 部分缺失",
    "note": "Juliano Valdi 在Wikipedia无独立页面"
  }
}
```

### 最终报告

生成缺失字段汇总：

```markdown
## 缺失字段汇总

| 字段 | 状态 | 原因 | 后续方案 |
|------|------|------|----------|
| imdbRating | ⚠️ 暂无 | 评分未出炉 | 等待1个月后补充 |
| tmdbId | ❌ 无数据 | TMDB未收录 | 等待收录后补充 |
| Juliano Valdi 头像 | ⚠️ 部分缺失 | 无Wikipedia页面 | 手动补充 |
```

## 更新记录

| 日期 | 变更 |
|------|------|
| 2026-05-01 | 初始版本 |
