# -*- coding: utf-8 -*-
"""
ID 生成工具

优先从数据库取最大序号 + 1，回退到本地计数器
"""
import json
import sqlite3
from pathlib import Path

import config
from utils import Logger


def _get_db_path() -> Path:
    return Path(__file__).parent.parent.parent / ".local" / "treasure.db"


def generate_book_id() -> str:
    """
    生成书籍 ID

    格式：0200NNNNNN

    优先从数据库 books 表取最大序号 + 1，
    回退到本地 .book_counter 文件
    """
    db_path = _get_db_path()

    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("SELECT id FROM books WHERE id LIKE '0200%' ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()

            if row:
                match = __import__('re').match(r"0200(\d+)", row[0])
                if match:
                    next_num = int(match.group(1)) + 1
                    return f"{config.BOOK_ID_PREFIX}{next_num:06d}"
        except Exception:
            pass

    counter_file = Path(config.OUTPUT_DIR) / ".book_counter"

    if counter_file.exists():
        data = json.loads(counter_file.read_text(encoding="utf-8"))
        last_num = data.get("book", 0)
    else:
        last_num = 0

    next_num = last_num + 1

    counter_file.parent.mkdir(parents=True, exist_ok=True)
    counter_file.write_text(
        json.dumps({"book": next_num}, ensure_ascii=False),
        encoding="utf-8",
    )

    return f"{config.BOOK_ID_PREFIX}{next_num:06d}"


def generate_series_id() -> str:
    """
    生成系列 ID

    格式：0299NNNNNN
    """
    counter_file = Path(config.OUTPUT_DIR) / ".book_counter"

    if counter_file.exists():
        data = json.loads(counter_file.read_text(encoding="utf-8"))
        last_num = data.get("series", 0)
    else:
        last_num = 0

    next_num = last_num + 1

    counter_file.parent.mkdir(parents=True, exist_ok=True)
    counter_file.write_text(
        json.dumps({"series": next_num}, ensure_ascii=False),
        encoding="utf-8",
    )

    return f"{config.BOOK_SERIES_ID_PREFIX}{next_num:06d}"


def generate_person_id() -> str:
    """
    生成人物 ID

    格式：pNNNNNN

    优先从数据库 person 表取最大序号 + 1，
    回退到本地计数器
    """
    db_path = _get_db_path()

    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("SELECT person_id FROM person ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()

            if row:
                match = __import__('re').match(r"p(\d+)", row[0])
                if match:
                    next_num = int(match.group(1)) + 1
                    return f"{config.PERSON_ID_PREFIX}{next_num:06d}"
        except Exception:
            pass

    counter_file = Path(config.OUTPUT_DIR) / ".book_counter"

    if counter_file.exists():
        data = json.loads(counter_file.read_text(encoding="utf-8"))
        last_num = data.get("person", 0)
    else:
        last_num = 0

    next_num = last_num + 1

    counter_file.parent.mkdir(parents=True, exist_ok=True)
    counter_file.write_text(
        json.dumps({"person": next_num}, ensure_ascii=False),
        encoding="utf-8",
    )

    return f"{config.PERSON_ID_PREFIX}{next_num:06d}"


def get_next_book_number() -> int:
    """获取下一个书籍序号"""
    db_path = _get_db_path()

    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.execute("SELECT id FROM books WHERE id LIKE '0200%' ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()

            if row:
                match = __import__('re').match(r"0200(\d+)", row[0])
                if match:
                    return int(match.group(1)) + 1
        except Exception:
            pass

    counter_file = Path(config.OUTPUT_DIR) / ".book_counter"

    if counter_file.exists():
        data = json.loads(counter_file.read_text(encoding="utf-8"))
        return data.get("book", 0) + 1

    return 1