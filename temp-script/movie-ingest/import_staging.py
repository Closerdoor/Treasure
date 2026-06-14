# -*- coding: utf-8 -*-
"""
Staging 入库预检与正式导入入口。

默认只做只读预检和临时库演练；只有显式传入 --apply 才会写入 .local/treasure.db。
本脚本只负责 movie-ingest 边界内的 SQLite 入库，不导出 generated，也不运行 Astro 构建。
"""
import argparse
import json
import re
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import config
from database import TreasureDB
from media_profiles import apply_profile_defaults, expected_next_id, resolve_profile_from_data, supported_schema_types
from utils import Logger


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


def collect_source_ids(data: Dict[str, Any]) -> Dict[str, str]:
    ids = {
        "douban": data.get("doubanId"),
        "imdb": data.get("imdbId"),
        "tmdb": data.get("tmdbId"),
        "baike": data.get("baikeId"),
        "wikipedia": data.get("wikipediaId"),
    }
    return {key: str(value) for key, value in ids.items() if value}


def extract_baike_numeric_id(url: Any) -> str:
    value = str(url or "")
    match = re.search(r"baike\.baidu\.com/item/[^/?#]+/(\d+)(?:[/?#]|$)", value)
    return match.group(1) if match else ""


def validate_source_integrity(data: Dict[str, Any]) -> List[str]:
    """校验 source hint 是否足够精确；失败项必须阻断入库。"""
    problems: List[str] = []

    douban_id = str(data.get("doubanId") or data.get("douban_id") or "").strip()
    if douban_id and not re.fullmatch(r"\d+", douban_id):
        problems.append(f"豆瓣 ID 非数字: {douban_id}")

    imdb_id = str(data.get("imdbId") or data.get("imdb_id") or "").strip()
    if imdb_id and not re.fullmatch(r"tt\d+", imdb_id):
        problems.append(f"IMDb ID 格式异常: {imdb_id}")

    tmdb_id = str(data.get("tmdbId") or data.get("tmdb_id") or "").strip()
    if tmdb_id and not re.fullmatch(r"\d+", tmdb_id):
        problems.append(f"TMDB ID 非数字: {tmdb_id}")

    baike_url = str(data.get("baikeUrl") or data.get("baike_url") or "").strip()
    baike_id = str(data.get("baikeId") or data.get("baike_id") or "").strip()
    baike_url_id = extract_baike_numeric_id(baike_url)
    if baike_url and "baike.baidu.com/item/" in baike_url and not baike_url_id:
        problems.append("百度百科链接不是精确词条 URL，缺少数字词条 ID")
    if baike_id and not re.fullmatch(r"\d+", baike_id):
        problems.append(f"百度百科 ID 不是数字词条 ID: {baike_id}")
    if baike_url_id and baike_id and baike_url_id != baike_id:
        problems.append(f"百度百科 URL ID 与 baikeId 不一致: url={baike_url_id}, id={baike_id}")

    return problems


def get_db_max_profile_id(conn: sqlite3.Connection, id_prefix: str) -> str:
    row = conn.execute(
        "SELECT id FROM works WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
        (f"{id_prefix}%",),
    ).fetchone()
    return row["id"] if row else ""


def has_required_field(data: Dict[str, Any], field: str) -> bool:
    aliases = {
        "schemaType": ["schema_type"],
        "episodeCount": ["episode_count"],
        "episodeTime": ["episode_time"],
        "episodesStory": ["episodes_story"],
    }
    for key in [field, *aliases.get(field, [])]:
        value = data.get(key)
        if value in (None, "", []):
            continue
        if field == "episodesStory" and isinstance(value, list):
            episode_count = data.get("episodeCount") or data.get("episode_count")
            try:
                episode_count = int(episode_count or 0)
            except (TypeError, ValueError):
                episode_count = 0

            story_episodes = set()
            for index, item in enumerate(value, start=1):
                if not isinstance(item, dict):
                    continue
                if not (item.get("story") or item.get("summary") or item.get("content")):
                    continue
                episode_number = item.get("episode") or item.get("episodeNumber") or item.get("number") or index
                try:
                    episode_number = int(episode_number)
                except (TypeError, ValueError):
                    episode_number = index
                story_episodes.add(episode_number)

            if episode_count:
                expected_numbers = set(range(1, episode_count + 1))
                return story_episodes == expected_numbers
            return bool(story_episodes)
        if field == "characters" and isinstance(value, list):
            return any(
                isinstance(item, dict) and (item.get("name") or item.get("nameEn"))
                for item in value
            )
        return True
    return False


