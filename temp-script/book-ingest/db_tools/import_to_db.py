# -*- coding: utf-8 -*-
"""
数据库录入脚本 - 单本书

将 staging 目录下的合并数据录入数据库

使用方法：
python db_tools/import_to_db.py --book-id 0200000001
python db_tools/import_to_db.py --book-id 0200000001 --dry-run
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from database import BookDB
from utils import Logger


def import_book(book_id: str, dry_run: bool = False) -> dict:
    staging_dir = Path(config.OUTPUT_DIR) / "staging"
    staging_file = staging_dir / f"{book_id}.json"

    if not staging_file.exists():
        Logger.error(f"staging 文件不存在: {staging_file}")
        return {"success": False, "error": "staging 文件不存在"}

    try:
        book_data = json.loads(staging_file.read_text(encoding="utf-8"))
    except Exception as e:
        Logger.error(f"读取 staging 文件失败: {e}")
        return {"success": False, "error": f"读取文件失败: {e}"}

    meta = book_data.get("_meta", {})
    Logger.info(f"准备入库: {book_data.get('title', book_id)}")

    if dry_run:
        Logger.info("[DRY RUN] 预览模式，不实际入库")
        Logger.info(f"  书籍 ID: {book_id}")
        Logger.info(f"  书名: {book_data.get('title')}")
        Logger.info(f"  作者: {meta.get('authors', [])}")
        Logger.info(f"  译者: {meta.get('translators', [])}")
        Logger.info(f"  标签: {meta.get('tags', [])}")
        Logger.info(f"  字段来源: {meta.get('fieldSources', {})}")
        Logger.info(f"  冲突: {meta.get('conflicts', [])}")
        return {"success": True, "dry_run": True}

    db = BookDB()
    result = db.import_book(book_data)
    db.close()

    if result.get("success"):
        Logger.success(f"入库成功: {book_data.get('title')} ({book_id})")
        Logger.info(f"  人物: {result.get('persons', 0)}")
        Logger.info(f"  标签: {result.get('categories', 0)}")
    else:
        Logger.error(f"入库失败: {result.get('error')}")

    return result


def main():
    parser = argparse.ArgumentParser(description="录入单本书到数据库")
    parser.add_argument("--book-id", required=True, help="书籍 ID")
    parser.add_argument("--dry-run", action="store_true", help="预览模式")

    args = parser.parse_args()
    import_book(args.book_id, args.dry_run)


if __name__ == "__main__":
    main()