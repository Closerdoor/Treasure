# -*- coding: utf-8 -*-
"""
CSV 导出功能（来自 douban-top250）

功能：
1. 将数据库数据导出为 CSV 格式
2. 支持字段映射
3. 使用 utf-8-sig 编码（Excel 兼容）

集成位置：movie-ingest/database.py 添加 export_to_csv() 方法
"""

import csv
from pathlib import Path
from typing import List, Dict


def export_to_csv(data: List[Dict], filepath: str, fieldnames: List[str] = None):
    """
    导出数据到 CSV 文件
    
    Args:
        data: 数据列表（字典列表）
        filepath: 输出文件路径
        fieldnames: 字段名列表（可选，默认使用第一条记录的键）
    
    示例：
        movies = [
            {"id": "0101000001", "title": "星际穿越", "year": 2014},
            {"id": "0101000002", "title": "肖申克的救赎", "year": 1994}
        ]
        export_to_csv(movies, "output/movies.csv")
    """
    if not data:
        print("数据为空，跳过导出")
        return
    
    # 确保输出目录存在
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    # 如果没有指定字段名，使用第一条记录的键
    if not fieldnames:
        fieldnames = list(data[0].keys())
    
    # 使用 utf-8-sig 编码（Excel 兼容）
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"已导出 {len(data)} 条记录到 {filepath}")


def export_movies_to_csv(db_conn, output_dir: str = "output"):
    """
    从数据库导出电影数据到 CSV
    
    Args:
        db_conn: 数据库连接
        output_dir: 输出目录
    """
    import sqlite3
    
    # 查询所有已完成的电影
    cursor = db_conn.execute(
        """
        SELECT 
            id, douban_id, title, original_title, year, 
            country, language, runtime_minutes, 
            synopsis_text, story_text,
            crawl_status, created_at, updated_at
        FROM crawled_movies 
        WHERE crawl_status = 'completed'
        ORDER BY id
        """
    )
    
    # 获取列名
    columns = [desc[0] for desc in cursor.description]
    
    # 转换为字典列表
    movies = []
    for row in cursor.fetchall():
        movies.append(dict(zip(columns, row)))
    
    # 导出
    export_to_csv(movies, f"{output_dir}/movies.csv", columns)
    
    return len(movies)


def export_ratings_to_csv(db_conn, output_dir: str = "output"):
    """
    导出评分数据到 CSV（展开 JSON 字段）
    
    Args:
        db_conn: 数据库连接
        output_dir: 输出目录
    """
    import json
    
    cursor = db_conn.execute(
        """
        SELECT id, title, ratings_json 
        FROM crawled_movies 
        WHERE crawl_status = 'completed' AND ratings_json IS NOT NULL
        """
    )
    
    ratings_data = []
    for row in cursor.fetchall():
        movie_id, title, ratings_json = row
        
        try:
            ratings = json.loads(ratings_json)
            
            ratings_data.append({
                "id": movie_id,
                "title": title,
                "douban_rating": ratings.get("douban", {}).get("value", ""),
                "imdb_rating": ratings.get("imdb", {}).get("value", ""),
                "tmdb_rating": ratings.get("tmdb", {}).get("value", ""),
                "rotten_tomatoes": ratings.get("rottenTomatoes", {}).get("value", ""),
                "metascore": ratings.get("metascore", {}).get("value", ""),
                "aggregate": ratings.get("aggregate", {}).get("value", "")
            })
        except:
            continue
    
    export_to_csv(ratings_data, f"{output_dir}/ratings.csv")
    
    return len(ratings_data)


# 使用示例
if __name__ == "__main__":
    """
    集成到 movie-ingest/database.py:
    
    class DatabaseManager:
        def export_all_to_csv(self, output_dir: str = "output"):
            '''导出所有数据到 CSV'''
            self.connect()
            
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            # 导出电影数据
            count_movies = export_movies_to_csv(self.conn, output_dir)
            
            # 导出评分数据
            count_ratings = export_ratings_to_csv(self.conn, output_dir)
            
            print(f"导出完成：电影 {count_movies} 部，评分 {count_ratings} 条")
    
    # 使用：
    # db = DatabaseManager()
    # db.export_all_to_csv("output")
    """
    pass
