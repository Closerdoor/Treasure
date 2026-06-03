# -*- coding: utf-8 -*-
"""
数据库管理模块

核心原则：
1. 从 staging 的对象/数组结构序列化为 DB 需要的 JSON 字符串
2. 从 _meta 提取 authors/translators/tags 等关联信息
3. 空字符串视为无效值，不覆盖已有数据
4. 人物匹配按 name + nameEn 精确匹配
"""
import os
import sys

if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

import sqlite3
import json
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

import config
from utils import Logger


def _serialize(value) -> Optional[str]:
    """将对象/数组序列化为 JSON 字符串，空值返回 None"""
    if value is None:
        return None
    if isinstance(value, str):
        if value.strip() == "":
            return None
        return value
    if isinstance(value, (list, dict)):
        if len(value) == 0:
            return None
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


def _coalesce(new_val, existing_val):
    """合并值：新值有效则用新值，否则保留旧值。空字符串视为无效。"""
    if new_val is not None and str(new_val).strip() != "":
        return new_val
    return existing_val


def _has_cjk(value) -> bool:
    """书籍分类 / 标签入库只接受含中文字符的值，避免英文来源类型进入前台。"""
    return bool(value and re.search(r"[\u4e00-\u9fff]", str(value)))


def _filter_chinese_values(values: List[Any]) -> List[str]:
    result: List[str] = []
    for value in values or []:
        text = str(value).strip()
        if text and _has_cjk(text) and text not in result:
            result.append(text)
    return result


