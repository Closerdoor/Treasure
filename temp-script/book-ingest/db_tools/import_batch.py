# -*- coding: utf-8 -*-
"""
数据库录入脚本 - 批量

批量录入 staging 目录下的所有书籍数据

使用方法：
python db_tools/import_batch.py --all
python db_tools/import_batch.py --all --dry-run
python db_tools/import_batch.py --ids 0200000001,0200000002
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from database import BookDB
from utils import Logger


def get_staging_books() -> list:
    """获取 staging 目录下所有书籍 ID"""
    staging_dir = Path(__file__).parent.parent / "data" / "staging"
    
    if not staging_dir.exists():
        return []
    
    book_ids = []
    for file in staging_dir.glob("*.json"):
        book_id = file.stem
        book_ids.append(book_id)
    
    return sorted(book_ids)


def import_batch(book_ids: list, dry_run: bool = False) -> dict:
    """
    批量录入书籍
    
    Args:
        book_ids: 书籍 ID 列表
        dry_run: 是否只预览不执行
        
    Returns:
        录入结果统计
    """
    staging_dir = Path(__file__).parent.parent / "data" / "staging"
    
    stats = {
        "total": len(book_ids),
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "errors": []
    }
    
    if dry_run:
        Logger.info("[DRY RUN] 预览模式，不实际录入")
    
    db = None
    if not dry_run:
        db = BookDB()
    
    for book_id in book_ids:
        staging_file = staging_dir / f"{book_id}.json"
        
        if not staging_file.exists():
            Logger.warning(f"跳过（文件不存在）: {book_id}")
            stats["skipped"] += 1
            continue
        
        try:
            book_data = json.loads(staging_file.read_text(encoding="utf-8"))
            title = book_data.get("title", book_id)
            
            Logger.info(f"处理: {title} ({book_id})")
            
            if dry_run:
                Logger.info(f"  书名: {title}")
                Logger.info(f"  作者: {book_data.get('_authors', [])}")
                stats["success"] += 1
            else:
                result = db.import_book(book_data)
                
                if result.get("success"):
                    Logger.success(f"录入成功: {title}")
                    stats["success"] += 1
                else:
                    Logger.error(f"录入失败: {result.get('error')}")
                    stats["failed"] += 1
                    stats["errors"].append({
                        "book_id": book_id,
                        "error": result.get("error")
                    })
                    
        except Exception as e:
            Logger.error(f"处理失败: {e}")
            stats["failed"] += 1
            stats["errors"].append({
                "book_id": book_id,
                "error": str(e)
            })
    
    if db:
        db.close()
    
    Logger.info("="*50)
    Logger.info(f"批量录入完成:")
    Logger.info(f"  总数: {stats['total']}")
    Logger.info(f"  成功: {stats['success']}")
    Logger.info(f"  失败: {stats['failed']}")
    Logger.info(f"  跳过: {stats['skipped']}")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="批量录入书籍到数据库")
    parser.add_argument("--all", action="store_true", help="录入 staging 目录下所有书籍")
    parser.add_argument("--ids", help="指定书籍 ID（逗号分隔）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际录入")
    
    args = parser.parse_args()
    
    if args.all:
        book_ids = get_staging_books()
        if not book_ids:
            Logger.warning("staging 目录下没有书籍数据")
            return
        Logger.info(f"发现 {len(book_ids)} 本书待录入")
    elif args.ids:
        book_ids = args.ids.split(",")
    else:
        Logger.error("请指定 --all 或 --ids")
        return
    
    import_batch(book_ids, args.dry_run)


if __name__ == "__main__":
    main()