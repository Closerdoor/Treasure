# -*- coding: utf-8 -*-
"""
Manifest-driven small batch runner for book-ingest.

This runner is intentionally read-only with respect to .local/treasure.db:
it crawls sources, builds staging, downloads assets, generates field reports,
and runs import_staging.precheck without ever passing --apply.
"""
import argparse
import asyncio
import html
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import config
from import_staging import load_staging, precheck
from main import AVAILABLE_SOURCES, crawl_source, download_author_avatars, sync_cover_assets_to_staging
from merger import DataMerger
from utils import Logger


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]


def load_manifest(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("manifest.items 必须是非空数组")
    return data


def normalize_problem(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def is_next_id_problem(problem: str) -> bool:
    return normalize_problem(problem).startswith("书籍 ID 不是数据库下一条书籍 ID")


def expected_batch_ids(items: List[Dict[str, Any]]) -> Dict[str, str]:
    first = str(items[0].get("bookId") or "")
    match = re.fullmatch(r"0200(\d{6})", first)
    if not match:
        return {}
    start = int(match.group(1))
    return {
        str(item.get("bookId")): f"0200{start + index:06d}"
        for index, item in enumerate(items)
    }


def runner_profile(item: Dict[str, Any], default_profile: str = "standard") -> str:
    return item.get("profile") or default_profile


def allowed_sources(item: Dict[str, Any], default_profile: str = "standard") -> List[str]:
    profile = runner_profile(item, default_profile)
    if item.get("type") == "web_novel" and profile == "web-novel-fast":
        return ["qidian"]
    if item.get("type") == "web_novel":
        return list(AVAILABLE_SOURCES)
    return [source for source in AVAILABLE_SOURCES if source != "qidian"]


def annotate_staging(item: Dict[str, Any], run_id: str) -> None:
    staging_path = config.OUTPUT_DIR / "staging" / f"{item['bookId']}.json"
    if not staging_path.exists():
        return
    data = json.loads(staging_path.read_text(encoding="utf-8"))
    meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
    if item.get("contentKind"):
        meta["contentKind"] = item["contentKind"]
    meta["batchRunId"] = run_id
    data["_meta"] = meta
    staging_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def classify_item(item: Dict[str, Any], report: Dict[str, Any] | None, errors: List[str], expected_ids: Dict[str, str]) -> Dict[str, Any]:
    review_notes = list(item.get("reviewNotes") or [])
    if not item.get("doubanId"):
        review_notes.append("缺少豆瓣读书锚点；根据项目规则，不得静默跳过豆瓣后直接正式入库。")

    problems = list(report.get("problems") or []) if report else []
    if report:
        expected_author_count = len(item.get("authors") or [])
        actual_author_count = int(report.get("authors") or 0)
        if expected_author_count and actual_author_count > expected_author_count + 1:
            review_notes.append(f"作者关系数量异常：manifest={expected_author_count}，staging={actual_author_count}，需人工去重/校正。")

    blocking_problems = []
    for problem in problems:
        if is_next_id_problem(problem) and expected_ids.get(item.get("bookId")) == item.get("bookId"):
            continue
        blocking_problems.append(problem)

    if errors or blocking_problems:
        status = "failed"
    elif review_notes:
        status = "needs_review"
    else:
        status = "ready"

    return {
        "status": status,
        "reviewNotes": review_notes,
        "precheckProblems": problems,
        "blockingProblems": blocking_problems,
        "errors": errors,
    }


def apply_profile_quality_gate(
    item: Dict[str, Any],
    report: Dict[str, Any] | None,
    raw_sources: Dict[str, bool],
    classification: Dict[str, Any],
    default_profile: str = "standard",
) -> Dict[str, Any]:
    profile = runner_profile(item, default_profile)
    if item.get("type") != "web_novel" or profile != "web-novel-fast":
        return classification

    blocking = list(classification.get("blockingProblems") or [])
    notes = list(classification.get("reviewNotes") or [])

    if not raw_sources.get("qidian"):
        notes.append("缺少起点 raw：允许用百科/维基等来源继续，但需人工确认来源是否可靠。")

    if report:
        if int(report.get("authors") or 0) <= 0:
            blocking.append("web-novel-fast 缺少作者")
        if report.get("assets", {}).get("local_refs", 0) <= 0:
            notes.append("缺少本地封面资源：前台可用占位图，但建议后续补封面。")
        if "story is missing" in (report.get("problems") or []):
            blocking = [problem for problem in blocking if problem != "story is missing"]
            notes.append("story 缺失：可先按网络小说整体入库，但需后续用百科或人工摘要补齐。")

    if blocking:
        status = "failed"
    elif notes:
        status = "needs_review"
    else:
        status = "ready"

    return {
        **classification,
        "status": status,
        "reviewNotes": notes,
        "blockingProblems": blocking,
    }


async def crawl_qidian_direct(item: Dict[str, Any]) -> None:
    hints = item.get("sourceHints") or {}
    url = hints.get("qidianUrl")
    if not url:
        await crawl_source("qidian", item.get("doubanId") or item["bookId"], item["title"], item["bookId"], item)
        return

    from sources.qidian_crawl import QidianCrawler

    crawler = QidianCrawler()
    merger = DataMerger()
    try:
        await crawler.init_browser()
        data = await crawler._get_detail(url)
        if data:
            merger.save_raw_data(item["bookId"], "qidian", data)
            Logger.success(f"起点中文网直连采集完成: {item['title']}")
        else:
            Logger.warning(f"起点中文网直连未返回数据: {item['title']}")
    finally:
        await crawler.close()


async def crawl_item(
    item: Dict[str, Any],
    refresh_sources: set[str] | None = None,
    default_profile: str = "standard",
) -> None:
    book_id = item["bookId"]
    douban_id = item.get("doubanId") or ""
    title = item["title"]
    refresh_sources = refresh_sources or set()

    if douban_id:
        for source in allowed_sources(item, default_profile):
            raw_file = config.OUTPUT_DIR / "raw" / book_id / f"{source}.json"
            if raw_file.exists() and source not in refresh_sources:
                Logger.info(f"{source} raw 已存在，复用: {raw_file}")
                continue
            try:
                await crawl_source(source, douban_id, title, book_id, item)
            except Exception as exc:
                Logger.error(f"{source} 采集失败: {title} - {exc}")
    else:
        raw_file = config.OUTPUT_DIR / "raw" / book_id / "qidian.json"
        if raw_file.exists() and "qidian" not in refresh_sources:
            Logger.info(f"qidian raw 已存在，复用: {raw_file}")
            return
        await crawl_qidian_direct(item)


def merge_item(item: Dict[str, Any], default_profile: str = "standard") -> None:
    merger = DataMerger()
    raw_data = merger.load_raw_data(item["bookId"])
    sources = set(allowed_sources(item, default_profile))
    filtered = {source: data for source, data in raw_data.items() if source in sources}
    if not filtered:
        Logger.warning(f"无可用 raw 数据: {item['bookId']}")
        return
    if set(raw_data) != set(filtered):
        ignored = sorted(set(raw_data) - set(filtered))
        Logger.info(f"合并时忽略不适用来源: {item['bookId']} -> {', '.join(ignored)}")
    merged = merger.merge(item["bookId"], filtered)
    merger.save_merged_data(item["bookId"], merged)


def generate_field_report(book_id: str, output: Path) -> bool:
    output.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "field_report.py"), "--book-id", book_id, "--output", str(output)],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
    )
    if result.returncode != 0:
        Logger.error(result.stderr or result.stdout or f"字段报告生成失败: {book_id}")
        return False
    return True


