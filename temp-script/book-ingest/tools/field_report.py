# -*- coding: utf-8 -*-
"""
Generate a book-ingest field coverage report.

The report is intentionally generated from raw/staging files so it does not drift
from the current crawler output.
"""
import argparse
import html
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config


SOURCES = ["douban", "openlibrary", "baike", "wikipedia", "goodreads", "dangdang", "qidian"]

FIELDS = [
    ("title", "title", "中文书名", {"douban": ["title"], "openlibrary": ["title"], "baike": ["title", "baike_title"], "wikipedia": ["title"], "goodreads": ["detail.title", "title"], "dangdang": ["detail.title", "title"], "qidian": ["title"]}),
    ("title_original", "titleOriginal", "原名 / 源语言标题", {"douban": ["title_original"], "openlibrary": ["title"], "baike": ["title_original"], "wikipedia": ["title_original", "info.原名"], "goodreads": ["detail.title", "title"]}),
    ("other_titles", "otherTitles", "别名", {"baike": ["other_titles", "info.作品别名"], "wikipedia": ["other_titles"]}),
    ("isbn", "isbn", "ISBN", {"douban": ["isbn"], "openlibrary": ["isbn"], "goodreads": ["detail.isbn", "isbn"], "dangdang": ["detail.isbn", "isbn"], "baike": ["isbn", "info.ISBN"], "wikipedia": ["isbn", "info.ISBN"]}),
    ("year", "year", "出版年份", {"douban": ["year"], "openlibrary": ["first_publish_year"], "baike": ["year", "info.首次出版时间"], "wikipedia": ["year", "info.出版日期"], "goodreads": ["detail.year", "year"], "dangdang": ["detail.publish_year", "publish_year"]}),
    ("publish_date", "publishDate", "完整出版日期", {"douban": ["publish_date"], "baike": ["publish_date", "info.出版时间", "info.首次出版时间"], "wikipedia": ["publish_date", "info.出版日期"], "dangdang": ["detail.publish_date", "publish_date"]}),
    ("country", "country", "国家", {"douban": ["country"], "baike": ["country"], "wikipedia": ["country", "info.国家", "info.地点", "info.出版地"]}),
    ("language", "language", "语言", {"douban": ["language"], "baike": ["language", "info.语言"], "wikipedia": ["language", "info.语言"], "openlibrary": ["language"]}),
    ("word_count", "wordCount", "字数", {"baike": ["word_count", "info.字数"], "dangdang": ["detail.word_count", "word_count"], "qidian": ["word_count"]}),
    ("publisher", "publisher", "出版社", {"douban": ["publisher"], "openlibrary": ["publisher"], "baike": ["publisher", "info.出版社", "info.出版机构"], "wikipedia": ["publisher", "info.出版机构", "info.出版商"], "goodreads": ["detail.publisher", "publisher"], "dangdang": ["detail.publisher", "publisher"]}),
    ("pages", "pages", "页数", {"douban": ["pages"], "baike": ["pages", "info.页数"], "wikipedia": ["pages", "info.页数"], "goodreads": ["detail.pages", "pages"], "dangdang": ["detail.pages", "pages"]}),
    ("price", "price", "定价", {"douban": ["price"], "baike": ["price", "info.定价"], "dangdang": ["detail.price", "price"]}),
    ("binding", "binding", "装帧", {"douban": ["binding"], "baike": ["binding", "info.装帧"], "dangdang": ["detail.binding", "binding"]}),
    ("format", "format", "开本 / 版式", {"dangdang": ["detail.format", "format"], "baike": ["format", "info.开本"]}),
    ("edition", "edition", "版本 / 版次", {"douban": ["edition"], "dangdang": ["detail.edition", "edition"], "baike": ["edition", "info.版次"]}),
    ("summary", "summary", "内容简介（优先取 Wikipedia 故事大纲）", {"douban": ["summary"], "openlibrary": ["description"], "baike": ["summary"], "wikipedia": ["summary"], "goodreads": ["detail.summary", "summary"], "dangdang": ["detail.summary", "summary"], "qidian": ["summary"]}),
    ("story", "story", "完整剧情 / 内容情节（优先取百度百科）", {"baike": ["story", "content_plot", "plot"], "wikipedia": ["summary"]}),
    ("scores", "scores", "评分", {"douban": ["rating"], "openlibrary": ["rating"], "goodreads": ["detail.rating", "rating"]}),
    ("authors", "_meta.authors", "作者", {"douban": ["authors"], "openlibrary": ["authors"], "baike": ["authors", "author"], "wikipedia": ["authors", "author"], "goodreads": ["detail.authors", "authors"], "dangdang": ["detail.authors", "authors"], "qidian": ["authors", "author"]}),
    ("translators", "_meta.translators", "译者", {"douban": ["translators"], "wikipedia": ["translators"], "goodreads": ["detail.translators", "translators"], "dangdang": ["detail.translators", "translators"]}),
    ("tags", "_meta.tags / category", "标签 / 类型", {"douban": ["tags"], "openlibrary": ["subjects"], "goodreads": ["detail.genres", "genres"], "qidian": ["tags", "category"]}),
    ("images", "images", "封面", {"douban": ["main_cover_url", "cover_urls"], "openlibrary": ["cover_url", "cover_urls"], "wikipedia": ["cover_url"], "goodreads": ["detail.cover_url", "cover_url"], "dangdang": ["detail.cover_url", "cover_url"], "qidian": ["cover_url"]}),
    ("person_details", "_meta.personDetails", "作者详情 / 头像", {"douban": ["person_details"], "openlibrary": ["author_details"], "baike": ["author_baike_url"]}),
    ("reviews", "reviews", "书评 / 评论", {"douban": ["reviews", "comments"], "goodreads": ["reviews"]}),
    ("excerpts", "excerpts", "原文摘录", {"douban": ["excerpts"]}),
    ("quotes", "quotes", "名句", {"wikipedia": ["quotes"], "baike": ["quotes"]}),
    ("series", "seriesId / _meta.series", "系列", {"douban": ["series"], "openlibrary": ["series"], "wikipedia": ["series", "info.系列"], "goodreads": ["detail.series", "series"], "dangdang": ["detail.series_name", "series_name"]}),
    ("related", "related", "相关书籍", {"douban": ["recommendations"], "goodreads": ["detail.similar_books", "similar_books"]}),
]


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def get_path(data: Any, dotted: str) -> Any:
    current = data
    for part in dotted.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True