def find_existing_matches(conn: sqlite3.Connection, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    source_ids = collect_source_ids(data)
    rows = conn.execute(
        """
        SELECT id, module, submodule, schema_type, title, title_original, year, external_source
        FROM works
        WHERE module IN ('video', 'anime')
        """
    ).fetchall()

    matches: List[Dict[str, Any]] = []
    for row in rows:
        reasons: List[str] = []
        sources = parse_json_text(row["external_source"], [])
        source_map: Dict[str, str] = {}
        if isinstance(sources, list):
            for source in sources:
                if not isinstance(source, dict):
                    continue
                name = str(source.get("name") or "").lower()
                source_id = source.get("id")
                if not source_id:
                    continue
                if "豆瓣" in name or "douban" in name:
                    source_map["douban"] = str(source_id)
                elif "imdb" in name:
                    source_map["imdb"] = str(source_id)
                elif "tmdb" in name:
                    source_map["tmdb"] = str(source_id)
                elif "百度" in name or "baike" in name:
                    source_map["baike"] = str(source_id)
                elif "维基" in name or "wikipedia" in name:
                    source_map["wikipedia"] = str(source_id)

        if row["id"] == data.get("id"):
            reasons.append("id")

        for key, value in source_ids.items():
            if value and source_map.get(key) == value:
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
        db._promote_work_assets = lambda *args, **kwargs: {"copied": 0, "missing": 0, "skipped": "precheck"}
        result = db.import_media(data)
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
    backup_path = backup_dir / f"treasure-before-media-{work_id}-{stamp}.db"
    shutil.copy2(config.DB_PATH, backup_path)
    return backup_path


def precheck(
    work_id: str,
    data: Dict[str, Any],
    update_existing: bool = False,
    expected_id_override: str = "",
    allow_enhancement_missing: bool = False,
) -> Dict[str, Any]:
    apply_profile_defaults(data)
    profile = resolve_profile_from_data(data)

    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row

    max_id = get_db_max_profile_id(conn, profile.id_prefix)
    expected_id = expected_id_override or expected_next_id(max_id, profile)
    matches = find_existing_matches(conn, data)
    conn.close()

    assets = validate_assets(work_id, data)
    dry_run = dry_run_import(data) if update_existing or not matches else None

    problems: List[str] = []
    if update_existing:
        id_matches = [match for match in matches if match.get("id") == work_id]
        other_matches = [match for match in matches if match.get("id") != work_id]
        if not id_matches:
            problems.append("update-existing 模式下数据库中未找到同 ID 的已有媒体作品")
        if other_matches:
            problems.append("update-existing 模式下数据库中存在其他疑似匹配作品")
        matches = []
        expected_id = data.get("id")
    if matches:
        problems.append("数据库中疑似已存在同一作品")
    if data.get("id") != expected_id:
        problems.append(f"作品 ID 不是该类型数据库下一条 ID，当前 {data.get('id')}，预期 {expected_id}")
    if assets["missing"]:
        problems.append(f"本地资源缺失 {len(assets['missing'])} 个")
    if assets["external_refs"]:
        problems.append(f"仍存在外链资源引用 {len(assets['external_refs'])} 个")
    if assets["non_local_objects"]:
        problems.append(f"图片列表仍存在非本地文件对象 {len(assets['non_local_objects'])} 个")
    source_problems = validate_source_integrity(data)
    problems.extend(source_problems)
    if dry_run and dry_run["foreign_key_problems"]:
        problems.append(f"临时库导入存在外键问题 {dry_run['foreign_key_problems']} 个")
    if dry_run and not dry_run["result"].get("success"):
        problems.append(f"临时库导入失败: {dry_run['result'].get('error')}")
    for field in profile.required_fields:
        if not has_required_field(data, field):
            problems.append(f"{profile.label} 缺少必填字段: {field}")
    enhancement_problems: List[str] = []
    for field in profile.enhancement_required_fields:
        if not has_required_field(data, field):
            message = f"{profile.label} 缺少增强必备字段: {field}"
            enhancement_problems.append(message)
            if not allow_enhancement_missing:
                problems.append(message)

    return {
        "work_id": work_id,
        "profile": {
            "key": profile.key,
            "label": profile.label,
            "module": profile.module,
            "submodule": profile.submodule,
            "schemaType": profile.schema_type,
            "id_prefix": profile.id_prefix,
            "asset_dir": profile.asset_dir,
            "series_fields": profile.series_fields,
            "enhancement_required_fields": profile.enhancement_required_fields,
        },
        "title": data.get("title"),
        "original_title": data.get("originalTitle"),
        "year": data.get("year"),
        "source_ids": collect_source_ids(data),
        "source_problems": source_problems,
        "db_max_profile_id": max_id,
        "expected_next_profile_id": expected_id,
        "expected_id_override": expected_id_override or None,
        "update_existing": update_existing,
        "matches": matches,
        "assets": assets,
        "dry_run": dry_run,
        "enhancement_problems": enhancement_problems,
        "allow_enhancement_missing": allow_enhancement_missing,
        "problems": problems,
    }


def apply_import(data: Dict[str, Any]) -> Dict[str, Any]:
    backup_path = backup_database(data["id"])
    db = TreasureDB()
    result = db.import_media(data)
    db.close()
    return {
        "backup": str(backup_path),
        "result": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="movie-ingest staging 入库预检与正式导入")
    parser.add_argument("--work-id", required=True, help="待导入的媒体作品 ID")
    parser.add_argument("--apply", action="store_true", help="通过预检后正式写入 .local/treasure.db")
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="刷新数据库中同 ID 的已有作品；只用于用户明确要求重新采集并覆盖入库的场景",
    )
    parser.add_argument(
        "--schema-type",
        choices=sorted(supported_schema_types()),
        help="覆盖 staging 中的 schemaType，用于人工确认后的分型入库",
    )
    parser.add_argument(
        "--allow-enhancement-missing",
        action="store_true",
        help="显式允许剧集/番剧缺少分集剧情或角色介绍等增强必备字段；会写入预检报告，不应静默使用",
    )
    args = parser.parse_args()

    data = load_staging(args.work_id)
    if args.schema_type:
        data["schemaType"] = args.schema_type
        data.pop("schema_type", None)
    apply_profile_defaults(data)
    report = precheck(
        args.work_id,
        data,
        update_existing=args.update_existing,
        allow_enhancement_missing=args.allow_enhancement_missing,
    )
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