async def download_item_assets(item: Dict[str, Any], default_profile: str = "standard") -> None:
    from downloaders import CoverDownloader

    merger = DataMerger()
    raw_data = merger.load_raw_data(item["bookId"])
    sources = set(allowed_sources(item, default_profile))
    filtered = {source: data for source, data in raw_data.items() if source in sources}
    if not filtered:
        Logger.warning(f"无 raw 数据，跳过资源下载: {item['bookId']}")
        return

    downloader = CoverDownloader()
    try:
        await downloader.init()
        result = await downloader.download_from_raw_data(item["bookId"], filtered)
        if result:
            sync_cover_assets_to_staging(item["bookId"], result)
            Logger.success(f"封面下载完成: {item['bookId']} ({len(result)} 张)")
        else:
            Logger.warning(f"无封面可下载: {item['bookId']}")

        avatar_result = await download_author_avatars(item["bookId"])
        if avatar_result:
            Logger.success(f"作者头像下载完成: {item['bookId']} ({len(avatar_result)} 张)")
    finally:
        await downloader.close()


def summarize_raw_sources(item: Dict[str, Any], default_profile: str = "standard") -> Dict[str, bool]:
    book_id = item["bookId"]
    raw_dir = config.OUTPUT_DIR / "raw" / book_id
    return {
        source: (raw_dir / f"{source}.json").exists()
        for source in allowed_sources(item, default_profile)
    }