def preview(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        text = f"{len(value)} 项"
        if value:
            text += ": " + json.dumps(value[:2], ensure_ascii=False)
    elif isinstance(value, dict):
        keys = list(value.keys())
        text = f"{len(keys)} 键: " + ", ".join(str(k) for k in keys[:6])
    else:
        text = str(value)
    return text[:220] + ("..." if len(text) > 220 else "")


def first_values(data: Dict[str, Any], paths: Iterable[str]) -> List[tuple]:
    values = []
    for path in paths:
        value = get_path(data, path)
        if present(value):
            values.append((path, value))
    return values


def staging_value(staging: Dict[str, Any], staging_field: str) -> Any:
    if staging_field.startswith("_meta."):
        return get_path(staging, staging_field)
    return staging.get(staging_field)


def tag(text: str, cls: str) -> str:
    return f'<span class="tag {cls}">{html.escape(text)}</span>'


def render_report(book_id: str, raw: Dict[str, Any], staging: Dict[str, Any], output: Path) -> None:
    rows = []
    for index, (key, staging_field_name, desc, source_paths) in enumerate(FIELDS, 1):
        source_cells = []
        source_hit_count = 0
        for source in SOURCES:
            source_data = raw.get(source)
            if not source_data:
                source_cells.append(tag("缺 raw", "muted"))
                continue
            values = first_values(source_data, source_paths.get(source, []))
            if values:
                source_hit_count += 1
                source_cells.append("<br>".join(
                    f'{tag(path, "path")} <span class="value">{html.escape(preview(value))}</span>'
                    for path, value in values[:3]
                ))
            else:
                source_cells.append(tag("无", "muted"))

        staged = staging_value(staging, staging_field_name)
        staged_ok = present(staged)
        rows.append({
            "index": index,
            "db": staging_field_name,
            "desc": desc,
            "staging": preview(staged) if staged_ok else "",
            "staging_ok": staged_ok,
            "source_hit_count": source_hit_count,
            "source_cells": source_cells,
        })

    raw_summary = {source: len(value.keys()) if isinstance(value, dict) else 0 for source, value in raw.items()}
    title = staging.get("title") or book_id
    css = """
    body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif;background:#f6f7f9;color:#1f2937;margin:0;padding:24px}
    h1{font-size:24px;margin:0 0 4px}.sub{color:#6b7280;margin-bottom:18px}.card{background:#fff;border:1px solid #e5e7eb;border-radius:10px;margin-bottom:18px;overflow:hidden}
    .card h2{font-size:16px;margin:0;padding:12px 14px;background:#111827;color:white}.inner{padding:12px 14px}
    table{width:100%;border-collapse:collapse;font-size:12px}th,td{border-bottom:1px solid #e5e7eb;padding:8px;vertical-align:top}th{background:#f3f4f6;text-align:left;position:sticky;top:0}
    tr:hover td{background:#fafafa}.field{font-family:Consolas,monospace;color:#047857;font-weight:700}.value{color:#374151}.staged{max-width:240px}
    .tag{display:inline-block;border-radius:4px;padding:1px 5px;margin:1px;font-size:11px;font-weight:650}.ok{background:#dcfce7;color:#166534}.miss{background:#fee2e2;color:#991b1b}.muted{background:#f3f4f6;color:#6b7280}.path{background:#e0e7ff;color:#3730a3;font-family:Consolas,monospace}
    .summary{display:flex;gap:10px;flex-wrap:wrap}.pill{background:#eef2ff;color:#3730a3;border-radius:999px;padding:4px 10px;font-size:12px}
    """
    html_text = [
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">",
        f"<title>{html.escape(title)} 字段核对</title><style>{css}</style></head><body>",
        f"<h1>{html.escape(title)} 字段核对</h1>",
        f"<div class=\"sub\">book_id: {html.escape(book_id)} | 自动生成自 raw/staging</div>",
        "<div class=\"card\"><h2>数据源 raw 覆盖</h2><div class=\"inner\"><div class=\"summary\">",
    ]
    for source in SOURCES:
        count = raw_summary.get(source, 0)
        html_text.append(f"<span class=\"pill\">{source}: {count if count else '缺失'}</span>")
    html_text.append("</div></div></div>")
    html_text.append("<div class=\"card\"><h2>字段对照</h2><div class=\"inner\"><table><thead><tr>")
    headers = ["#", "DB / Staging 字段", "说明", "Staging 当前值", "来源数"] + SOURCES
    html_text.extend(f"<th>{html.escape(h)}</th>" for h in headers)
    html_text.append("</tr></thead><tbody>")
    for row in rows:
        html_text.append("<tr>")
        html_text.append(f"<td>{row['index']}</td>")
        html_text.append(f"<td class=\"field\">{html.escape(row['db'])}</td>")
        html_text.append(f"<td>{html.escape(row['desc'])}</td>")
        status = tag("已入 staging", "ok") if row["staging_ok"] else tag("缺 staging", "miss")
        html_text.append(f"<td class=\"staged\">{status}<br><span class=\"value\">{html.escape(row['staging'])}</span></td>")
        html_text.append(f"<td>{row['source_hit_count']}/{len(SOURCES)}</td>")
        html_text.extend(f"<td>{cell}</td>" for cell in row["source_cells"])
        html_text.append("</tr>")
    html_text.append("</tbody></table></div></div></body></html>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(html_text), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="生成书籍字段核对 HTML")
    parser.add_argument("--book-id", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    raw_dir = config.OUTPUT_DIR / "raw" / args.book_id
    raw = {}
    for source in SOURCES:
        data = load_json(raw_dir / f"{source}.json")
        if data is not None:
            raw[source] = data
    staging = load_json(config.OUTPUT_DIR / "staging" / f"{args.book_id}.json") or {}
    output = Path(args.output) if args.output else ROOT / "docs" / "field-map.html"
    render_report(args.book_id, raw, staging, output)
    print(f"field report written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
