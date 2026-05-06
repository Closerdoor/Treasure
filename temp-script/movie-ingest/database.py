# -*- coding: utf-8 -*-
"""
数据库管理模块
"""
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils import Logger


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_path: str = r"F:\MyProject\Treasure\.local\crawled.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        
    def connect(self):
        """连接数据库"""
        if not self.conn:
            self.conn = sqlite3.connect(str(self.db_path))
            # 启用 WAL 模式，支持并发读
            self.conn.execute("PRAGMA journal_mode=WAL")
            Logger.info(f"数据库已连接: {self.db_path}")
            
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            Logger.info("数据库已关闭")
            
    def create_table(self):
        """创建 crawled_movies 表"""
        sql = """
        CREATE TABLE IF NOT EXISTS crawled_movies (
            -- 主键
            id TEXT PRIMARY KEY,
            
            -- 基本信息（与 works 表一致）
            module TEXT NOT NULL DEFAULT 'video',
            submodule TEXT NOT NULL DEFAULT 'movie',
            schema_type TEXT NOT NULL DEFAULT 'live_action_movie',
            title TEXT NOT NULL,
            original_title TEXT,
            year INTEGER,
            country TEXT,
            language TEXT,
            runtime_minutes INTEGER,
            
            -- 简介（与 works 表一致）
            synopsis_text TEXT,
            synopsis_note TEXT,
            story_text TEXT,
            
            -- JSON 字段（与 works 表一致）
            aliases_json TEXT,
            release_dates_json TEXT,
            identifiers_json TEXT,
            ratings_json TEXT,
            links_json TEXT,
            images_json TEXT,
            videos_json TEXT,
            reviews_json TEXT,
            production_companies_json TEXT,
            
            -- 新增字段：演职人员（works 表在关联表中，这里合并存储）
            credits_json TEXT,
            
            -- 新增字段：豆瓣 ID（方便追溯）
            douban_id TEXT,
            
            -- 新增字段：类型标签
            genres_json TEXT,
            
            -- 新增字段：爬取元数据
            crawl_status TEXT NOT NULL DEFAULT 'pending',
            crawl_sources TEXT,
            crawl_errors TEXT,
            
            -- 新增字段：模块级别爬取状态
            basic_crawled INTEGER DEFAULT 0,
            reviews_crawled INTEGER DEFAULT 0,
            images_crawled INTEGER DEFAULT 0,
            
            -- 时间戳（与 works 表一致）
            status TEXT NOT NULL DEFAULT 'published',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        
        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_douban_id ON crawled_movies(douban_id);
        CREATE INDEX IF NOT EXISTS idx_crawl_status ON crawled_movies(crawl_status);
        CREATE INDEX IF NOT EXISTS idx_year ON crawled_movies(year);
        """
        
        self.connect()
        self.conn.executescript(sql)
        self.conn.commit()
        Logger.success("数据库表已创建")
        
    def init_movies(self, movies: List[Dict]):
        """
        初始化电影列表（批量插入 pending 状态的记录）
        
        Args:
            movies: 电影列表 [{douban_id, title, rank}, ...]
        """
        self.connect()
        
        now = datetime.now().isoformat()
        
        for movie in movies:
            douban_id = movie.get("douban_id", "")
            title = movie.get("title", "")
            
            # 检查是否已存在
            cursor = self.conn.execute(
                "SELECT id FROM crawled_movies WHERE douban_id = ?",
                (douban_id,)
            )
            if cursor.fetchone():
                continue
            
            # 生成 ID（使用豆瓣 ID 的数字部分）
            # 例如：douban_id = "1292052" -> id = "0101001292052"（前缀 + 豆瓣 ID）
            # 但为了保持一致性，使用递增 ID
            cursor = self.conn.execute("SELECT COUNT(*) FROM crawled_movies")
            count = cursor.fetchone()[0]
            movie_id = f"0101{count + 1:06d}"  # 0101 = 电影模块，后 6 位递增
            
            # 插入记录
            self.conn.execute(
                """
                INSERT INTO crawled_movies (
                    id, douban_id, title, created_at, updated_at, crawl_status
                ) VALUES (?, ?, ?, ?, ?, 'pending')
                """,
                (movie_id, douban_id, title, now, now)
            )
        
        self.conn.commit()
        Logger.success(f"已初始化 {len(movies)} 部电影")
        
    def get_pending_movies(self) -> List[Dict]:
        """获取待爬取的电影列表"""
        self.connect()
        
        cursor = self.conn.execute(
            """
            SELECT id, douban_id, title 
            FROM crawled_movies 
            WHERE crawl_status = 'pending'
            ORDER BY id
            """
        )
        
        movies = []
        for row in cursor.fetchall():
            movies.append({
                "id": row[0],
                "douban_id": row[1],
                "title": row[2]
            })
        
        return movies
        
    def save_movie(self, movie_id: str, data: Dict[str, Any], sources: List[str], errors: List[str]):
        """
        保存电影数据
        
        Args:
            movie_id: 电影 ID
            data: 电影数据
            sources: 成功的数据源
            errors: 错误信息
        """
        self.connect()
        
        now = datetime.now().isoformat()
        
        # 准备 JSON 字段
        def to_json(value):
            if value is None:
                return None
            if isinstance(value, str):
                return value
            return json.dumps(value, ensure_ascii=False)
        
        # 检查记录是否存在
        cursor = self.conn.execute(
            "SELECT id FROM crawled_movies WHERE id = ?",
            (movie_id,)
        )
        exists = cursor.fetchone() is not None
        
        if not exists:
            # 插入新记录
            insert_sql = """
            INSERT INTO crawled_movies (
                id, douban_id, title, created_at, updated_at, crawl_status
            ) VALUES (?, ?, ?, ?, ?, 'pending')
            """
            self.conn.execute(insert_sql, (
                movie_id,
                data.get("identifiers_json", {}).get("douban") if isinstance(data.get("identifiers_json"), dict) else None,
                data.get("title"),
                now,
                now
            ))
        
        # 更新记录
        sql = """
        UPDATE crawled_movies SET
            module = ?,
            submodule = ?,
            schema_type = ?,
            title = ?,
            original_title = ?,
            year = ?,
            country = ?,
            language = ?,
            runtime_minutes = ?,
            synopsis_text = ?,
            synopsis_note = ?,
            story_text = ?,
            aliases_json = ?,
            release_dates_json = ?,
            identifiers_json = ?,
            ratings_json = ?,
            links_json = ?,
            images_json = ?,
            videos_json = ?,
            reviews_json = ?,
            production_companies_json = ?,
            credits_json = ?,
            genres_json = ?,
            crawl_status = ?,
            crawl_sources = ?,
            crawl_errors = ?,
            updated_at = ?
        WHERE id = ?
        """
        
        params = (
            data.get("module", "video"),
            data.get("submodule", "movie"),
            data.get("schema_type", "live_action_movie"),
            data.get("title"),
            data.get("original_title"),
            data.get("year"),
            data.get("country"),
            data.get("language"),
            data.get("runtime_minutes"),
            data.get("synopsis_text"),
            data.get("synopsis_note", ""),
            data.get("story_text"),
            to_json(data.get("aliases_json")),
            to_json(data.get("release_dates_json")),
            to_json(data.get("identifiers_json")),
            to_json(data.get("ratings_json")),
            to_json(data.get("links_json")),
            to_json(data.get("images_json")),
            to_json(data.get("videos_json")),
            to_json(data.get("reviews_json")),
            to_json(data.get("production_companies_json")),
            to_json(data.get("credits")),
            to_json(data.get("genres")),
            "completed" if not errors else "partial",
            to_json(sources),
            to_json(errors),
            now,
            movie_id
        )
        
        self.conn.execute(sql, params)
        self.conn.commit()
        
        Logger.success(f"已保存电影数据: {data.get('title')} ({movie_id})")
        
    def get_movie_basic_info(self, movie_id: str) -> Optional[Dict]:
        """获取电影基本信息（用于评论和图片爬取）"""
        self.connect()
        
        cursor = self.conn.execute(
            """
            SELECT title, original_title, year, identifiers_json
            FROM crawled_movies WHERE id = ?
            """,
            (movie_id,)
        )
        
        row = cursor.fetchone()
        
        if row:
            return {
                "title": row[0],
                "original_title": row[1],
                "year": row[2],
                "identifiers_json": json.loads(row[3]) if row[3] else {}
            }
        
        return None
        
    def get_movie_by_douban_id(self, douban_id: str) -> Optional[Dict]:
        """通过豆瓣 ID 获取电影"""
        self.connect()
        
        cursor = self.conn.execute(
            "SELECT id, douban_id, title FROM crawled_movies WHERE douban_id = ?",
            (douban_id,)
        )
        
        row = cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "douban_id": row[1],
                "title": row[2]
            }
        
        return None
        
    def get_all_movies(self) -> List[Dict]:
        """获取所有电影"""
        self.connect()
        
        cursor = self.conn.execute(
            "SELECT id, douban_id, title FROM crawled_movies ORDER BY id"
        )
        
        movies = []
        for row in cursor.fetchall():
            movies.append({
                "id": row[0],
                "douban_id": row[1],
                "title": row[2]
            })
        
        return movies
        
    def get_movies_missing_reviews(self) -> List[Dict]:
        """获取缺失评论的电影"""
        self.connect()
        
        cursor = self.conn.execute(
            """
            SELECT id, douban_id, title 
            FROM crawled_movies 
            WHERE reviews_crawled = 0 OR reviews_crawled IS NULL
            ORDER BY id
            """
        )
        
        movies = []
        for row in cursor.fetchall():
            movies.append({
                "id": row[0],
                "douban_id": row[1],
                "title": row[2]
            })
        
        return movies
        
    def get_movies_missing_images(self) -> List[Dict]:
        """获取缺失图片的电影"""
        self.connect()
        
        cursor = self.conn.execute(
            """
            SELECT id, douban_id, title 
            FROM crawled_movies 
            WHERE images_crawled = 0 OR images_crawled IS NULL
            ORDER BY id
            """
        )
        
        movies = []
        for row in cursor.fetchall():
            movies.append({
                "id": row[0],
                "douban_id": row[1],
                "title": row[2]
            })
        
        return movies
        
    def update_movie_reviews(self, movie_id: str, reviews_data: Dict):
        """更新电影评论数据"""
        self.connect()
        
        now = datetime.now().isoformat()
        
        self.conn.execute(
            """
            UPDATE crawled_movies 
            SET reviews_json = ?, reviews_crawled = 1, updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(reviews_data, ensure_ascii=False), now, movie_id)
        )
        
        self.conn.commit()
        Logger.success(f"已更新评论数据: {movie_id}")
        
    def update_movie_images(self, movie_id: str, images_data: Dict):
        """更新电影图片数据"""
        self.connect()
        
        now = datetime.now().isoformat()
        
        # 合并到 images_json
        cursor = self.conn.execute(
            "SELECT images_json FROM crawled_movies WHERE id = ?",
            (movie_id,)
        )
        
        row = cursor.fetchone()
        existing_images = json.loads(row[0]) if row and row[0] else {}
        
        # 更新图片列表
        if images_data.get("posters"):
            existing_images["posters"] = images_data["posters"]
        if images_data.get("stills"):
            existing_images["stills"] = images_data["stills"]
        
        self.conn.execute(
            """
            UPDATE crawled_movies 
            SET images_json = ?, images_crawled = 1, updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(existing_images, ensure_ascii=False), now, movie_id)
        )
        
        self.conn.commit()
        Logger.success(f"已更新图片数据: {movie_id}")
        
    def mark_basic_crawled(self, movie_id: str):
        """标记基本信息已爬取"""
        self.connect()
        
        self.conn.execute(
            "UPDATE crawled_movies SET basic_crawled = 1 WHERE id = ?",
            (movie_id,)
        )
        
        self.conn.commit()
        
    def mark_reviews_crawled(self, movie_id: str):
        """标记评论已爬取"""
        self.connect()
        
        self.conn.execute(
            "UPDATE crawled_movies SET reviews_crawled = 1 WHERE id = ?",
            (movie_id,)
        )
        
        self.conn.commit()
        
    def mark_images_crawled(self, movie_id: str):
        """标记图片已爬取"""
        self.connect()
        
        self.conn.execute(
            "UPDATE crawled_movies SET images_crawled = 1 WHERE id = ?",
            (movie_id,)
        )
        
        self.conn.commit()
        
    def get_statistics(self) -> Dict:
        """获取爬取统计"""
        self.connect()
        
        cursor = self.conn.execute(
            """
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN crawl_status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN crawl_status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN crawl_status = 'partial' THEN 1 ELSE 0 END) as partial
            FROM crawled_movies
            """
        )
        
        row = cursor.fetchone()
        
        return {
            "total": row[0],
            "completed": row[1],
            "pending": row[2],
            "partial": row[3]
        }
        
    def get_movie(self, movie_id: str) -> Optional[Dict]:
        """获取单部电影数据"""
        self.connect()
        
        cursor = self.conn.execute(
            "SELECT * FROM crawled_movies WHERE id = ?",
            (movie_id,)
        )
        
        row = cursor.fetchone()
        if not row:
            return None
            
        # 获取列名
        columns = [desc[0] for desc in cursor.description]
        
        return dict(zip(columns, row))
