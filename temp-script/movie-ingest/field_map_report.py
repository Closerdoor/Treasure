# -*- coding: utf-8 -*-
"""
生成电影采集字段对照 HTML。

输入为 data/raw/{work_id}/ 下的各数据源 JSON，输出类似 book-ingest 的字段核对页面。
图片类字段只展示数量，不展开 URL 列表。
"""
import argparse
import html
import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List


SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR / "data" / "raw"
DOCS_DIR = SCRIPT_DIR / "docs"


SOURCES = [
    ("douban", "豆瓣"),
    ("tmdb", "TMDB"),
    ("omdb", "OMDb"),
    ("baike", "百度百科"),
    ("wikipedia", "Wikipedia"),
    ("rotten_tomatoes", "烂番茄"),
    ("metacritic", "Metacritic"),
]


FIELD_ROWS = [
    ("标识信息", [
        ("id", "作品ID", "id", "自动生成", {}),
        ("module", "一级模块", "module", "固定 video", {}),
        ("submodule", "二级模块", "submodule", "固定 movie", {}),
        ("schema_type", "内容类型", "schemaType", "固定 live_action_movie", {}),
        ("external_source", "外部来源(JSON数组)", "externalSource", "由 doubanId / imdbId / tmdbId 等生成", {
            "douban": ["douban_id"],
            "tmdb": ["detail.tmdb_id", "external_ids.imdb_id", "external_ids.wikidata_id"],
            "omdb": ["imdb_id"],
            "baike": ["url", "baike_id"],
            "wikipedia": ["url", "wikipedia_id"],
        }),
    ]),
    ("基础信息", [
        ("title", "中文标题", "title", "豆瓣优先", {
            "douban": ["detail.title", "title"],
            "tmdb": ["detail.title"],
            "omdb": ["title"],
            "baike": ["title"],
            "wikipedia": ["title"],
            "rotten_tomatoes": ["ratings.title", "title"],
        }),
        ("title_original", "原名", "originalTitle", "TMDB / 豆瓣 / OMDb 补充", {
            "douban": ["detail.original_title", "original_title"],
            "tmdb": ["detail.original_title"],
            "omdb": ["title"],
            "baike": ["title_foreign", "basic_info.外文名"],
        }),
        ("other_titles", "别名(JSON数组)", "aka", "豆瓣别名为主", {
            "douban": ["detail.aliases", "aliases"],
            "baike": ["other_titles", "basic_info.其他译名"],
        }),
        ("year", "年份", "year", "豆瓣优先，TMDB/OMDb 补充", {
            "douban": ["detail.year", "year"],
            "tmdb": ["detail.year"],
            "omdb": ["year"],
        }),
        ("country", "国家/地区", "country", "豆瓣优先", {
            "douban": ["detail.countries", "countries"],
            "tmdb": ["detail.countries"],
            "omdb": ["country"],
            "baike": ["production_region", "basic_info.制片地区"],
        }),
        ("language", "语言", "language", "豆瓣优先", {
            "douban": ["detail.languages", "languages"],
            "tmdb": ["detail.languages"],
            "omdb": ["language"],
            "baike": ["languages", "basic_info.对白语言"],
        }),
        ("total_time", "总时长(分钟)", "runtime", "豆瓣优先，TMDB/OMDb 补充", {
            "douban": ["detail.runtime_minutes", "runtime_minutes"],
            "tmdb": ["detail.runtime_minutes"],
            "omdb": ["runtime"],
            "baike": ["runtime", "basic_info.片长"],
        }),
        ("studio", "制片方", "studio", "TMDB 制片公司补充", {
            "tmdb": ["detail.production_companies"],
            "baike": ["production_companies", "basic_info.出品公司"],
        }),
        ("distributor", "发行公司", "distributor", "百度百科补充", {
            "baike": ["distributors", "basic_info.发行公司"],
        }),
        ("budget", "预算/成本", "budget", "TMDB/百科补充", {
            "tmdb": ["detail.budget"],
            "baike": ["budget", "basic_info.制片成本"],
        }),
        ("release_dates", "上映日期(JSON数组)", "releaseDate", "豆瓣优先，TMDB 分级/地区补充", {
            "douban": ["detail.release_dates", "release_dates"],
            "tmdb": ["release_dates.results", "detail.release_date"],
            "omdb": ["released"],
            "baike": ["release_time", "basic_info.上映时间"],
            "rotten_tomatoes": ["ratings.schema_movie.date_published"],
        }),
    ]),
    ("内容文本", [
        ("introduction", "简介(短文)", "synopsis", "豆瓣优先，百科补充", {
            "douban": ["detail.summary", "summary"],
            "tmdb": ["detail.overview"],
            "baike": ["summary"],
            "wikipedia": ["summary"],
            "omdb": ["plot"],
            "rotten_tomatoes": ["ratings.synopsis", "ratings.schema_movie.description"],
        }),
        ("story", "剧情(长文)", "story", "Wikipedia/百科补充", {
            "wikipedia": ["plot"],
            "baike": ["plot", "summary"],
        }),
        ("quotes", "名言(JSON数组)", "quotes", "Wikipedia 补充", {
            "wikipedia": ["quotes"],
        }),
        ("awards", "获奖信息", "awards", "OMDb/Wikipedia 补充", {
            "omdb": ["awards"],
            "wikipedia": ["awards"],
        }),
    ]),
    ("评分与分类", [
        ("scores", "评分(JSON对象)", "ratings", "各平台独立记录", {
            "douban": ["detail.rating", "rating", "rating_count"],
            "tmdb": ["detail.rating", "detail.rating_count"],
            "omdb": ["ratings", "imdb_rating", "imdb_votes", "metascore"],
            "rotten_tomatoes": ["ratings", "rating"],
            "metacritic": ["rating"],
        }),
        ("rating_certification", "分级/适龄", "rated", "OMDb/TMDB 补充", {
            "omdb": ["rated"],
            "tmdb": ["release_dates.results"],
            "rotten_tomatoes": ["ratings.metadata.certification"],
        }),
        ("genre", "类型(写入分类)", "genre", "豆瓣优先，TMDB/OMDb 补充", {
            "douban": ["detail.genres", "genres"],
            "tmdb": ["detail.genres"],
            "omdb": ["genres"],
            "rotten_tomatoes": ["ratings.metadata.genres", "ratings.schema_movie.genre"],
        }),
        ("tags", "标签(写入分类)", "tags", "豆瓣标签与 TMDB keywords", {
            "douban": ["detail.tags", "tags"],
            "tmdb": ["keywords"],
        }),
    ]),
    ("人物关系", [
        ("director", "导演(写入 work_person)", "director", "豆瓣中文名，TMDB 补充", {
            "douban": ["celebrities.directors", "directors"],
            "tmdb": ["__tmdb_directors"],
            "omdb": ["directors"],
            "baike": ["credits.directors", "directors_text", "basic_info.导演"],
            "rotten_tomatoes": ["ratings.schema_movie.directors"],
        }),
        ("writer", "编剧(写入 work_person)", "writer", "豆瓣中文名，TMDB 补充", {
            "douban": ["celebrities.writers", "writers"],
            "tmdb": ["__tmdb_writers"],
            "omdb": ["writers"],
            "baike": ["credits.writers", "writers_text", "basic_info.编剧"],
        }),
        ("producer", "制片人(写入 work_person)", "producer", "百度百科/TMDB 补充", {
            "baike": ["credits.producers", "producers_text", "basic_info.制片人"],
        }),
        ("cast", "演员(写入 work_person)", "cast/all_cast", "采集层全量，展示/合并层可切分", {
            "douban": ["celebrities.cast", "casts"],
            "tmdb": ["credits.cast"],
            "omdb": ["actors"],
            "baike": ["credits.cast", "cast_text", "basic_info.主演"],
            "rotten_tomatoes": ["ratings.schema_movie.actors", "search.selected_candidate.cast"],
        }),
    ]),
    ("媒体资源", [
        ("images", "图片(JSON对象)", "images", "只展示数量", {
            "douban": ["images", "main_poster_url"],
            "tmdb": ["images"],
            "omdb": ["poster"],
            "rotten_tomatoes": ["ratings.images", "ratings.poster"],
        }),
        ("videos", "视频(JSON数组)", "videos", "展示数量与首条标题", {
            "douban": ["trailers"],
            "tmdb": ["videos"],
        }),
        ("comments", "评论(JSON数组)", "reviews/comments", "影评/评论按配置数量，其余字段全量采集", {
            "douban": ["comments", "reviews"],
            "tmdb": ["reviews"],
            "rotten_tomatoes": ["reviews"],
            "metacritic": ["reviews"],
        }),
        ("related", "相关作品(JSON对象)", "similar/recommendations", "豆瓣推荐、TMDB 推荐/相似", {
            "douban": ["detail.series", "series", "detail.recommendations", "recommendations"],
            "tmdb": ["recommendations", "similar"],
        }),
    ]),
]


