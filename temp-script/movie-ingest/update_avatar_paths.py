# -*- coding: utf-8 -*-
"""
更新数据库中人物的头像路径

从已有的 staging JSON 文件中提取头像信息，更新到数据库
"""
import os
import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime

if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

# 路径配置
REPO_ROOT = Path(__file__).parent.parent.parent
DB_PATH = REPO_ROOT / ".local" / "treasure.db"
STAGING_DIR = REPO_ROOT / ".local" / "staging" / "video" / "movie"

def main():
    print("=== 更新人物头像路径 ===")
    print(f"数据库: {DB_PATH}")
    print(f"数据目录: {STAGING_DIR}")
    
    # 连接数据库
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 统计
    total_updated = 0
    total_skipped = 0
    
    # 遍历所有 staging JSON 文件
    json_files = list(STAGING_DIR.glob("*.json"))
    print(f"\n找到 {len(json_files)} 个数据文件")
    
    for json_file in json_files:
        work_id = json_file.stem
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 提取所有人物
        all_persons = []
        all_persons.extend(data.get('director', []))
        all_persons.extend(data.get('writer', []))
        all_persons.extend(data.get('cast', []))
        all_persons.extend(data.get('otherCast', []))
        
        for person in all_persons:
            name = person.get('name')
            name_en = person.get('nameEn')
            avatar = person.get('avatar')
            
            if not name or not avatar:
                continue
            
            # 查找数据库中的人物
            if name_en:
                cursor.execute(
                    "SELECT id, person_id, avatar_path FROM person WHERE name = ? AND name_en = ?",
                    (name, name_en)
                )
            else:
                cursor.execute(
                    "SELECT id, person_id, avatar_path FROM person WHERE name = ?",
                    (name,)
                )
            
            row = cursor.fetchone()
            
            if not row:
                continue
            
            # 如果已有头像，跳过
            if row['avatar_path']:
                total_skipped += 1
                continue
            
            # 生成头像路径
            person_id = row['person_id']
            ext = Path(avatar).suffix or '.jpg'
            avatar_path = f"people/{person_id}-avatar{ext}"
            
            # 更新数据库
            cursor.execute(
                "UPDATE person SET avatar_path = ? WHERE id = ?",
                (avatar_path, row['id'])
            )
            
            total_updated += 1
            print(f"  更新: {name} -> {avatar_path}")
    
    # 提交更改
    conn.commit()
    conn.close()
    
    print(f"\n=== 完成 ===")
    print(f"更新: {total_updated} 人")
    print(f"跳过: {total_skipped} 人 (已有头像)")

if __name__ == "__main__":
    main()
