# TMDB ID 映射表

本文档维护常见电影的 TMDB ID 映射，用于自动化图片爬取。

## 使用方式

通过 IMDb ID 查询 TMDB ID：

```powershell
$tmdbIdMap = @{
    "tt0111161" = 278  # 肖申克的救赎
    "tt0109830" = 13   # 阿甘正传
}

$tmdbId = $tmdbIdMap[$imdbId]
```

## 映射表

| IMDb ID | TMDB ID | 电影名 | 年份 |
|---------|---------|--------|------|
| tt0111161 | 278 | 肖申克的救赎 | 1994 |
| tt0109830 | 13 | 阿甘正传 | 1994 |
| tt0110413 | 1104 | 这个杀手不太冷 | 1994 |
| tt0120338 | 597 | 泰坦尼克号 | 1997 |
| tt0133093 | 604 | 黑客帝国 | 1999 |
| tt0168260 | 122 | 指环王：护戒使者 | 2001 |
| tt0120774 | 120 | 指环王：双塔奇兵 | 2002 |
| tt0167260 | 123 | 指环王：王者归来 | 2003 |
| tt0372784 | 155 | 蝙蝠侠：侠影之谜 | 2005 |
| tt0468569 | 1552 | 蝙蝠侠：黑暗骑士 | 2008 |
| tt1345836 | 49026 | 蝙蝠侠：黑暗骑士崛起 | 2012 |
| tt1375666 | 27205 | 盗梦空间 | 2010 |
| tt0848228 | 24428 | 复仇者联盟 | 2012 |
| tt2395427 | 99861 | 复仇者联盟2：奥创纪元 | 2015 |
| tt4154756 | 299536 | 复仇者联盟3：无限战争 | 2018 |
| tt4150214 | 299534 | 复仇者联盟4：终局之战 | 2019 |
| tt0245429 | 4504 | 指环王（未定） | - |

## 自动查询方案

如果映射表中没有，可以通过以下方式自动查询：

### 方案 1：爬取 TMDB 搜索页面

```powershell
function Get-TmdbId($movieName) {
    $searchUrl = "https://www.themoviedb.org/search/movie?query=" + [Uri]::EscapeDataString($movieName)
    $html = Invoke-WebRequest -Uri $searchUrl -UseBasicParsing
    $match = [regex]::Match($html.Content, '/movie/(\d+)')
    if ($match.Success) {
        return [int]$match.Groups[1].Value
    }
    return $null
}

$tmdbId = Get-TmdbId "Forrest Gump"
```

### 方案 2：使用 TMDB API（需要 API key）

```powershell
function Get-TmdbIdByImdb($imdbId, $apiKey) {
    $url = "https://api.themoviedb.org/3/find/$imdbId?api_key=$apiKey&external_source=imdb_id"
    $result = Invoke-RestMethod -Uri $url
    return $result.movie_results[0].id
}

$tmdbId = Get-TmdbIdByImdb "tt0109830" "YOUR_API_KEY"
```

## 更新记录

| 日期 | 变更 |
|------|------|
| 2026-05-01 | 初始版本，添加常见电影映射 |