def load_raw(work_id: str) -> Dict[str, Dict[str, Any]]:
    raw_path = RAW_DIR / work_id
    data = {}
    for key, _ in SOURCES:
        path = raw_path / f"{key}.json"
        if path.exists():
            data[key] = json.loads(path.read_text(encoding="utf-8"))
    return data


def get_path(data: Any, dotted: str) -> Any:
    if dotted == "__tmdb_directors":
        crew = get_path(data, "credits.crew") or []
        return [
            item for item in crew
            if isinstance(item, dict) and item.get("job") == "Director"
        ]
    if dotted == "__tmdb_writers":
        writer_jobs = {"Writer", "Screenplay", "Story", "Novel", "Author", "Characters"}
        crew = get_path(data, "credits.crew") or []
        return [
            item for item in crew
            if isinstance(item, dict) and item.get("job") in writer_jobs
        ]

    current = data
    for part in dotted.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def image_summary(value: Any) -> str:
    if isinstance(value, dict):
        parts = []
        for key in ["posters", "stills", "wallpapers", "backdrops", "logos"]:
            if isinstance(value.get(key), list):
                total_key = f"{key}_total"
                if len(value[key]) == 0 and total_key in value:
                    continue
                parts.append(f"{key}: {len(value[key])}")
        for key in ["all_photos_total", "posters_total", "stills_total", "wallpapers_total", "other_total"]:
            if key in value:
                parts.append(f"{key}: {value[key]}")
        if value.get("poster") or value.get("main_poster_url"):
            parts.append("主图: 1")
        return "；".join(parts) if parts else summarize_value(value)
    if isinstance(value, str) and value:
        return "图片: 1"
    return "-"