async def run_item(
    item: Dict[str, Any],
    run_dir: Path,
    expected_ids: Dict[str, str],
    refresh_sources: set[str] | None = None,
    default_profile: str = "standard",
) -> Dict[str, Any]:
    book_id = item["bookId"]
    title = item["title"]
    errors: List[str] = []
    Logger.info("=" * 60)
    Logger.info(f"批量试运行: {title} ({book_id})")
    Logger.info("=" * 60)

    try:
        await crawl_item(item, refresh_sources=refresh_sources, default_profile=default_profile)
    except Exception as exc:
        errors.append(f"crawl failed: {exc}")

    try:
        merge_item(item, default_profile=default_profile)
        annotate_staging(item, run_dir.name)
    except Exception as exc:
        errors.append(f"merge failed: {exc}")

    try:
        await download_item_assets(item, default_profile=default_profile)
    except Exception as exc:
        errors.append(f"download failed: {exc}")

    field_report_path = run_dir / "field-reports" / f"{book_id}.html"
    if not generate_field_report(book_id, field_report_path):
        errors.append("field report failed")

    report = None
    try:
        staging = load_staging(book_id)
        report = precheck(book_id, staging, update_existing=False)
    except Exception as exc:
        errors.append(f"precheck failed: {exc}")

    raw_sources = summarize_raw_sources(item, default_profile)
    classification = classify_item(item, report, errors, expected_ids)
    classification = apply_profile_quality_gate(item, report, raw_sources, classification, default_profile)
    result = {
        "bookId": book_id,
        "title": title,
        "type": item.get("type"),
        "contentKind": item.get("contentKind"),
        "profile": runner_profile(item, default_profile),
        "expectedAction": item.get("expectedAction"),
        "doubanId": item.get("doubanId") or "",
        "sourceHints": item.get("sourceHints") or {},
        "rawSources": raw_sources,
        "fieldReport": str(field_report_path.relative_to(ROOT)).replace("\\", "/"),
        "precheck": report,
        **classification,
    }

    item_result_path = run_dir / "items" / f"{book_id}.json"
    item_result_path.parent.mkdir(parents=True, exist_ok=True)
    item_result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def build_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    status_counts = {
        status: sum(1 for item in results if item["status"] == status)
        for status in ["ready", "needs_review", "failed"]
    }
    source_counts = {
        source: sum(1 for item in results if item["rawSources"].get(source))
        for source in AVAILABLE_SOURCES
    }
    cover_ok = sum(
        1 for item in results
        if item.get("precheck") and item["precheck"].get("assets", {}).get("local_refs", 0) > 0
    )
    return {
        "total": total,
        "statusCounts": status_counts,
        "sourceCoverage": {
            source: {
                "count": count,
                "rate": round(count / total, 4) if total else 0,
            }
            for source, count in source_counts.items()
        },
        "assetCoverage": {
            "itemsWithLocalAssets": cover_ok,
            "rate": round(cover_ok / total, 4) if total else 0,
        },
    }


