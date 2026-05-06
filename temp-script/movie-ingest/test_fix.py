# -*- coding: utf-8 -*-
"""
测试修复后的 TMDB 演职员获取
"""
import asyncio
import sys
import json
import sqlite3

sys.path.insert(0, '.')

from sources.tmdb import TMDBClient
from merger import DataMerger

async def test():
    # 测试 TMDB 客户端
    tmdb = TMDBClient()
    imdb_id = 'tt0111161'  # 肖申克的救赎
    
    print('1. 测试 TMDB API:')
    tmdb_data = await tmdb.get_all(imdb_id)
    
    credits = tmdb_data.get('credits', {})
    cast = len(credits.get('cast', []))
    crew = len(credits.get('crew', []))
    print(f'   Credits: cast={cast}, crew={crew}')
    
    # 测试数据合并
    print('\n2. 测试数据合并:')
    merger = DataMerger()
    
    raw_data = {
        'douban': {
            'title': '肖申克的救赎',
            'year': '1994',
            'rating': '9.7',
            'imdb_id': 'tt0111161',
            'summary': '测试简介'
        },
        'tmdb': tmdb_data
    }
    
    merged = merger.merge('0101000001', raw_data)
    
    merged_credits = merged.get('credits', {})
    merged_cast = len(merged_credits.get('cast', []))
    merged_crew = len(merged_credits.get('crew', []))
    print(f'   Merged credits: cast={merged_cast}, crew={merged_crew}')
    
    # 测试数据库保存
    print('\n3. 测试数据库保存:')
    conn = sqlite3.connect(r'F:\MyProject\Treasure\.local\crawled.db')
    
    # 删除旧记录
    conn.execute("DELETE FROM crawled_movies WHERE id = '0101000001'")
    conn.commit()
    
    # 插入新记录
    now = '2025-05-05'
    conn.execute(
        """
        INSERT INTO crawled_movies (
            id, douban_id, title, created_at, updated_at, crawl_status,
            credits_json
        ) VALUES (?, ?, ?, ?, ?, 'completed', ?)
        """,
        (
            '0101000001',
            '1292052',
            '肖申克的救赎',
            now,
            now,
            json.dumps(merged_credits, ensure_ascii=False)
        )
    )
    conn.commit()
    
    # 验证
    cursor = conn.execute(
        "SELECT credits_json FROM crawled_movies WHERE id = '0101000001'"
    )
    row = cursor.fetchone()
    if row:
        saved_credits = json.loads(row[0])
        saved_cast = len(saved_credits.get('cast', []))
        saved_crew = len(saved_credits.get('crew', []))
        print(f'   Saved credits: cast={saved_cast}, crew={saved_crew}')
        
        if saved_cast > 0:
            print(f'   First actor: {saved_credits["cast"][0]["name"]}')
    
    conn.close()
    
    print('\n✓ 测试完成')

if __name__ == '__main__':
    asyncio.run(test())