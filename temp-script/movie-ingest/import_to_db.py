# -*- coding: utf-8 -*-
"""
导入 staging JSON 到 treasure.db

使用方法：
python import_to_db.py --work-id 0101000001
python import_to_db.py --all
python import_to_db.py --missing
"""
import os
import sys

# Windows UTF-8 兼容：必须在其他 import 之前设置
if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

import argparse
import json
import io
from pathlib import Path
from typing import Dict, List, Any

from database import TreasureDB
from utils import Logger


def load_staging_file(work_id: str, staging_dir: Path) -> Dict[str, Any]:
    """加载 staging JSON 文件"""
    filepath = staging_dir / f"{work_id}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"Staging 文件不存在: {filepath}")
    
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def get_all_staging_files(staging_dir: Path) -> List[str]:
    """获取所有 staging 文件的 work_id"""
    if not staging_dir.exists():
        return []
    
    work_ids = []
    for filepath in staging_dir.glob("*.json"):
        work_ids.append(filepath.stem)
    
    return sorted(work_ids)


def import_work(db: TreasureDB, work_id: str, staging_dir: Path) -> Dict[str, Any]:
    """导入单部作品"""
    try:
        data = load_staging_file(work_id, staging_dir)
        result = db.import_movie(data)
        return result
    except FileNotFoundError as e:
        return {"success": False, "work_id": work_id, "error": str(e)}
    except Exception as e:
        return {"success": False, "work_id": work_id, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="导入 staging JSON 到 treasure.db")
    parser.add_argument("--work-id", type=str, help="指定作品 ID 导入")
    parser.add_argument("--all", action="store_true", help="导入所有 staging 文件")
    parser.add_argument("--missing", action="store_true", help="只导入数据库中不存在的作品")
    parser.add_argument("--dry-run", action="store_true", help="只检查，不实际导入")
    
    args = parser.parse_args()
    
    staging_dir = Path(__file__).parent.parent.parent / ".local" / "staging" / "video" / "movie"
    db = TreasureDB()
    
    if args.work_id:
        Logger.info(f"导入单部作品: {args.work_id}")
        
        if args.dry_run:
            try:
                data = load_staging_file(args.work_id, staging_dir)
                Logger.success(f"[Dry Run] 文件存在: {args.work_id}")
                Logger.info(f"  标题: {data.get('title')}")
                Logger.info(f"  年份: {data.get('year')}")
                Logger.info(f"  导演: {len(data.get('director', []))} 人")
                Logger.info(f"  演员: {len(data.get('cast', []))} 人")
            except FileNotFoundError as e:
                Logger.error(str(e))
        else:
            result = import_work(db, args.work_id, staging_dir)
            if result.get("success"):
                Logger.success(f"导入成功: {result.get('title')} ({args.work_id})")
                Logger.info(f"  人物: {result.get('persons')} 条")
                Logger.info(f"  类型: {result.get('categories')} 条")
            else:
                Logger.error(f"导入失败: {result.get('error')}")
    
    elif args.all or args.missing:
        work_ids = get_all_staging_files(staging_dir)
        
        if not work_ids:
            Logger.warning("没有找到 staging 文件")
            return
        
        Logger.info(f"找到 {len(work_ids)} 个 staging 文件")
        
        if args.missing:
            missing_ids = []
            for work_id in work_ids:
                if not db.work_exists(work_id):
                    missing_ids.append(work_id)
            work_ids = missing_ids
            Logger.info(f"其中 {len(work_ids)} 个不在数据库中")
        
        if args.dry_run:
            Logger.info("[Dry Run] 将导入以下作品:")
            for work_id in work_ids:
                try:
                    data = load_staging_file(work_id, staging_dir)
                    exists = db.work_exists(work_id)
                    status = "已存在" if exists else "待导入"
                    Logger.info(f"  {work_id}: {data.get('title')} [{status}]")
                except:
                    Logger.warning(f"  {work_id}: 加载失败")
        else:
            success_count = 0
            fail_count = 0
            
            for work_id in work_ids:
                result = import_work(db, work_id, staging_dir)
                if result.get("success"):
                    success_count += 1
                    Logger.success(f"  {work_id}: {result.get('title')}")
                else:
                    fail_count += 1
                    Logger.error(f"  {work_id}: {result.get('error')}")
            
            Logger.info("="*60)
            Logger.info(f"导入完成: 成功 {success_count}，失败 {fail_count}")
            
            stats = db.get_statistics()
            Logger.info(f"数据库统计: works={stats['works']}, person={stats['person']}, work_person={stats['work_person']}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