def summarize_value(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, list):
        if not value:
            return "0"
        if all(isinstance(item, dict) for item in value):
            first = value[0]
            label = first.get("title") or first.get("name") or first.get("author") or first.get("job") or first.get("character") or ""
            return f"{len(value)} 条" + (f"；首条: {label}" if label else "")
        return "、".join(str(item) for item in value[:6]) + (f" 等 {len(value)} 项" if len(value) > 6 else "")
    if isinstance(value, dict):
        if not value:
            return "-"
        if "items" in value and isinstance(value["items"], list):
            return f"{len(value['items'])} 条"
        return json.dumps(value, ensure_ascii=False)[:240]
    text = str(value).strip()
    return text[:240] + ("..." if len(text) > 240 else "")


def source_cell(source_key: str, raw: Dict[str, Dict[str, Any]], paths: Dict[str, List[str]], db_field: str) -> str:
    data = raw.get(source_key)
    if not data:
        return "-"

    values = []
    for path in paths.get(source_key, []):
        value = get_path(data, path)
        if value is None and source_key == "douban" and not path.startswith("detail."):
            value = get_path(data.get("detail", {}), path)
        if value is None:
            continue
        if db_field == "images":
            values.append(image_summary(value))
        else:
            values.append(summarize_value(value))

    unique_values = []
    for value in values:
        if not value or value == "-" or value in unique_values:
            continue
        unique_values.append(value)
    values = unique_values
    return "；".join(values) if values else "-"


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def build_html(work_id: str, raw: Dict[str, Dict[str, Any]]) -> str:
    title = (
        get_path(raw.get("douban", {}), "detail.title")
        or get_path(raw.get("douban", {}), "title")
        or get_path(raw.get("tmdb", {}), "detail.title")
        or work_id
    )

    rows = []
    index = 1
    for category, fields in FIELD_ROWS:
        rows.append(f'<tr class="cat-header"><td colspan="{6 + len(SOURCES)}">{esc(category)}</td></tr>')
        for db_field, desc, crawler_field, note, paths in fields:
            cells = [
                f"<td>{index}</td>",
                f'<td><span class="db-field">{esc(db_field)}</span></td>',
                f"<td>{esc(desc)}</td>",
                '<td><span class="tag tag-db">DB</span></td>',
                f'<td><span class="crawler-field">{esc(crawler_field)}</span></td>',
            ]
            for source_key, _ in SOURCES:
                cells.append(f'<td><div class="data-val">{esc(source_cell(source_key, raw, paths, db_field))}</div></td>')
            cells.append(f"<td>{esc(note)}</td>")
            rows.append("<tr>" + "".join(cells) + "</tr>")
            index += 1

    source_rows = []
    for key, label in SOURCES:
        exists = key in raw
        source_rows.append(
            "<tr>"
            f"<td><b>{esc(label)}</b></td>"
            f"<td>{'已采集' if exists else '未采集'}</td>"
            f"<td>{esc(', '.join(raw[key].keys()) if exists else '-')}</td>"
            "</tr>"
        )

    source_headers = "".join(f"<th>{esc(label)}</th>" for _, label in SOURCES)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Movie-Ingest 字段映射对照表（{esc(title)}）</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"Microsoft YaHei",sans-serif;background:#f5f5f5;color:#333;padding:20px}}
