# -*- coding: utf-8 -*-
"""
重试失败的电影
"""
import asyncio
import aiohttp
import json
import sqlite3
from pathlib import Path

TMDB_API_KEY = '3a4e78fb56ab8fda8244aa3c96272534'
PROXY_URL = 'http://127.0.0.1:7890'
DB_PATH = Path(__file__).parent.parent.parent / ".local" / "treasure.db"

FAILED_MOVIES = [
    {'work_id': '0101000033', 'tmdb_id': '532753', 'title': '我不是药神'},
]


async def fetch_credits(tmdb_id: str) -> dict:
    url = f'https://api.themoviedb.org/3/movie/{tmdb_id}/credits'
    params = {'api_key': TMDB_API_KEY}
    
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.get(url, params=params, proxy=PROXY_URL, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                return await response.json()
            else:
                print(f'请求失败: {response.status}')
                return None


def normalize_name(name: str) -> str:
    if not name:
        return ""
    return name.lower().strip()


def reverse_name(name: str) -> str:
    """反转名字顺序：Wen Muye -> Muye Wen"""
    parts = name.strip().split()
    if len(parts) == 2:
        return f"{parts[1]} {parts[0]}"
    return name


def match_person(name_en: str, conn) -> dict:
    normalized = normalize_name(name_en)
    
    # 尝试直接匹配
    cursor = conn.execute(
        "SELECT id, person_id, name, name_en, source_ids FROM person WHERE LOWER(name_en) = ?",
        (normalized,)
    )
    rows = cursor.fetchall()
    
    if len(rows) == 1:
        return dict(rows[0])
    elif len(rows) > 1:
        print(f'  [WARN] 英文名重复: {name_en} ({len(rows)} 个)')
        return dict(rows[0])
    
    # 尝试反转名字匹配（Wen Muye -> Muye Wen）
    reversed_name = reverse_name(name_en)
    reversed_normalized = normalize_name(reversed_name)
    
    cursor = conn.execute(
        "SELECT id, person_id, name, name_en, source_ids FROM person WHERE LOWER(name_en) = ?",
        (reversed_normalized,)
    )
    rows = cursor.fetchall()
    
    if len(rows) == 1:
        return dict(rows[0])
    elif len(rows) > 1:
        print(f'  [WARN] 英文名重复（反转）: {name_en} ({len(rows)} 个)')
        return dict(rows[0])
    
    return None


def update_person(person_db_id: int, tmdb_id: str, tmdb_avatar_path: str, conn):
    cursor = conn.execute(
        "SELECT source_ids FROM person WHERE id = ?",
        (person_db_id,)
    )
    row = cursor.fetchone()
    
    current_source_ids = {}
    if row and row['source_ids']:
        try:
            current_source_ids = json.loads(row['source_ids'])
        except:
            pass
    
    current_source_ids['tmdb'] = tmdb_id
    
    conn.execute("""
        UPDATE person 
        SET source_ids = ?,
            tmdb_avatar_path = ?,
            avatar_path = COALESCE(avatar_path, ?)
        WHERE id = ?
    """, (
        json.dumps(current_source_ids),
        tmdb_avatar_path,
        tmdb_avatar_path,
        person_db_id
    ))
    
    conn.commit()


async def process_movie(movie: dict, conn):
    print(f"处理: {movie['title']} ({movie['work_id']})")
    
    credits = await fetch_credits(movie['tmdb_id'])
    
    if not credits:
        print(f"  [FAIL] 无法获取 credits")
        return
    
    cast = credits.get('cast', [])
    crew = credits.get('crew', [])
    
    print(f"  cast: {len(cast)}, crew: {len(crew)}")
    
    updated = 0
    
    # 处理演员
    for actor in cast:
        tmdb_person_id = str(actor.get('id', ''))
        name_en = actor.get('name', '')
        
        if not tmdb_person_id or not name_en:
            continue
        
        matched = match_person(name_en, conn)
        
        if matched:
            avatar_path = f"people/tmdb-{tmdb_person_id}-avatar.jpg"
            update_person(matched['id'], tmdb_person_id, avatar_path, conn)
            print(f"  [OK] {name_en} -> {matched['name']}")
            updated += 1
    
    # 处理导演
    directors = [c for c in crew if c.get('job') == 'Director']
    for director in directors:
        tmdb_person_id = str(director.get('id', ''))
        name_en = director.get('name', '')
        
        if not tmdb_person_id or not name_en:
            continue
        
        matched = match_person(name_en, conn)
        
        if matched:
            avatar_path = f"people/tmdb-{tmdb_person_id}-avatar.jpg"
            update_person(matched['id'], tmdb_person_id, avatar_path, conn)
            print(f"  [OK] {name_en} -> {matched['name']} (导演)")
            updated += 1
    
    print(f"  更新: {updated} 人")


async def main():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    for movie in FAILED_MOVIES:
        await process_movie(movie, conn)
        await asyncio.sleep(1)
    
    conn.close()
    print("完成")


if __name__ == '__main__':
    asyncio.run(main())