def render_html_report(run_id: str, summary: Dict[str, Any], results: List[Dict[str, Any]], output: Path) -> None:
    def esc(value: Any) -> str:
        return html.escape(str(value if value is not None else ""))

    rows = []
    for item in results:
        sources = " / ".join(source for source, ok in item["rawSources"].items() if ok) or "无"
        blocking = item.get("blockingProblems") or []
        notes = item.get("reviewNotes") or []
        rows.append(
            "<tr>"
            f"<td>{esc(item['bookId'])}</td>"
            f"<td>{esc(item['title'])}</td>"
            f"<td>{esc(item['status'])}</td>"
            f"<td>{esc(sources)}</td>"
            f"<td>{esc(len(blocking))}</td>"
            f"<td>{esc('；'.join(notes[:3]))}</td>"
            f"<td><a href=\"{esc(item['fieldReport'])}\">字段核对</a></td>"
            "</tr>"
        )

    css = "body{font-family:Segoe UI,Microsoft YaHei,sans-serif;padding:24px;background:#f7f7f8;color:#20242a}table{width:100%;border-collapse:collapse;background:white}th,td{border:1px solid #e5e7eb;padding:8px;vertical-align:top}th{background:#111827;color:white}.card{background:white;border:1px solid #e5e7eb;border-radius:8px;padding:14px;margin:14px 0}.pill{display:inline-block;margin:4px 8px 4px 0;padding:4px 10px;border-radius:999px;background:#eef2ff;color:#3730a3}"
    status = summary["statusCounts"]
    html_text = (
        "<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        f"<title>{esc(run_id)} 批量报告</title><style>{css}</style></head><body>"
        f"<h1>{esc(run_id)} 批量报告</h1>"
        "<div class=\"card\">"
        f"<span class=\"pill\">总数 {summary['total']}</span>"
        f"<span class=\"pill\">ready {status['ready']}</span>"
        f"<span class=\"pill\">needs_review {status['needs_review']}</span>"
        f"<span class=\"pill\">failed {status['failed']}</span>"
        f"<span class=\"pill\">本地资源覆盖 {summary['assetCoverage']['itemsWithLocalAssets']}/{summary['total']}</span>"
        "</div>"
        "<table><thead><tr><th>ID</th><th>书名</th><th>状态</th><th>已有 raw</th><th>阻断问题</th><th>人工确认备注</th><th>字段报告</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></body></html>"
    )
    output.write_text(html_text, encoding="utf-8")


def rebuild_report_from_items(run_id: str) -> Dict[str, Any]:
    run_dir = config.OUTPUT_DIR / "batch-runs" / run_id
    item_dir = run_dir / "items"
    if not item_dir.exists():
        raise FileNotFoundError(f"找不到 item 结果目录: {item_dir}")
    results = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(item_dir.glob("*.json"))
    ]
    if not results:
        raise ValueError(f"没有可汇总的 item 结果: {item_dir}")
    summary = build_summary(results)
    payload = {
        "runId": run_id,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        "items": results,
    }
    (run_dir / "report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    render_html_report(run_id, summary, results, run_dir / "report.html")
    return payload


async def run_batch(
    manifest_path: Path,
    only_ids: List[str] | None = None,
    refresh_sources: set[str] | None = None,
    default_profile: str = "standard",
) -> Dict[str, Any]:
    manifest = load_manifest(manifest_path)
    run_id = manifest.get("runId") or f"book-batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    run_dir = config.OUTPUT_DIR / "batch-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    items = manifest["items"]
    if only_ids:
        wanted = set(only_ids)
        items = [item for item in items if item.get("bookId") in wanted]
        if not items:
            raise ValueError(f"--only 未匹配任何 bookId: {', '.join(only_ids)}")
    expected_ids = expected_batch_ids(items)
    results = []
    for item in items:
        results.append(await run_item(
            item,
            run_dir,
            expected_ids,
            refresh_sources=refresh_sources,
            default_profile=default_profile,
        ))

    summary = build_summary(results)
    payload = {
        "runId": run_id,
        "manifest": str(manifest_path),
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        "items": results,
    }
    (run_dir / "report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    render_html_report(run_id, summary, results, run_dir / "report.html")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="书籍 manifest 小批量只读试运行")
    parser.add_argument("--manifest", required=True, help="batch manifest JSON 路径")
    parser.add_argument("--only", default="", help="只运行指定 bookId，多个用逗号分隔")
    parser.add_argument("--profile", default="standard", choices=["standard", "web-novel-fast"], help="批量采集策略")
    parser.add_argument("--refresh-source", default="", help="强制重抓指定来源，多个用逗号分隔，例如 douban 或 douban,baike")
    parser.add_argument("--report-only", action="store_true", help="只从已有 item 结果重建 report.json/report.html")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = (ROOT / manifest_path).resolve()

    if args.report_only:
        manifest = load_manifest(manifest_path)
        payload = rebuild_report_from_items(manifest.get("runId"))
    else:
        only_ids = [item.strip() for item in args.only.split(",") if item.strip()]
        refresh_sources = {item.strip() for item in args.refresh_source.split(",") if item.strip()}
        payload = asyncio.run(
            run_batch(
                manifest_path,
                only_ids=only_ids or None,
                refresh_sources=refresh_sources or None,
                default_profile=args.profile,
            )
        )
    print(json.dumps({
        "runId": payload["runId"],
        "summary": payload["summary"],
        "report": str((config.OUTPUT_DIR / "batch-runs" / payload["runId"] / "report.html").relative_to(ROOT)).replace("\\", "/"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
