# -*- coding: utf-8 -*-
"""
Book staging precheck and import entry.

Default mode is read-only: it validates staging data and rehearses the import
against a temporary SQLite copy. Use --apply explicitly to write .local/treasure.db.
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
from database import BookDB
from utils import Logger


BOOK_PREFIX = "0200"
REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / ".local" / "treasure.db"


def load_staging(book_id: str) -> Dict[str, Any]:
    staging_path = config.OUTPUT_DIR / "staging" / f"{book_id}.json"
    if not staging_path.exists():
        raise FileNotFoundError(f"找不到 staging 文件: {staging_path}")

    data = json.loads(staging_path.read_text(encoding="utf-8"))
    if data.get("id") != book_id:
        raise ValueError(f"staging 内部 id={data.get('id')}，与文件 book_id={book_id} 不一致")
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


def get_db_max_book_id(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT id FROM books WHERE id LIKE ? ORDER BY id DESC LIMIT 1",
        (f"{BOOK_PREFIX}%",),
    ).fetchone()
    return row["id"] if row else ""


def expected_next_book_id(max_id: str) -> str:
    if not max_id:
        return f"{BOOK_PREFIX}000001"
    return f"{BOOK_PREFIX}{int(max_id[-6:]) + 1:06d}"


def collect_source_ids(data: Dict[str, Any]) -> Dict[str, str]:
    ids: Dict[str, str] = {}
    if data.get("isbn"):
        ids["isbn"] = str(data["isbn"])

    for source in data.get("externalSource") or []:
        if not isinstance(source, dict):
            continue
        name = str(source.get("name") or "").lower()
        source_id = source.get("id")
        if not source_id:
            continue
        if "豆瓣" in name or "douban" in name:
            ids["douban"] = str(source_id)
        elif "openlibrary" in name:
            ids["openlibrary"] = str(source_id)
        elif "goodreads" in name:
            ids["goodreads"] = str(source_id)
        elif "百度" in name or "baike" in name:
            ids["baike"] = str(source_id)
        elif "维基" in name or "wikipedia" in name:
            ids["wikipedia"] = str(source_id)
        elif "当当" in name or "dangdang" in name:
            ids["dangdang"] = str(source_id)
        elif "起点" in name or "qidian" in name:
            ids["qidian"] = str(source_id)

    return ids


def _source_map_from_db(row: sqlite3.Row) -> Dict[str, str]:
    source_map: Dict[str, str] = {}
    if row["isbn"]:
        source_map["isbn"] = str(row["isbn"])

    sources = parse_json_text(row["external_source"], [])
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
            elif "openlibrary" in name:
                source_map["openlibrary"] = str(source_id)
            elif "goodreads" in name:
                source_map["goodreads"] = str(source_id)
            elif "百度" in name or "baike" in name:
                source_map["baike"] = str(source_id)
            elif "维基" in name or "wikipedia" in name:
                source_map["wikipedia"] = str(source_id)
            elif "当当" in name or "dangdang" in name:
                source_map["dangdang"] = str(source_id)
            elif "起点" in name or "qidian" in name:
                source_map["qidian"] = str(source_id)

    return source_map


def find_existing_matches(conn: sqlite3.Connection, data: Dict[str, Any]) -> List[Dict[str, Any]]:
    source_ids = collect_source_ids(data)
    rows = conn.execute(
        """
        SELECT id, title, title_original, isbn, year, external_source
        FROM books
        """
    ).fetchall()

    matches: List[Dict[str, Any]] = []
    for row in rows:
        reasons: List[str] = []
        source_map = _source_map_from_db(row)

        if row["id"] == data.get("id"):
            reasons.append("id")

        for key, value in source_ids.items():
            if value and source_map.get(key) == value:
                reasons.append(f"{key}:{value}")

        if data.get("title") and row["title"] == data.get("title") and row["year"] == data.get("year"):
            reasons.append("title+year")

        if (
            data.get("titleOriginal")
            and row["title_original"] == data.get("titleOriginal")
            and row["year"] == data.get("year")
        ):
            reasons.append("titleOriginal+year")

        if reasons:
            item = dict(row)
            item["reasons"] = reasons
            matches.append(item)

    return matches


def collect_asset_refs(data: Dict[str, Any]) -> Tuple[List[str], List[str], List[str]]:
    images = data.get("images") or {}
    refs: List[str] = []
    non_local: List[str] = []

    if isinstance(images, str):
        non_local.append("<serialized-json:images>")
        images = parse_json_text(images, {})

    if isinstance(images, dict):
        cover = images.get("cover")
        if isinstance(cover, str):
            refs.append(cover)
        covers = images.get("covers") or {}
        if isinstance(covers, dict):
            iterable = covers.values()
        elif isinstance(covers, list):
            iterable = covers
        else:
            iterable = []
            non_local.append("<non-local-object:images.covers>")
        for value in iterable:
            if isinstance(value, str):
                refs.append(value)
            else:
                non_local.append("<non-local-object:images.covers>")
    elif images:
        non_local.append("<non-local-object:images>")

    meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
    for detail in meta.get("personDetails") or []:
        if not isinstance(detail, dict):
            continue
        avatar_path = detail.get("avatarPath")
        if isinstance(avatar_path, str):
            refs.append(avatar_path)

    external = sorted({ref for ref in refs if ref.startswith(("http://", "https://"))})
    non_local_sorted = sorted(set(non_local))
    local_refs = sorted({ref for ref in refs if ref and ref not in external})
    return local_refs, external, non_local_sorted


def validate_assets(book_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    base_dir = config.OUTPUT_DIR / "assets" / book_id
    local_refs, external, non_local = collect_asset_refs(data)
    missing: List[str] = []

    for ref in local_refs:
        if not (base_dir / ref).exists():
            missing.append(ref)

    return {
        "local_refs": len(local_refs),
        "external_refs": external,
        "non_local_objects": non_local,
        "missing": missing,
    }


def validate_staging_shape(data: Dict[str, Any]) -> List[str]:
    problems: List[str] = []
    object_fields = ["scores", "externalSource", "images", "related", "quotes", "excerpts", "otherTitles", "reviews"]
    for field in object_fields:
        value = data.get(field)
        if isinstance(value, str) and value.strip().startswith(("{", "[")):
            problems.append(f"staging 字段 {field} 已提前 JSON 字符串化")

    meta = data.get("_meta")
    if not isinstance(meta, dict):
        problems.append("staging 缺少 _meta 对象")
    else:
        if not isinstance(meta.get("fieldSources"), dict):
            problems.append("_meta.fieldSources 不是对象")
        if not isinstance(meta.get("conflicts"), list):
            problems.append("_meta.conflicts 不是数组")
        for key in ("authors", "translators", "tags", "subjects", "genres"):
            if meta.get(key) is not None and not isinstance(meta.get(key), list):
                problems.append(f"_meta.{key} 不是数组")

    return problems


def validate_content_quality(data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    problems: List[str] = []
    warnings: List[str] = []
    meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
    content_kind = meta.get("contentKind")

    for field in ("summary", "story"):
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            if field == "story" and content_kind == "nonfiction" and isinstance(data.get("summary"), str) and data["summary"].strip():
                warnings.append("story is missing; nonfiction uses summary as content outline")
                continue
            if field == "story" and content_kind == "web_novel" and isinstance(data.get("summary"), str) and data["summary"].strip():
                warnings.append("story is missing; web novel uses summary as whole-work outline")
                continue
            problems.append(f"{field} is missing")
            continue
        if not isinstance(value, str):
            problems.append(f"{field} is not text")
            continue
        text = value.strip()
        if text.endswith("...") or text.endswith("…") or "..." in text[-20:]:
            problems.append(f"{field} appears truncated with ellipsis")

    excerpts = data.get("excerpts") or []
    if isinstance(excerpts, list):
        seen_urls = set()
        seen_text = set()
        duplicate_urls = 0
        duplicate_text = 0
        for item in excerpts:
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            text = str(item.get("content") or "").strip()
            if url:
                if url in seen_urls:
                    duplicate_urls += 1
                seen_urls.add(url)
            if text:
                text_key = "".join(text.split())
                if text_key in seen_text:
                    duplicate_text += 1
                seen_text.add(text_key)
        if duplicate_urls or duplicate_text:
            problems.append(
                f"excerpts contain duplicates: duplicate_urls={duplicate_urls}, duplicate_text={duplicate_text}"
            )

    return problems, warnings


def dry_run_import(data: Dict[str, Any]) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_db = Path(temp_dir) / "treasure-book-precheck.db"
        shutil.copy2(DB_PATH, temp_db)

        db = BookDB(str(temp_db), promote_assets=False)
        result = db.import_book(data)
        db.close()

        conn = sqlite3.connect(temp_db)
        conn.row_factory = sqlite3.Row
        fk_problems = conn.execute("PRAGMA foreign_key_check").fetchall()
        book_person_count = conn.execute(
            "SELECT COUNT(*) AS count FROM book_person WHERE book_id = ?",
            (data["id"],),
        ).fetchone()["count"]
        book_category_count = conn.execute(
            "SELECT COUNT(*) AS count FROM book_category WHERE book_id = ?",
            (data["id"],),
        ).fetchone()["count"]
        conn.close()

        return {
            "result": result,
            "foreign_key_problems": len(fk_problems),
            "book_person": book_person_count,
            "book_category": book_category_count,
        }


def backup_database(book_id: str) -> Path:
    backup_dir = REPO_ROOT / ".local" / "backup"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = backup_dir / f"treasure-before-book-{book_id}-{stamp}.db"
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def precheck(book_id: str, data: Dict[str, Any], update_existing: bool = False) -> Dict[str, Any]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    max_id = get_db_max_book_id(conn)
    expected_id = expected_next_book_id(max_id)
    matches = find_existing_matches(conn, data)
    conn.close()

    assets = validate_assets(book_id, data)
    shape_problems = validate_staging_shape(data)
    quality_problems, quality_warnings = validate_content_quality(data)
    dry_run = dry_run_import(data) if update_existing or not matches else None

    problems: List[str] = []
    problems.extend(shape_problems)
    problems.extend(quality_problems)

    if update_existing:
        id_matches = [match for match in matches if match.get("id") == book_id]
        other_matches = [match for match in matches if match.get("id") != book_id]
        if not id_matches:
            problems.append("update-existing 模式下数据库中未找到同 ID 的已有书籍")
        if other_matches:
            problems.append("update-existing 模式下数据库中存在其他疑似匹配书籍")
        matches = []
        expected_id = data.get("id")
    else:
        if matches:
            problems.append("数据库中疑似已存在同一本书")
        if data.get("id") != expected_id:
            problems.append(f"书籍 ID 不是数据库下一条书籍 ID，当前 {data.get('id')}，预期 {expected_id}")

    if assets["missing"]:
        problems.append(f"本地资源缺失 {len(assets['missing'])} 个")
    if assets["external_refs"]:
        problems.append(f"仍存在外链资源引用 {len(assets['external_refs'])} 个")
    if assets["non_local_objects"]:
        problems.append(f"图片字段存在非本地文件引用 {len(assets['non_local_objects'])} 个")
    if dry_run and dry_run["foreign_key_problems"]:
        problems.append(f"临时库导入存在外键问题 {dry_run['foreign_key_problems']} 个")
    if dry_run and not dry_run["result"].get("success"):
        problems.append(f"临时库导入失败: {dry_run['result'].get('error')}")

    meta = data.get("_meta", {}) if isinstance(data.get("_meta"), dict) else {}
    return {
        "book_id": book_id,
        "title": data.get("title"),
        "title_original": data.get("titleOriginal"),
        "year": data.get("year"),
        "isbn": data.get("isbn"),
        "source_ids": collect_source_ids(data),
        "db_max_book_id": max_id,
        "expected_next_book_id": expected_id,
        "update_existing": update_existing,
        "matches": matches,
        "assets": assets,
        "authors": len(meta.get("authors") or []),
        "translators": len(meta.get("translators") or []),
        "tags": len(meta.get("tags") or []),
        "reviews": len(data.get("reviews") or []) if isinstance(data.get("reviews"), list) else 0,
        "field_sources": len(meta.get("fieldSources") or {}),
        "conflicts": len(meta.get("conflicts") or []),
        "dry_run": dry_run,
        "problems": problems,
        "warnings": quality_warnings,
    }


def apply_import(data: Dict[str, Any]) -> Dict[str, Any]:
    backup_path = backup_database(data["id"])
    db = BookDB()
    result = db.import_book(data)
    db.close()
    return {
        "backup": str(backup_path),
        "result": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="book-ingest staging 入库预检与正式导入")
    parser.add_argument("--book-id", required=True, help="待导入的书籍 ID")
    parser.add_argument("--apply", action="store_true", help="通过预检后正式写入 .local/treasure.db")
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="刷新数据库中同 ID 的已有书籍；只用于用户明确要求重新采集并覆盖入库的场景",
    )
    args = parser.parse_args()

    data = load_staging(args.book_id)
    report = precheck(args.book_id, data, update_existing=args.update_existing)
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
