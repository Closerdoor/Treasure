# -*- coding: utf-8 -*-
"""
媒体作品批量采集验证入口。

只生成 raw / staging / validation report，不写入 .local/treasure.db。
正式入库仍必须走 import_staging.py --apply。
"""
import argparse
import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import config
from crawl import MovieCrawler
from import_staging import load_staging, precheck, validate_source_integrity
from media_profiles import get_profile_by_schema_type, expected_next_id
from utils import Logger


def load_manifest(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    items = data.get("items", [])
    if not isinstance(items, list) or not items:
        raise ValueError("manifest.items 不能为空")
    return data


def get_profile_max_ids() -> Dict[str, str]:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    max_ids: Dict[str, str] = {}
    try:
        from media_profiles import MEDIA_PROFILES

        for profile in MEDIA_PROFILES.values():
            row = conn.execute(
                "SELECT id FROM works WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
                (f"{profile.id_prefix}%",),
            ).fetchone()
            max_ids[profile.id_prefix] = row["id"] if row else ""
    finally:
        conn.close()
    return max_ids


def parse_json_text(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def find_existing_for_item(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    title = item.get("title") or ""
    year = item.get("year")
    douban_id = str(item.get("doubanId") or "")

    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT id, title, title_original, year, module, submodule, schema_type, external_source
            FROM works
            WHERE module IN ('video', 'anime')
            """
        ).fetchall()
    finally:
        conn.close()

    matches: List[Dict[str, Any]] = []
    for row in rows:
        reasons: List[str] = []
        if douban_id:
            sources = parse_json_text(row["external_source"], [])
            if isinstance(sources, list):
                for source in sources:
                    name = str(source.get("name") or "").lower()
                    source_id = str(source.get("id") or "")
                    if ("豆瓣" in name or "douban" in name) and source_id == douban_id:
                        reasons.append("doubanId")
                        break

        if title and row["title"] == title and (not year or row["year"] == year):
            reasons.append("title_year")
        if title and row["title_original"] == title and (not year or row["year"] == year):
            reasons.append("original_title_year")

        if reasons:
            matches.append({
                "id": row["id"],
                "title": row["title"],
                "originalTitle": row["title_original"],
                "year": row["year"],
                "module": row["module"],
                "submodule": row["submodule"],
                "schemaType": row["schema_type"],
                "reasons": sorted(set(reasons)),
            })

    return matches


def write_preflight_report(manifest: Dict[str, Any], run_dir: Path) -> Dict[str, Any]:
    items = []
    for index, item in enumerate(manifest["items"], start=1):
        existing = find_existing_for_item(item)
        source_hint_problems = validate_source_integrity(item)
        status = "existing" if existing else "ready"
        if source_hint_problems:
            status = "source_hint_invalid"
        elif not item.get("doubanId"):
            status = "needs_source_hint" if not existing else "existing"
        items.append({
            "index": index,
            "input": item,
            "status": status,
            "existingMatches": existing,
            "sourceHintProblems": source_hint_problems,
        })

    report = {
        "runId": manifest.get("id"),
        "createdAt": datetime.now().isoformat(),
        "total": len(items),
        "existing": sum(1 for item in items if item["status"] == "existing"),
        "ready": sum(1 for item in items if item["status"] == "ready"),
        "needsSourceHint": sum(1 for item in items if item["status"] == "needs_source_hint"),
        "sourceHintInvalid": sum(1 for item in items if item["status"] == "source_hint_invalid"),
        "items": items,
    }
    (run_dir / "preflight-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return report


def next_expected_id(max_ids: Dict[str, str], schema_type: str) -> str:
    profile = get_profile_by_schema_type(schema_type)
    current_max = max_ids.get(profile.id_prefix, "")
    next_id = expected_next_id(current_max, profile)
    max_ids[profile.id_prefix] = next_id
    return next_id


def summarize_staging(data: Dict[str, Any]) -> Dict[str, Any]:
    images = data.get("images") or {}
    return {
        "id": data.get("id"),
        "title": data.get("title"),
        "originalTitle": data.get("originalTitle"),
        "year": data.get("year"),
        "module": data.get("module"),
        "submodule": data.get("submodule"),
        "schemaType": data.get("schemaType") or data.get("schema_type"),
        "runtime": data.get("runtime"),
        "episodeCount": data.get("episodeCount") or data.get("episode_count"),
        "episodeTime": data.get("episodeTime") or data.get("episode_time"),
        "episodesStoryCount": len(data.get("episodesStory") or data.get("episodes_story") or []),
        "charactersCount": len(data.get("characters") or []),
        "doubanId": data.get("doubanId"),
        "imdbId": data.get("imdbId"),
        "tmdbId": data.get("tmdbId"),
        "poster": images.get("poster"),
        "coversCount": len(images.get("covers") or {}),
        "postersCount": len(images.get("posters") or []),
        "stillsCount": len(images.get("stills") or []),
        "wallpapersCount": len(images.get("wallpapers") or []),
        "directorsCount": len(data.get("director") or []),
        "castCount": len(data.get("cast") or []),
        "genre": data.get("genre") or [],
        "tags": data.get("tags") or [],
    }


async def run_batch(
    manifest_path: Path,
    limit: int = 0,
    photo_category_limit: int = 0,
    skip_existing: bool = False,
    preflight_only: bool = False,
    resume: bool = False,
) -> Dict[str, Any]:
    manifest = load_manifest(manifest_path)
    items: List[Dict[str, Any]] = manifest["items"]
    if limit:
        Logger.warning(f"本次只验证前 {limit} 条；这是显式传入 --limit 的限制性运行")
        items = items[:limit]
    if photo_category_limit:
        Logger.warning(
            f"本次每个豆瓣图片分类最多采样 {photo_category_limit} 张；"
            "这是验证模式的显式限制，不得用于正式入库"
        )
        config.PHOTO_CATEGORY_LIMIT = photo_category_limit
    config.NONINTERACTIVE_BATCH = True

    run_id = manifest.get("id") or manifest_path.stem
    run_dir = config.DATA_DIR / "batch-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    preflight = write_preflight_report(manifest, run_dir)
    if preflight_only:
        return preflight

    report: Dict[str, Any] = {
        "runId": run_id,
        "manifest": str(manifest_path),
        "startedAt": datetime.now().isoformat(),
        "total": len(items),
        "photoCategoryLimit": photo_category_limit or None,
        "skipExisting": skip_existing,
        "preflight": {
            "existing": preflight["existing"],
            "ready": preflight["ready"],
            "needsSourceHint": preflight["needsSourceHint"],
            "sourceHintInvalid": preflight["sourceHintInvalid"],
        },
        "completed": 0,
        "failed": 0,
        "skipped": 0,
        "items": [],
    }
    preflight_items: Dict[int, Dict[str, Any]] = {
        int(item.get("index", 0)): item
        for item in preflight.get("items", [])
    }
    previous_items: Dict[int, Dict[str, Any]] = {}
    previous_report_path = run_dir / "validation-report.json"
    if resume and previous_report_path.exists():
        previous_report = json.loads(previous_report_path.read_text(encoding="utf-8"))
        for previous_item in previous_report.get("items", []):
            previous_items[int(previous_item.get("index", 0))] = previous_item

    expected_ids = get_profile_max_ids()
    crawler = MovieCrawler()
    await crawler.init()
    try:
        for index, item in enumerate(items, start=1):
            title = item["title"]
            schema_type = item["schemaType"]
            year = item.get("year")
            douban_id = item.get("doubanId") or ""
            expected_id = next_expected_id(expected_ids, schema_type)

            Logger.info("=" * 80)
            Logger.info(f"[{index}/{len(items)}] 验证采集: {title} -> {schema_type}, 预期 ID {expected_id}")
            Logger.info("=" * 80)

            result: Dict[str, Any] = {
                "index": index,
                "input": item,
                "expectedWorkId": expected_id,
                "status": "pending",
            }
            previous_result = previous_items.get(index)
            if previous_result and previous_result.get("status") in ("completed", "skipped_existing"):
                report["items"].append(previous_result)
                if previous_result["status"] == "completed":
                    report["completed"] += 1
                else:
                    report["skipped"] += 1
                report_path = run_dir / "validation-report.json"
                report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                continue

            try:
                preflight_item = preflight_items.get(index, {})
                if preflight_item.get("status") == "source_hint_invalid":
                    result.update({
                        "status": "source_hint_invalid",
                        "sourceHintProblems": preflight_item.get("sourceHintProblems") or [],
                    })
                    report["failed"] += 1
                    report["items"].append(result)
                    report_path = run_dir / "validation-report.json"
                    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                    continue

                existing = find_existing_for_item(item)
                if skip_existing and existing:
                    result.update({
                        "status": "skipped_existing",
                        "existingMatches": existing,
                    })
                    report["skipped"] += 1
                    report["items"].append(result)
                    report_path = run_dir / "validation-report.json"
                    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                    continue

                if douban_id:
                    work_id = await crawler.run_by_douban_id(douban_id, title, expected_id, schema_type)
                else:
                    work_id = await crawler.run_by_movie_name(title, year, schema_type)

                data = load_staging(work_id)
                check = precheck(work_id, data, expected_id_override=expected_id)
                source_problems = check.get("source_problems") or []
                result.update({
                    "status": (
                        "completed"
                        if not check["problems"]
                        else "source_validation_failed"
                        if source_problems
                        else "precheck_failed"
                    ),
                    "workId": work_id,
                    "stagingPath": str(config.STAGING_DIR / f"{work_id}.json"),
                    "rawDir": str(config.RAW_DIR / work_id),
                    "summary": summarize_staging(data),
                    "precheckProblems": check["problems"],
                    "sourceValidationProblems": source_problems,
                    "enhancementProblems": check["enhancement_problems"],
                    "assetMissing": len(check["assets"]["missing"]),
                    "externalAssetRefs": len(check["assets"]["external_refs"]),
                    "profile": check["profile"],
                })
            except Exception as exc:
                result.update({
                    "status": "failed",
                    "error": str(exc),
                })

            if result["status"] == "completed":
                report["completed"] += 1
            else:
                report["failed"] += 1
            report["items"].append(result)

            report_path = run_dir / "validation-report.json"
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    finally:
        await crawler.close()

    report["finishedAt"] = datetime.now().isoformat()
    report["completionRate"] = report["completed"] / report["total"] if report["total"] else 0
    report_path = run_dir / "validation-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="媒体作品批量采集验证，不写主库")
    parser.add_argument("--manifest", required=True, help="批量验证 manifest JSON 路径")
    parser.add_argument("--limit", type=int, default=0, help="只验证前 N 条；默认 0 表示不限制")
    parser.add_argument(
        "--photo-category-limit",
        type=int,
        default=0,
        help="验证模式下每个豆瓣图片分类最多采样 N 张；默认 0 表示完整抓取",
    )
    parser.add_argument("--skip-existing", action="store_true", help="预审发现已入库作品时跳过采集")
    parser.add_argument("--preflight-only", action="store_true", help="只生成预审报告，不初始化浏览器，不采集")
    parser.add_argument("--resume", action="store_true", help="复用已有 validation-report 中已完成/已跳过的项目")
    args = parser.parse_args()

    report = asyncio.run(
        run_batch(
            Path(args.manifest),
            args.limit,
            args.photo_category_limit,
            args.skip_existing,
            args.preflight_only,
            args.resume,
        )
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("failed", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
