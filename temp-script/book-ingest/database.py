# -*- coding: utf-8 -*-
"""
数据库管理模块
"""
import os
import sys

if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

import sqlite3
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from utils import Logger


class BookDB:
    """书籍数据库操作"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / ".local" / "treasure.db"
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        
    def connect(self):
        """连接数据库"""
        if not self.conn:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.row_factory = sqlite3.Row
            Logger.info(f"数据库已连接: {self.db_path}")
            
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
            Logger.info("数据库已关闭")
    
    # ========================================
    # Book 表操作
    # ========================================
    
    def book_exists(self, book_id: str) -> bool:
        """检查书籍是否存在"""
        self.connect()
        cursor = self.conn.execute("SELECT id FROM books WHERE id = ?", (book_id,))
        return cursor.fetchone() is not None
    
    def get_book(self, book_id: str) -> Optional[Dict]:
        """获取书籍"""
        self.connect()
        cursor = self.conn.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def save_book(self, data: Dict[str, Any]) -> str:
        """
        保存书籍数据
        
        Args:
            data: 书籍数据
            
        Returns:
            书籍 ID
        """
        self.connect()
        
        book_id = data.get("id")
        isbn = data.get("isbn")
        
        if not book_id:
            raise ValueError("书籍 ID 不能为空")
        
        now = datetime.now().isoformat()
        
        # 检查 ISBN 是否已存在
        if isbn:
            cursor = self.conn.execute(
                "SELECT id FROM books WHERE isbn = ?",
                (isbn,)
            )
            existing = cursor.fetchone()
            if existing:
                # ISBN 已存在，直接更新现有记录
                existing_id = existing["id"]
                Logger.warning(f"ISBN {isbn} 已存在，更新记录 {existing_id}")
                
                update_sql = """
                UPDATE books SET
                    title = ?,
                    title_original = COALESCE(?, title_original),
                    other_titles = COALESCE(?, other_titles),
                    year = COALESCE(?, year),
                    country = COALESCE(?, country),
                    language = COALESCE(?, language),
                    word_count = COALESCE(?, word_count),
                    publisher = COALESCE(?, publisher),
                    summary = COALESCE(?, summary),
                    quotes = COALESCE(?, quotes),
                    scores = COALESCE(?, scores),
                    external_source = COALESCE(?, external_source),
                    images = COALESCE(?, images),
                    reviews = COALESCE(?, reviews),
                    related = COALESCE(?, related),
                    updated_at = ?
                WHERE id = ?
                """
                
                update_params = (
                    data.get("title", ""),
                    data.get("titleOriginal"),
                    data.get("otherTitles"),
                    data.get("year"),
                    data.get("country"),
                    data.get("language"),
                    data.get("wordCount"),
                    data.get("publisher"),
                    data.get("summary"),
                    data.get("quotes"),
                    data.get("scores"),
                    data.get("externalSource"),
                    data.get("images"),
                    data.get("reviews"),
                    data.get("related"),
                    now,
                    existing_id
                )
                
                self.conn.execute(update_sql, update_params)
                self.conn.commit()
                
                Logger.success(f"已更新书籍: {data.get('title')} ({existing_id})")
                return existing_id
        
        # 新书籍，插入
        sql = """
        INSERT INTO books (
            id, title, title_original, other_titles, isbn, year, country,
            language, word_count, publisher, summary, quotes, series_id,
            series_order, scores, external_source, images, reviews, related,
            status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            title_original = COALESCE(excluded.title_original, books.title_original),
            other_titles = COALESCE(excluded.other_titles, books.other_titles),
            isbn = COALESCE(excluded.isbn, books.isbn),
            year = COALESCE(excluded.year, books.year),
            country = COALESCE(excluded.country, books.country),
            language = COALESCE(excluded.language, books.language),
            word_count = COALESCE(excluded.word_count, books.word_count),
            publisher = COALESCE(excluded.publisher, books.publisher),
            summary = COALESCE(excluded.summary, books.summary),
            quotes = COALESCE(excluded.quotes, books.quotes),
            scores = COALESCE(excluded.scores, books.scores),
            external_source = COALESCE(excluded.external_source, books.external_source),
            images = COALESCE(excluded.images, books.images),
            reviews = COALESCE(excluded.reviews, books.reviews),
            related = COALESCE(excluded.related, books.related),
            updated_at = excluded.updated_at
        """
        
        params = (
            book_id,
            data.get("title", ""),
            data.get("titleOriginal"),
            data.get("otherTitles"),
            data.get("isbn"),
            data.get("year"),
            data.get("country"),
            data.get("language"),
            data.get("wordCount"),
            data.get("publisher"),
            data.get("summary"),
            data.get("quotes"),
            data.get("seriesId"),
            data.get("seriesOrder"),
            data.get("scores"),
            data.get("externalSource"),
            data.get("images"),
            data.get("reviews"),
            data.get("related"),
            data.get("status", "draft"),
            now,
            now
        )
        
        self.conn.execute(sql, params)
        self.conn.commit()
        
        Logger.success(f"已保存书籍: {data.get('title')} ({book_id})")
        return book_id
    
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
        """获取下一个人物 ID"""
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
        保存人物
        
        Args:
            data: 人物数据
            person_id: 人物 ID（可选）
            
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
        
        sql = """
        INSERT INTO person (person_id, name, name_en, avatar_path, profile_link, intro)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        
        cursor = self.conn.execute(sql, (
            person_id, name, name_en, 
            data.get("avatarPath"), 
            data.get("profileLink"), 
            data.get("intro")
        ))
        
        self.conn.commit()
        
        Logger.success(f"已保存人物: {name} ({person_id})")
        return cursor.lastrowid, person_id
    
    # ========================================
    # BookPerson 表操作
    # ========================================
    
    def clear_book_persons(self, book_id: str):
        """清除书籍的所有人物关联"""
        self.connect()
        self.conn.execute("DELETE FROM book_person WHERE book_id = ?", (book_id,))
    
    def save_book_person(self, book_id: str, person_db_id: int, role: str,
                         order: int = 0, is_primary: bool = False):
        """保存书籍与人物的关联"""
        self.connect()
        
        sql = """
        INSERT INTO book_person (book_id, person_id, role, "order", is_primary)
        VALUES (?, ?, ?, ?, ?)
        """
        
        self.conn.execute(sql, (
            book_id, person_db_id, role, order, 1 if is_primary else 0
        ))
    
    def save_book_persons(self, book_id: str, book_data: Dict[str, Any], 
                          person_map: Dict[str, int]):
        """
        保存书籍的所有人物关联
        
        Args:
            book_id: 书籍 ID
            book_data: 书籍数据
            person_map: 人物映射 {"name||nameEn": person_db_id}
        """
        self.clear_book_persons(book_id)
        
        order = 0
        
        # 作者
        authors = book_data.get("_authors", [])
        for author in authors:
            key = f"{author}||"
            person_db_id = person_map.get(key)
            if person_db_id:
                self.save_book_person(
                    book_id, person_db_id, "author",
                    order=order, is_primary=(order == 0)
                )
                order += 1
        
        # 译者
        translators = book_data.get("_translators", [])
        for translator in translators:
            key = f"{translator}||"
            person_db_id = person_map.get(key)
            if person_db_id:
                self.save_book_person(
                    book_id, person_db_id, "translator",
                    order=order, is_primary=False
                )
                order += 1
        
        self.conn.commit()
        Logger.success(f"已保存 {order} 条人物关联: {book_id}")
    
    # ========================================
    # Category 表操作
    # ========================================
    
    def get_category(self, name: str, group: str, module: str = None) -> Optional[Dict]:
        """获取类型/标签"""
        self.connect()
        
        sql = "SELECT * FROM category WHERE name = ? AND \"group\" = ?"
        params = [name, group]
        
        if module:
            sql += " AND module = ?"
            params.append(module)
        else:
            sql += " AND module IS NULL"
        
        cursor = self.conn.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def save_category(self, name: str, group: str, module: str = None) -> int:
        """保存类型/标签"""
        self.connect()
        
        existing = self.get_category(name, group, module)
        if existing:
            return existing["id"]
        
        sql = """
        INSERT INTO category ("group", name, module, "order", enabled)
        VALUES (?, ?, ?, 0, 1)
        """
        
        cursor = self.conn.execute(sql, (group, name, module))
        self.conn.commit()
        
        Logger.success(f"已保存类型/标签: {name} ({group})")
        return cursor.lastrowid
    
    # ========================================
    # BookCategory 表操作
    # ========================================
    
    def clear_book_categories(self, book_id: str):
        """清除书籍的所有类型/标签关联"""
        self.connect()
        self.conn.execute("DELETE FROM book_category WHERE book_id = ?", (book_id,))
    
    def save_book_category(self, book_id: str, category_db_id: int, order: int = 0):
        """保存书籍与类型/标签的关联"""
        self.connect()
        
        sql = """
        INSERT INTO book_category (book_id, category_id, "order")
        VALUES (?, ?, ?)
        """
        
        self.conn.execute(sql, (book_id, category_db_id, order))
    
    def save_book_categories(self, book_id: str, book_data: Dict[str, Any],
                              category_map: Dict[str, int]):
        """保存书籍的所有类型/标签关联"""
        self.clear_book_categories(book_id)
        
        order = 0
        
        # 标签
        tags = book_data.get("_tags", [])
        for tag in tags:
            if tag and tag in category_map:
                category_db_id = category_map[tag]
                self.save_book_category(book_id, category_db_id, order)
                order += 1
        
        # 主题（OpenLibrary）
        subjects = book_data.get("_subjects", [])
        for subject in subjects:
            if subject and subject in category_map:
                category_db_id = category_map[subject]
                self.save_book_category(book_id, category_db_id, order)
                order += 1
        
        self.conn.commit()
        Logger.success(f"已保存 {order} 条类型关联: {book_id}")
    
    # ========================================
    # 批量导入
    # ========================================
    
    def import_book(self, book_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导入一本书的所有数据
        
        Args:
            book_data: 书籍数据
            
        Returns:
            导入结果
        """
        self.connect()
        
        try:
            self.conn.execute("BEGIN TRANSACTION")
            
            # 保存书籍
            book_id = self.save_book(book_data)
            
            # 保存人物
            person_map = {}
            
            authors = book_data.get("_authors", [])
            translators = book_data.get("_translators", [])
            
            for name in authors + translators:
                key = f"{name}||"
                if key not in person_map:
                    db_id, _ = self.save_person({"name": name})
                    person_map[key] = db_id
            
            # 保存人物关联
            self.save_book_persons(book_id, book_data, person_map)
            
            # 保存类型/标签
            category_map = {}
            
            tags = book_data.get("_tags", [])
            for tag in tags:
                if tag and tag not in category_map:
                    db_id = self.save_category(tag, "tag")
                    category_map[tag] = db_id
            
            subjects = book_data.get("_subjects", [])
            for subject in subjects:
                if subject and subject not in category_map:
                    db_id = self.save_category(subject, "tag", "book")
                    category_map[subject] = db_id
            
            # 保存类型关联
            self.save_book_categories(book_id, book_data, category_map)
            
            self.conn.commit()
            
            return {
                "success": True,
                "book_id": book_id,
                "title": book_data.get("title"),
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
    # 统计
    # ========================================
    
    def get_statistics(self) -> Dict[str, int]:
        """获取数据库统计"""
        self.connect()
        
        stats = {}
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM books")
        stats["books"] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM book_series")
        stats["book_series"] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM book_person")
        stats["book_person"] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM book_category")
        stats["book_category"] = cursor.fetchone()[0]
        
        return stats
