# -*- coding: utf-8 -*-
"""
数据库管理模块 - 直接操作 treasure.db

表结构基于 Prisma Schema:
- works: 作品主表
- person: 人物主表
- work_person: 作品与人物关系表
- category: 类型/标签表
- work_category: 作品与类型/标签关联表
"""
import os
import sys

# Windows UTF-8 兼容：必须在其他 import 之前设置
if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

import sqlite3
import json
import re
import io
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from utils import Logger


class TreasureDB:
    """直接操作 treasure.db"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / ".local" / "treasure.db"
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        
    def connect(self):
        if not self.conn:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.row_factory = sqlite3.Row
            Logger.info(f"数据库已连接: {self.db_path}")
            
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            Logger.info("数据库已关闭")
    
    # ========================================
    # Work 表操作
    # ========================================
    
    def work_exists(self, work_id: str) -> bool:
        self.connect()
        cursor = self.conn.execute("SELECT id FROM works WHERE id = ?", (work_id,))
        return cursor.fetchone() is not None
    
    def get_work(self, work_id: str) -> Optional[Dict]:
        self.connect()
        cursor = self.conn.execute("SELECT * FROM works WHERE id = ?", (work_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def save_work(self, data: Dict[str, Any]) -> str:
        """
        保存作品数据到 works 表
        
        Args:
            data: 作品数据（staging JSON 格式）
            
        Returns:
            作品 ID
        """
        self.connect()
        
        work_id = data.get("id")
        if not work_id:
            raise ValueError("作品 ID 不能为空")
        
        now = datetime.now().isoformat()
        
        sql = """
        INSERT INTO works (
            id, module, submodule, schema_type, title, title_original,
            year, country, language, total_time, studio,
            introduction, story, other_titles, release_dates,
            external_source, scores, images, videos, comments,
            soundtrack, related, quotes, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            title_original = COALESCE(excluded.title_original, works.title_original),
            year = COALESCE(excluded.year, works.year),
            country = COALESCE(excluded.country, works.country),
            language = COALESCE(excluded.language, works.language),
            total_time = COALESCE(excluded.total_time, works.total_time),
            studio = COALESCE(excluded.studio, works.studio),
            introduction = COALESCE(excluded.introduction, works.introduction),
            story = COALESCE(excluded.story, works.story),
            other_titles = COALESCE(excluded.other_titles, works.other_titles),
            release_dates = COALESCE(excluded.release_dates, works.release_dates),
            external_source = COALESCE(excluded.external_source, works.external_source),
            scores = COALESCE(excluded.scores, works.scores),
            images = COALESCE(excluded.images, works.images),
            videos = COALESCE(excluded.videos, works.videos),
            comments = COALESCE(excluded.comments, works.comments),
            soundtrack = COALESCE(excluded.soundtrack, works.soundtrack),
            related = COALESCE(excluded.related, works.related),
            quotes = COALESCE(excluded.quotes, works.quotes),
            updated_at = excluded.updated_at
        """
        
        params = (
            work_id,
            "video",
            "movie",
            "live_action_movie",
            data.get("title", ""),
            data.get("originalTitle"),
            data.get("year"),
            data.get("country"),
            data.get("language"),
            data.get("runtime"),
            data.get("studio"),
            data.get("synopsis", {}).get("text") if isinstance(data.get("synopsis"), dict) else data.get("synopsis"),
            data.get("story", {}).get("text") if isinstance(data.get("story"), dict) else data.get("story"),
            self._to_json(data.get("aka")),
            self._to_json(data.get("releaseDate")),
            self._build_external_source(data),
            self._build_scores(data),
            self._to_json(data.get("images")),
            self._to_json(data.get("videos")),
            self._to_json(data.get("reviews")),
            self._to_json(data.get("soundtrack")),
            self._build_related(data),
            self._to_json(data.get("quotes")),
            "published",
            now,
            now
        )
        
        self.conn.execute(sql, params)
        self.conn.commit()
        
        Logger.success(f"已保存作品: {data.get('title')} ({work_id})")
        return work_id
    
    # ========================================
    # Person 表操作
    # ========================================
    
    def get_person_by_name(self, name: str, name_en: str = None) -> Optional[Dict]:
        """通过姓名查找人物"""
        self.connect()
        
        if name_en:
            cursor = self.conn.execute(
                "SELECT * FROM person WHERE name = ? AND name_en = ?",
                (name, name_en)
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM person WHERE name = ?",
                (name,)
            )
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_next_person_id(self) -> str:
        """获取下一个人物 ID（格式：p000001）"""
        self.connect()
        
        cursor = self.conn.execute(
            "SELECT person_id FROM person ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        
        if row:
            last_id = row["person_id"]
            match = re.match(r"p(\d+)", last_id)
            if match:
                next_num = int(match.group(1)) + 1
                return f"p{next_num:06d}"
        
        return "p000001"
    
    def save_person(self, data: Dict[str, Any], person_id: str = None) -> Tuple[int, str]:
        """
        保存人物数据到 person 表
        
        Args:
            data: 人物数据
            person_id: 人物 ID（可选，不提供则自动生成）
            
        Returns:
            (数据库主键 id, person_id)
        """
        self.connect()
        
        name = data.get("name", "")
        name_en = data.get("nameEn")
        
        existing = self.get_person_by_name(name, name_en)
        if existing:
            return existing["id"], existing["person_id"]
        
        if not person_id:
            person_id = self.get_next_person_id()
        
        avatar = data.get("avatar", "")
        avatar_path = None
        if avatar:
            ext = Path(avatar).suffix or ".jpg"
            avatar_path = f"people/{person_id}-avatar{ext}"
        
        profile_link = data.get("baike") or data.get("profileLink")
        
        sql = """
        INSERT INTO person (person_id, name, name_en, avatar_path, profile_link, intro)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        cursor = self.conn.execute(sql, (
            person_id, name, name_en, avatar_path, profile_link, None
        ))
        
        self.conn.commit()
        
        Logger.success(f"已保存人物: {name} ({person_id})")
        return cursor.lastrowid, person_id
    
    def save_persons_from_movie(self, movie_data: Dict[str, Any]) -> Dict[str, int]:
        """
        从电影数据中提取并保存所有人物
        
        Args:
            movie_data: 电影数据（staging JSON 格式）
            
        Returns:
            人物映射字典 {"name||nameEn": person_db_id}
        """
        person_map = {}
        
        groups = [
            movie_data.get("director", []),
            movie_data.get("writer", []),
            movie_data.get("cast", []),
            movie_data.get("otherCast", []),
            movie_data.get("producer", [])
        ]
        
        for group in groups:
            for person in group:
                if not person or not person.get("name"):
                    continue
                
                key = f"{person.get('name', '')}||{person.get('nameEn', '')}"
                if key not in person_map:
                    db_id, _ = self.save_person(person)
                    person_map[key] = db_id
        
        return person_map
    
    # ========================================
    # WorkPerson 表操作
    # ========================================
    
    def clear_work_persons(self, work_id: str):
        """清除作品的所有人物关联"""
        self.connect()
        self.conn.execute("DELETE FROM work_person WHERE work_id = ?", (work_id,))
    
    def save_work_person(self, work_id: str, person_db_id: int, department: str,
                         role: str = None, character: str = None, 
                         order: int = 0, is_primary: bool = False):
        """
        保存作品与人物的关联
        
        Args:
            work_id: 作品 ID
            person_db_id: 人物数据库主键 ID
            department: 部门（direction/writing/cast/production/music/original_work/other）
            role: 具体职位
            character: 角色名（演员专用）
            order: 排序
            is_primary: 是否主要人员
        """
        self.connect()
        
        sql = """
        INSERT INTO work_person (work_id, person_id, department, role, character, `order`, is_primary)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        
        self.conn.execute(sql, (
            work_id, person_db_id, department, role, character, order, 1 if is_primary else 0
        ))
    
    def save_work_persons_from_movie(self, work_id: str, movie_data: Dict[str, Any], 
                                      person_map: Dict[str, int]):
        """
        从电影数据中保存所有人物关联
        
        Args:
            work_id: 作品 ID
            movie_data: 电影数据
            person_map: 人物映射字典
        """
        self.clear_work_persons(work_id)
        
        order = 0
        
        for person in movie_data.get("director", []):
            key = f"{person.get('name', '')}||{person.get('nameEn', '')}"
            person_db_id = person_map.get(key)
            if person_db_id:
                self.save_work_person(
                    work_id, person_db_id, "direction", "导演",
                    order=order, is_primary=True
                )
                order += 1
        
        for person in movie_data.get("writer", []):
            key = f"{person.get('name', '')}||{person.get('nameEn', '')}"
            person_db_id = person_map.get(key)
            if person_db_id:
                role_text = person.get("role", "编剧")
                department = "original_work" if "原著" in role_text else "writing"
                self.save_work_person(
                    work_id, person_db_id, department, role_text,
                    order=order, is_primary=True
                )
                order += 1
        
        for person in movie_data.get("cast", []):
            key = f"{person.get('name', '')}||{person.get('nameEn', '')}"
            person_db_id = person_map.get(key)
            if person_db_id:
                self.save_work_person(
                    work_id, person_db_id, "cast", "主演",
                    character=person.get("role"),
                    order=order, is_primary=True
                )
                order += 1
        
        for person in movie_data.get("otherCast", []):
            key = f"{person.get('name', '')}||{person.get('nameEn', '')}"
            person_db_id = person_map.get(key)
            if person_db_id:
                self.save_work_person(
                    work_id, person_db_id, "cast", "演员",
                    character=person.get("role"),
                    order=order, is_primary=False
                )
                order += 1
        
        for person in movie_data.get("producer", []):
            key = f"{person.get('name', '')}||{person.get('nameEn', '')}"
            person_db_id = person_map.get(key)
            if person_db_id:
                role_text = person.get("role", "制片人")
                self.save_work_person(
                    work_id, person_db_id, "production", role_text,
                    order=order, is_primary=True
                )
                order += 1
        
        self.conn.commit()
        Logger.success(f"已保存 {order} 条人物关联: {work_id}")
    
    # ========================================
    # Category 表操作
    # ========================================
    
    def get_category(self, name: str, group: str, module: str = None, 
                     submodule: str = None) -> Optional[Dict]:
        """获取类型/标签"""
        self.connect()
        
        sql = "SELECT * FROM category WHERE name = ? AND `group` = ?"
        params = [name, group]
        
        if module:
            sql += " AND module = ?"
            params.append(module)
        else:
            sql += " AND module IS NULL"
        
        if submodule:
            sql += " AND submodule = ?"
            params.append(submodule)
        else:
            sql += " AND submodule IS NULL"
        
        cursor = self.conn.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def save_category(self, name: str, group: str, module: str = None, 
                      submodule: str = None) -> int:
        """
        保存类型/标签
        
        Args:
            name: 名称
            group: 分组（type/tag）
            module: 模块作用域
            submodule: 子模块作用域
            
        Returns:
            数据库主键 ID
        """
        self.connect()
        
        existing = self.get_category(name, group, module, submodule)
        if existing:
            return existing["id"]
        
        sql = """
        INSERT INTO category (`group`, name, module, submodule, `order`, enabled)
        VALUES (?, ?, ?, ?, 0, 1)
        """
        
        cursor = self.conn.execute(sql, (group, name, module, submodule))
        self.conn.commit()
        
        Logger.success(f"已保存类型/标签: {name} ({group})")
        return cursor.lastrowid
    
    def save_categories_from_movie(self, movie_data: Dict[str, Any]) -> Dict[str, int]:
        """
        从电影数据中提取并保存所有类型/标签
        
        Args:
            movie_data: 电影数据
            
        Returns:
            类型映射字典 {"name": category_db_id}
        """
        category_map = {}
        
        for genre in movie_data.get("genre", []):
            if genre and genre not in category_map:
                db_id = self.save_category(genre, "type", "video", "movie")
                category_map[genre] = db_id
        
        for tag in movie_data.get("tags", []):
            if tag and tag not in category_map:
                db_id = self.save_category(tag, "tag")
                category_map[tag] = db_id
        
        return category_map
    
    # ========================================
    # WorkCategory 表操作
    # ========================================
    
    def clear_work_categories(self, work_id: str):
        """清除作品的所有类型/标签关联"""
        self.connect()
        self.conn.execute("DELETE FROM work_category WHERE work_id = ?", (work_id,))
    
    def save_work_category(self, work_id: str, category_db_id: int, order: int = 0):
        """保存作品与类型/标签的关联"""
        self.connect()
        
        sql = """
        INSERT INTO work_category (work_id, category_id, `order`)
        VALUES (?, ?, ?)
        """
        
        self.conn.execute(sql, (work_id, category_db_id, order))
    
    def save_work_categories_from_movie(self, work_id: str, movie_data: Dict[str, Any],
                                         category_map: Dict[str, int]):
        """
        从电影数据中保存所有类型/标签关联
        
        Args:
            work_id: 作品 ID
            movie_data: 电影数据
            category_map: 类型映射字典
        """
        self.clear_work_categories(work_id)
        
        order = 0
        
        for genre in movie_data.get("genre", []):
            category_db_id = category_map.get(genre)
            if category_db_id:
                self.save_work_category(work_id, category_db_id, order)
                order += 1
        
        for tag in movie_data.get("tags", []):
            category_db_id = category_map.get(tag)
            if category_db_id:
                self.save_work_category(work_id, category_db_id, order)
                order += 1
        
        self.conn.commit()
        Logger.success(f"已保存 {order} 条类型关联: {work_id}")
    
    # ========================================
    # 批量导入
    # ========================================
    
    def import_movie(self, movie_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导入一部电影的所有数据（事务）
        
        Args:
            movie_data: 电影数据（staging JSON 格式）
            
        Returns:
            导入结果
        """
        self.connect()
        
        try:
            self.conn.execute("BEGIN TRANSACTION")
            
            work_id = self.save_work(movie_data)
            
            person_map = self.save_persons_from_movie(movie_data)
            
            self.save_work_persons_from_movie(work_id, movie_data, person_map)
            
            category_map = self.save_categories_from_movie(movie_data)
            
            self.save_work_categories_from_movie(work_id, movie_data, category_map)
            
            self.conn.commit()
            
            return {
                "success": True,
                "work_id": work_id,
                "title": movie_data.get("title"),
                "persons": len(person_map),
                "categories": len(category_map)
            }
            
        except Exception as e:
            self.conn.rollback()
            Logger.error(f"导入失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    # ========================================
    # 辅助方法
    # ========================================
    
    def _to_json(self, value: Any) -> Optional[str]:
        """转换为 JSON 字符串"""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)
    
    def _build_external_source(self, data: Dict[str, Any]) -> Optional[str]:
        """构建 external_source 字段"""
        sources = []
        
        douban_id = data.get("doubanId")
        if douban_id:
            sources.append({
                "name": "豆瓣",
                "id": douban_id,
                "link": f"https://movie.douban.com/subject/{douban_id}/"
            })
        
        imdb_id = data.get("imdbId")
        if imdb_id:
            sources.append({
                "name": "IMDb",
                "id": imdb_id,
                "link": f"https://www.imdb.com/title/{imdb_id}/"
            })
        
        tmdb_id = data.get("tmdbId")
        if tmdb_id:
            sources.append({
                "name": "TMDB",
                "id": str(tmdb_id),
                "link": f"https://www.themoviedb.org/movie/{tmdb_id}"
            })
        
        return self._to_json(sources) if sources else None
    
    def _build_scores(self, data: Dict[str, Any]) -> Optional[str]:
        """构建 scores 字段"""
        scores = {}
        
        if data.get("doubanRating"):
            scores["douban"] = data["doubanRating"]
        
        if data.get("imdbRating"):
            scores["imdb"] = data["imdbRating"]
        
        if data.get("tmdbRating"):
            scores["tmdb"] = data["tmdbRating"]
        
        if data.get("rottenTomatoes"):
            scores["rottenTomatoes"] = data["rottenTomatoes"]
        
        if data.get("metascore"):
            scores["metacritic"] = data["metascore"]
        
        if data.get("rated"):
            scores["certification"] = data["rated"]
        
        if data.get("awards"):
            scores["awards"] = data["awards"]
        
        if scores:
            valid_ratings = [v for k, v in scores.items() 
                           if k in ["douban", "imdb", "tmdb", "rottenTomatoes", "metacritic"] 
                           and isinstance(v, (int, float))]
            if valid_ratings:
                scores["avg"] = round(sum(valid_ratings) / len(valid_ratings), 1)
        
        return self._to_json(scores) if scores else None
    
    def _build_related(self, data: Dict[str, Any]) -> Optional[str]:
        """构建 related 字段"""
        related = {}
        
        similar = data.get("similar", [])
        if similar:
            related["similar"] = similar
        
        series = data.get("series", [])
        if series:
            related["series"] = series
        
        return self._to_json(related) if related else None
    
    # ========================================
    # 统计信息
    # ========================================
    
    def get_statistics(self) -> Dict[str, int]:
        """获取数据库统计"""
        self.connect()
        
        stats = {}
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM works")
        stats["works"] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM person")
        stats["person"] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM work_person")
        stats["work_person"] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM category")
        stats["category"] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM work_category")
        stats["work_category"] = cursor.fetchone()[0]
        
        return stats