h1{{text-align:center;margin-bottom:6px;font-size:22px}}
.subtitle{{text-align:center;color:#888;margin-bottom:20px;font-size:13px}}
.section{{background:#fff;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);margin-bottom:20px;overflow:hidden}}
.section-title{{background:#1a1a2e;color:#fff;padding:10px 16px;font-size:15px;font-weight:600}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{background:#f0f4f8;padding:8px 10px;text-align:left;font-weight:600;border-bottom:2px solid #d0d7de;white-space:nowrap;position:sticky;top:0;z-index:1}}
td{{padding:6px 10px;border-bottom:1px solid #eee;vertical-align:top;line-height:1.5}}
tr:hover td{{background:#f7f9fc}}
.db-field{{font-family:"Cascadia Code","Fira Code",monospace;font-size:11px;color:#059669;font-weight:600}}
.crawler-field{{font-family:"Cascadia Code","Fira Code",monospace;font-size:11px;color:#7c3aed}}
.data-val{{font-size:11px;color:#555;max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.data-val:hover{{white-space:normal;overflow:visible;background:#fffbe6;border-radius:3px;position:relative;z-index:2}}
.tag{{display:inline-block;padding:1px 6px;border-radius:3px;font-size:10px;font-weight:600;margin:1px}}
.tag-db{{background:#dcfce7;color:#166534}}
.cat-header{{background:#eef2ff;font-weight:600}}
.wrapper{{overflow-x:auto}}
</style>
</head>
<body>
<h1>Movie-Ingest 字段映射对照表</h1>
<p class="subtitle">以 {esc(title)}（work_id: {esc(work_id)}）为实例，展示各数据源实际采集内容；图片字段只展示数量 | {date.today().isoformat()}</p>
<div class="section">
<div class="section-title">数据源采集状态</div>
<div class="wrapper">
<table><thead><tr><th>数据源</th><th>状态</th><th>Raw 顶层字段</th></tr></thead><tbody>
{''.join(source_rows)}
</tbody></table>
</div>
</div>
<div class="section">
<div class="section-title">字段映射全表（含实际采集数据）</div>
<div class="wrapper">
<table>
<thead><tr><th>#</th><th>DB字段</th><th>说明</th><th>入库</th><th>爬虫字段</th>{source_headers}<th>备注</th></tr></thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</div>
</div>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="生成 movie-ingest 字段映射对照 HTML")
    parser.add_argument("--work-id", required=True, help="data/raw/{work_id} 的作品 ID")
    parser.add_argument("--output", default=str(DOCS_DIR / "field-map.html"), help="输出 HTML 路径")
    args = parser.parse_args()

    raw = load_raw(args.work_id)
    if not raw:
        raise SystemExit(f"未找到 raw 数据: {RAW_DIR / args.work_id}")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(build_html(args.work_id, raw), encoding="utf-8")
    print(f"已生成: {output}")


if __name__ == "__main__":
    main()