class BookDB:
    """书籍数据库操作"""

    def __init__(self, db_path: str = None, promote_assets: bool = True):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / ".local" / "treasure.db"
        self.db_path = Path(db_path)
        self.conn: Optional[sqlite3.Connection] = None
        self._suspend_autocommit = False
        self.promote_assets = promote_assets

    def _commit_if_needed(self):
        if self.conn and not self._suspend_autocommit:
            self.conn.commit()

    def _promote_book_assets(self, book_id: str) -> Dict[str, int]:
        """把采集阶段下载的书籍资源提升到正式本地资源目录。"""
        source_dir = Path(__file__).parent / "data" / "assets" / book_id
        target_dir = config.OUTPUT_DIR.parents[2] / ".local" / "assets" / "book" / book_id
        stats = {"copied": 0, "missing": 0}

        if not source_dir.exists():
            stats["missing"] = 1
            return stats

        for source_file in source_dir.rglob("*"):
            if source_file.is_file():
                relative = source_file.relative_to(source_dir)
                target_file = target_dir / relative
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, target_file)
                stats["copied"] += 1

        return stats

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

    def get_next_book_number(self) -> int:
        """从数据库获取下一个书籍序号"""
        self.connect()
        cursor = self.conn.execute("SELECT id FROM books WHERE id LIKE '0200%' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            last_id = row["id"]
            match = re.match(r"0200(\d+)", last_id)
            if match:
                return int(match.group(1)) + 1
        return 1

    def get_next_series_id(self) -> str:
        """获取下一个书籍系列 ID。"""
        self.connect()
        cursor = self.conn.execute("SELECT id FROM book_series WHERE id LIKE '0299%' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return f"0299{int(row['id'][-6:]) + 1:06d}"
        return "0299000001"

    def get_book_series_by_name(self, name: str) -> Optional[Dict]:
        """通过系列名查找书籍系列。"""
        self.connect()
        cursor = self.conn.execute("SELECT * FROM book_series WHERE name = ?", (name,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def save_book_series(self, series_data: Dict[str, Any]) -> Optional[str]:
        """保存或复用书籍系列。"""
        name = series_data.get("name") if isinstance(series_data, dict) else None
        if not name:
            return None

        existing = self.get_book_series_by_name(name)
        if existing:
            return existing["id"]

        series_id = series_data.get("id") or self.get_next_series_id()
        now = datetime.now().isoformat()
        self.conn.execute(
            """
            INSERT INTO book_series (
                id, name, name_original, book_count, summary, images, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                series_id,
                name,
                series_data.get("nameOriginal"),
                series_data.get("bookCount"),
                series_data.get("summary"),
                _serialize(series_data.get("images")),
                series_data.get("status", "draft"),
                now,
                now,
            ),
        )
        self._commit_if_needed()
        Logger.success(f"已保存书籍系列: {name} ({series_id})")
        return series_id

    def save_book(self, data: Dict[str, Any]) -> str:
        """
        保存书籍数据

        staging 数据中的复杂字段（scores, externalSource, images, related, quotes,
        excerpts, otherTitles, reviews）保持对象/数组结构，在此处序列化为 JSON 字符串写入 DB。

        Args:
            data: staging 格式的书籍数据（含 _meta）

        Returns:
            书籍 ID
        """
        self.connect()

        book_id = data.get("id")
        isbn = data.get("isbn")

        if not book_id:
            raise ValueError("书籍 ID 不能为空")

        now = datetime.now().isoformat()

        # 序列化复杂字段
        scores_json = _serialize(data.get("scores"))
        external_source_json = _serialize(data.get("externalSource"))
        images_json = _serialize(data.get("images"))
        related_json = _serialize(data.get("related"))
        quotes_json = _serialize(data.get("quotes"))
        excerpts_json = _serialize(data.get("excerpts"))
        other_titles_json = _serialize(data.get("otherTitles"))
        reviews_json = _serialize(data.get("reviews"))

        # 检查 ISBN 是否已存在
        if isbn:
            cursor = self.conn.execute("SELECT id FROM books WHERE isbn = ?", (isbn,))
            existing = cursor.fetchone()
            if existing:
                existing_id = existing["id"]
                Logger.warning(f"ISBN {isbn} 已存在，更新记录 {existing_id}")

                update_sql = """
                UPDATE books SET
                    title = ?,
                    title_original = COALESCE(NULLIF(?, ''), title_original),
                    other_titles = COALESCE(?, other_titles),
                    year = COALESCE(?, year),
                    country = COALESCE(NULLIF(?, ''), country),
                    language = COALESCE(NULLIF(?, ''), language),
                    word_count = COALESCE(?, word_count),
                    publisher = COALESCE(NULLIF(?, ''), publisher),
                    publish_date = COALESCE(NULLIF(?, ''), publish_date),
                    pages = COALESCE(?, pages),
                    price = COALESCE(NULLIF(?, ''), price),
                    binding = COALESCE(NULLIF(?, ''), binding),
                    format = COALESCE(NULLIF(?, ''), format),
                    edition = COALESCE(NULLIF(?, ''), edition),
                    summary = COALESCE(NULLIF(?, ''), summary),
                    story = COALESCE(NULLIF(?, ''), story),
                    quotes = COALESCE(?, quotes),
                    excerpts = COALESCE(?, excerpts),
                    series_id = COALESCE(NULLIF(?, ''), series_id),
                    series_order = COALESCE(?, series_order),
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
                    other_titles_json,
                    data.get("year"),
                    data.get("country"),
                    data.get("language"),
                    data.get("wordCount"),
                    data.get("publisher"),
                    data.get("publishDate"),
                    data.get("pages"),
                    data.get("price"),
                    data.get("binding"),
                    data.get("format"),
                    data.get("edition"),
                    data.get("summary"),
                    data.get("story"),
                    quotes_json,
                    excerpts_json,
                    data.get("seriesId"),
                    data.get("seriesOrder"),
                    scores_json,
                    external_source_json,
                    images_json,
                    reviews_json,
                    related_json,
                    now,
                    existing_id,
                )

                self.conn.execute(update_sql, update_params)
                self._commit_if_needed()

                Logger.success(f"已更新书籍: {data.get('title')} ({existing_id})")
                return existing_id

        # 新书籍，插入
        sql = """
        INSERT INTO books (
            id, title, title_original, other_titles, isbn, year, country,
            language, word_count, publisher, publish_date, pages, price,
            binding, format, edition, summary, story, quotes, excerpts, series_id,
            series_order, scores, external_source, images, reviews, related,
            status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            title = excluded.title,
            title_original = COALESCE(NULLIF(excluded.title_original, ''), books.title_original),
            other_titles = COALESCE(excluded.other_titles, books.other_titles),
            isbn = COALESCE(NULLIF(excluded.isbn, ''), books.isbn),
            year = COALESCE(excluded.year, books.year),
            country = COALESCE(NULLIF(excluded.country, ''), books.country),
            language = COALESCE(NULLIF(excluded.language, ''), books.language),
            word_count = COALESCE(excluded.word_count, books.word_count),
            publisher = COALESCE(NULLIF(excluded.publisher, ''), books.publisher),
            publish_date = COALESCE(NULLIF(excluded.publish_date, ''), books.publish_date),
            pages = COALESCE(excluded.pages, books.pages),
            price = COALESCE(NULLIF(excluded.price, ''), books.price),
            binding = COALESCE(NULLIF(excluded.binding, ''), books.binding),
            format = COALESCE(NULLIF(excluded.format, ''), books.format),
            edition = COALESCE(NULLIF(excluded.edition, ''), books.edition),
            summary = COALESCE(NULLIF(excluded.summary, ''), books.summary),
            story = COALESCE(NULLIF(excluded.story, ''), books.story),
            quotes = COALESCE(excluded.quotes, books.quotes),
            excerpts = COALESCE(excluded.excerpts, books.excerpts),
            series_id = COALESCE(excluded.series_id, books.series_id),
            series_order = COALESCE(excluded.series_order, books.series_order),
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
            other_titles_json,
            data.get("isbn"),
            data.get("year"),
            data.get("country"),
            data.get("language"),
            data.get("wordCount"),
            data.get("publisher"),
            data.get("publishDate"),
            data.get("pages"),
            data.get("price"),
            data.get("binding"),
            data.get("format"),
            data.get("edition"),
            data.get("summary"),
            data.get("story"),
            quotes_json,
            excerpts_json,
            data.get("seriesId"),
            data.get("seriesOrder"),
            scores_json,
            external_source_json,
            images_json,
            reviews_json,
            related_json,
            data.get("status", "draft"),
            now,
            now,
        )

        self.conn.execute(sql, params)
        self._commit_if_needed()

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
                (name, name_en),
            )
        else:
            cursor = self.conn.execute(
                "SELECT * FROM person WHERE name = ?",
                (name,),
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
            update_fields = []
            update_params = []
            if name_en and not existing.get("name_en"):
                update_fields.append("name_en = ?")
                update_params.append(name_en)
            if data.get("profileLink") and not existing.get("profile_link"):
                update_fields.append("profile_link = ?")
                update_params.append(data["profileLink"])
            if data.get("intro") and not existing.get("intro"):
                update_fields.append("intro = ?")
                update_params.append(data["intro"])
            if data.get("sourceIds") and not existing.get("source_ids"):
                update_fields.append("source_ids = ?")
                update_params.append(data["sourceIds"])
            if data.get("avatarPath") and not existing.get("avatar_path"):
                update_fields.append("avatar_path = ?")
                update_params.append(data["avatarPath"])
            if data.get("doubanAvatarPath") and not existing.get("douban_avatar_path"):
                update_fields.append("douban_avatar_path = ?")
                update_params.append(data["doubanAvatarPath"])
            if update_fields:
                update_sql = f"UPDATE person SET {', '.join(update_fields)} WHERE id = ?"
                update_params.append(existing["id"])
                self.conn.execute(update_sql, update_params)
                self._commit_if_needed()
            return existing["id"], existing["person_id"]

        if not person_id:
            source_ids = data.get("sourceIds")
            try:
                source_map = json.loads(source_ids) if source_ids else {}
            except Exception:
                source_map = {}
            if source_map.get("douban"):
                person_id = f"p{source_map['douban']}"
            else:
                person_id = self.get_next_person_id()

        sql = """
        INSERT INTO person (person_id, name, name_en, source_ids, avatar_path, douban_avatar_path, profile_link, intro)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """

        cursor = self.conn.execute(sql, (
            person_id, name, name_en,
            data.get("sourceIds"),
            data.get("avatarPath"),
            data.get("doubanAvatarPath"),
            data.get("profileLink"),
            data.get("intro"),
        ))

        self._commit_if_needed()

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

    def save_book_persons(self, book_id: str, authors: List[str], translators: List[str],
                           person_map: Dict[str, int]):
        """
        保存书籍的所有人物关联

        Args:
            book_id: 书籍 ID
            authors: 作者列表（已清洗）
            translators: 译者列表（已清洗）
            person_map: 人物映射 {"name||nameEn": person_db_id}
        """
        self.clear_book_persons(book_id)

        order = 0

        for author in authors:
            key = f"{author}||"
            person_db_id = person_map.get(key)
            if person_db_id:
                self.save_book_person(
                    book_id, person_db_id, "author",
                    order=order, is_primary=(order == 0),
                )
                order += 1

        for translator in translators:
            key = f"{translator}||"
            person_db_id = person_map.get(key)
            if person_db_id:
                self.save_book_person(
                    book_id, person_db_id, "translator",
                    order=order, is_primary=False,
                )
                order += 1

        self._commit_if_needed()
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
        self._commit_if_needed()

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

    def save_book_categories(self, book_id: str, tags: List[str], subjects: List[str],
                              genres: List[str], category_map: Dict[tuple, int]):
        """
        保存书籍的所有类型/标签关联

        Args:
            book_id: 书籍 ID
            tags: 标签列表
            subjects: 主题列表（OpenLibrary）
            genres: 类型列表（Goodreads/起点）
            category_map: 分类映射 {("tag"|"type", "name"): category_db_id}
        """
        self.clear_book_categories(book_id)

        order = 0

        for tag in tags:
            category_id = category_map.get(("tag", tag))
            if tag and category_id:
                self.save_book_category(book_id, category_id, order)
                order += 1

        for subject in subjects:
            category_id = category_map.get(("tag", subject))
            if subject and category_id:
                self.save_book_category(book_id, category_id, order)
                order += 1

        for genre in genres:
            category_id = category_map.get(("type", genre))
            if genre and category_id:
                self.save_book_category(book_id, category_id, order)
                order += 1

        self._commit_if_needed()
        Logger.success(f"已保存 {order} 条类型关联: {book_id}")

    # ========================================
    # 批量导入
    # ========================================

    def import_book(self, book_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        导入一本书的所有数据

        从 staging 格式的数据中提取：
        - 正式字段 → books 表
        - _meta.authors / _meta.translators → person + book_person 表
        - _meta.tags / _meta.subjects / _meta.genres → category + book_category 表

        Args:
            book_data: staging 格式的书籍数据

        Returns:
            导入结果
        """
        self.connect()

        previous_autocommit_state = self._suspend_autocommit
        self._suspend_autocommit = True
        try:
            self.conn.execute("BEGIN TRANSACTION")

            meta = book_data.get("_meta", {})
            series_data = meta.get("series") if isinstance(meta, dict) else None
            if series_data and not book_data.get("seriesId"):
                series_id = self.save_book_series(series_data)
                if series_id:
                    book_data["seriesId"] = series_id
            if series_data and book_data.get("seriesOrder") is None:
                order = series_data.get("order")
                if order is not None:
                    try:
                        book_data["seriesOrder"] = int(order)
                    except (TypeError, ValueError):
                        Logger.warning(f"书籍系列顺序不是有效数字: {order}")

            # 保存书籍
            book_id = self.save_book(book_data)

            # 从 _meta 提取关联信息
            authors = meta.get("authors", [])
            translators = meta.get("translators", [])
            tags = meta.get("tags", [])
            subjects = meta.get("subjects", [])
            genres = meta.get("genres", [])
            tags = _filter_chinese_values(tags)
            subjects = _filter_chinese_values(subjects)
            genres = _filter_chinese_values(genres)

            # 保存人物
            person_map = {}
            person_details = meta.get("personDetails", [])
            person_detail_map = {}
            for pd in person_details:
                pd_name = pd.get("name", "")
                if pd_name:
                    person_detail_map[pd_name] = pd

            for name in authors + translators:
                key = f"{name}||"
                if key not in person_map:
                    person_data = {"name": name}
                    detail = person_detail_map.get(name)
                    if detail:
                        if detail.get("name_en"):
                            person_data["nameEn"] = detail["name_en"]
                        if detail.get("intro"):
                            person_data["intro"] = detail["intro"]
                        if detail.get("personage_url"):
                            person_data["profileLink"] = detail["personage_url"]
                        if detail.get("avatar_url"):
                            person_data["doubanAvatarUrl"] = detail["avatar_url"]
                        if detail.get("avatarPath"):
                            person_data["avatarPath"] = detail["avatarPath"]
                            person_data["doubanAvatarPath"] = detail["avatarPath"]
                        if detail.get("douban_personage_id"):
                            source_ids = {"douban": detail["douban_personage_id"]}
                            if detail.get("imdb_id"):
                                source_ids["imdb"] = detail["imdb_id"]
                            person_data["sourceIds"] = json.dumps(source_ids, ensure_ascii=False)
                        if detail.get("personId"):
                            person_data["personId"] = detail["personId"]
                    db_id, _ = self.save_person(person_data, person_id=person_data.get("personId"))
                    person_map[key] = db_id

            # 保存人物关联
            self.save_book_persons(book_id, authors, translators, person_map)

            # 保存类型/标签
            category_map = {}

            for tag in tags:
                key = ("tag", tag)
                if tag and key not in category_map:
                    db_id = self.save_category(tag, "tag")
                    category_map[key] = db_id

            for subject in subjects:
                key = ("tag", subject)
                if subject and key not in category_map:
                    db_id = self.save_category(subject, "tag", "book")
                    category_map[key] = db_id

            for genre in genres:
                key = ("type", genre)
                if genre and key not in category_map:
                    db_id = self.save_category(genre, "type", "book")
                    category_map[key] = db_id

            # 保存类型关联
            self.save_book_categories(book_id, tags, subjects, genres, category_map)

            self.conn.commit()
            asset_stats = {"copied": 0, "missing": 0, "skipped": 0}
            if self.promote_assets:
                asset_stats = self._promote_book_assets(book_id)
                if asset_stats["copied"]:
                    Logger.success(f"已同步 {asset_stats['copied']} 个书籍封面资源: {book_id}")
                elif asset_stats["missing"]:
                    Logger.warning(f"未找到采集阶段书籍封面目录: {book_id}")
            else:
                asset_stats["skipped"] = 1

            return {
                "success": True,
                "book_id": book_id,
                "title": book_data.get("title"),
                "persons": len(person_map),
                "categories": len(category_map),
                "assets": asset_stats,
            }

        except Exception as e:
            self.conn.rollback()
            Logger.error(f"导入失败: {e}")
            return {
                "success": False,
                "error": str(e),
            }
        finally:
            self._suspend_autocommit = previous_autocommit_state

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

        cursor = self.conn.execute("SELECT COUNT(*) FROM person")
        stats["person"] = cursor.fetchone()[0]

        return stats
