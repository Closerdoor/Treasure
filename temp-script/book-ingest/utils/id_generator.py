# -*- coding: utf-8 -*-
"""
ID 生成工具
"""
import json
from pathlib import Path
from typing import Tuple

import config
from utils import Logger


def generate_book_id() -> str:
    """
    生成书籍 ID
    
    格式：0200NNNNNN
    
    Returns:
        书籍 ID
    """
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
        encoding="utf-8"
    )
    
    return f"{config.BOOK_ID_PREFIX}{next_num:06d}"


def generate_series_id() -> str:
    """
    生成系列 ID
    
    格式：0299NNNNNN
    
    Returns:
        系列 ID
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
        encoding="utf-8"
    )
    
    return f"{config.BOOK_SERIES_ID_PREFIX}{next_num:06d}"


def generate_person_id() -> str:
    """
    生成人物 ID
    
    格式：pNNNNNN
    
    Returns:
        人物 ID
    """
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
        encoding="utf-8"
    )
    
    return f"{config.PERSON_ID_PREFIX}{next_num:06d}"


def get_next_book_number() -> int:
    """
    获取下一个书籍序号
    
    Returns:
        序号
    """
    counter_file = Path(config.OUTPUT_DIR) / ".book_counter"
    
    if counter_file.exists():
        data = json.loads(counter_file.read_text(encoding="utf-8"))
        return data.get("book", 0) + 1
    
    return 1
