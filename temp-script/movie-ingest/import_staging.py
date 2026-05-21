# -*- coding: utf-8 -*-
"""
Staging 入库预检与正式导入入口。

默认只做只读预检和临时库演练；只有显式传入 --apply 才会写入 .local/treasure.db。
本脚本只负责 movie-ingest 边界内的 SQLite 入库，不导出 generated，也不运行 Astro 构建。
"""
import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import config
from database import TreasureDB
from utils import Logger


MOVIE_PREFIX = "0101"


def load_staging(work_id: str) -> Dict[str, Any]:
    staging_path = config.STAGING_DIR / f"{work_id}.json"
    if not staging_path.exists():
        raise FileNotFoundError(f"找不到 staging 文件: {staging_path}")

    data = json.loads(staging_path.read_text(encoding="utf-8"))
    if data.get("id") != work_id:
        raise ValueError(f"staging 内部 id={data.get('id')}，与文件 work_id={work_id} 不一致")
    return data


def parse_json_text(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def get_db_max_movie_id(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT id FROM works WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
        (f"{MOVIE_PREFIX}%",),
    ).fetchone()
    return row["id"] if row else ""


def expected_next_movie_id(max_id: str) -> str:
    if not max_id:
        return f"{MOVIE_PREFIX}000001"
    return f"{MOVIE_PREFIX}{int(max_id[-6:]) + 1:06d}"


def collect_source_ids(data: Dict[str, Any]) -> Dict[str, str]:
    ids = {
        "douban": data.get("doubanId"),
        "imdb": data.get("imdbId"),
        "tmdb": data.get("tmdbId"),
        "baike": data.get("baikeId"),
        "wikipedia": data.get("wikipediaId"),
    }
    return {key: str(value) for key, value in ids.items() if value}


def find_existing_matches(conn: sqlite3.Connection, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    source_ids = collect_source_ids(data)
    rows = conn.execute(
        """
        SELECT id, title, title_original, year, external_source
        FROM works
        WHERE module = 'video' AND submodule = 'movie'
        """
    ).fetchall()

    matches: List[Dict[str, Any]] = []
    for row in rows:
        reasons: List[str] = []
        sources = parse_json_text(row["external_source"], [])
        source_blob = json.dumps(sources, ensure_ascii=False)

        if row["id"] == data.get("id"):
            reasons.append("id")

        for key, value in source_ids.items():
            if value and value in source_blob:
                reasons.append(f"{key}:{value}")

        if data.get("title") and row["title"] == data.get("title") and row["year"] == data.get("year"):
            reasons.append("title+year")

        if (
            data.get("originalTitle")
            and row["title_original"] == data.get("originalTitle")
            and row["year"] == data.get("year")
        ):
            reasons.append("originalTitle+year")

        if reasons:
            item = dict(row)
            item["reasons"] = reasons
            matches.append(item)

    return matches


def collect_asset_refs(data: Dict[str, Any]) -> Tuple[List[str], List[str], List[str]]:
    images = data.get("images") or {}
    refs: List[str] = []

    poster = images.get("poster")
    if isinstance(poster, str):
        refs.append(poster)

    for key in ("posters", "stills", "wallpapers"):
        for value in images.get(key) or []:
            if isinstance(value, str):
                refs.append(value)
            else:
                refs.append(f"<non-local-object:{key}>")

    covers = images.get("covers") or {}
    if isinstance(covers, dict):
        refs.extend(value for value in covers.values() if isinstance(value, str))

    for video in data.get("videos") or []:
        if isinstance(video, dict) and isinstance(video.get("thumbnail"), str):
            refs.append(video["thumbnail"])

    external = sorted({ref for ref in refs if ref.startswith("http://") or ref.startswith("https://")})
    non_local = sorted({ref for ref in refs if ref.startswith("<non-local-object:")})
    local_refs = sorted({ref for ref in refs if ref and ref not in external and ref not in non_local})
    return local_refs, external, non_local


def validate_assets(work_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    base_dir = config.WORK_ASSETS_DIR / work_id
    local_refs, external, non_local = collect_asset_refs(data)
    missing: List[str] = []

    for ref in local_refs:
        path = base_dir / ref if "/" in ref else base_dir / "images" / ref
        if not path.exists():
            missing.append(ref)

    images = data.get("images") or {}
    return {
        "local_refs": len(local_refs),
        "external_refs": external,
        "non_local_objects": non_local,
        "missing": missing,
        "posters": len(images.get("posters") or []),
        "stills": len(images.get("stills") or []),
        "wallpapers": len(images.get("wallpapers") or []),
        "covers": images.get("covers") if isinstance(images.get("covers"), dict) else {},
        "videos": len(data.get("videos") or []),
    }


def dry_run_import(data: Dict[str, Any]) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db = Path(temp_dir) / "treasure-precheck.db"
        shutil.copy2(config.DB_PATH, temp_db)

        db = TreasureDB(str(temp_db))
        db._promote_work_assets = lambda work_id: {"copied": 0, "missing": 0, "skipped": "precheck"}
        result = db.import_movie(data)
        db.close()

        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        fk_problems = conn.execute("PRAGMA foreign_key_check").fetchall()
        work_person_count = conn.execute(
            "SELECT COUNT(*) AS count FROM work_person WHERE work_id = ?",
            (data["id"],),
        ).fetchone()["count"]
        work_category_count = conn.execute(
            "SELECT COUNT(*) AS count FROM work_category WHERE work_id = ?",
            (data["id"],),
        ).fetchone()["count"]
        conn.close()

        return {
            "result": result,
            "foreign_key_problems": len(fk_problems),
            "work_person": work_person_count,
            "work_category": work_category_count,
        }


def backup_database(work_id: str) -> Path:
    backup_dir = config.REPO_ROOT / ".local" / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"treasure-before-movie-{work_id}-{stamp}.db"
    shutil.copy2(config.DB_PATH, backup_path)
    return backup_path


def precheck(work_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row

    max_id = get_db_max_movie_id(conn)
    expected_id = expected_next_movie_id(max_id)
    matches = find_existing_matches(conn, data)
    conn.close()

    assets = validate_assets(work_id, data)
    dry_run = dry_run_import(data) if not matches else None

    problems: List[str] = []
    if matches:
        problems.append("数据库中疑似已存在同一作品")
    if data.get("id") != expected_id:
        problems.append(f"作品 ID 不是数据库下一条电影 ID，当前 {data.get('id')}，预期 {expected_id}")
    if assets["missing"]:
        problems.append(f"本地资源缺失 {len(assets['missing'])} 个")
    if assets["external_refs"]:
        problems.append(f"仍存在外链资源引用 {len(assets['external_refs'])} 个")
    if assets["non_local_objects"]:
        problems.append(f"图片列表仍存在非本地文件对象 {len(assets['non_local_objects'])} 个")
    if dry_run and dry_run["foreign_key_problems"]:
        problems.append(f"临时库导入存在外键问题 {dry_run['foreign_key_problems']} 个")
    if dry_run and not dry_run["result"].get("success"):
        problems.append(f"临时库导入失败: {dry_run['result'].get('error')}")

    return {
        "work_id": work_id,
        "title": data.get("title"),
        "original_title": data.get("originalTitle"),
        "year": data.get("year"),
        "source_ids": collect_source_ids(data),
        "db_max_movie_id": max_id,
        "expected_next_movie_id": expected_id,
        "matches": matches,
        "assets": assets,
        "dry_run": dry_run,
        "problems": problems,
    }


def apply_import(data: Dict[str, Any]) -> Dict[str, Any]:
    backup_path = backup_database(data["id"])
    db = TreasureDB()
    result = db.import_movie(data)
    db.close()
    return {
        "backup": str(backup_path),
        "result": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="movie-ingest staging 入库预检与正式导入")
    parser.add_argument("--work-id", required=True, help="待导入的电影作品 ID")
    parser.add_argument("--apply", action="store_true", help="通过预检后正式写入 .local/treasure.db")
    args = parser.parse_args()

    data = load_staging(args.work_id)
    report = precheck(args.work_id, data)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report["problems"]:
        Logger.error("预检未通过，已停止。")
        return 1

    if not args.apply:
        Logger.info("预检通过。未传入 --apply，因此没有写入主数据库。")
        return 0

    result = apply_import(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["result"].get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
