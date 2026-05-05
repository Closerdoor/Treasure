# -*- coding: utf-8 -*-
"""
哈希计算工具
"""
import hashlib
from pathlib import Path
from typing import Optional


def calculate_file_hash(filepath: str) -> str:
    """计算文件 MD5 哈希"""
    md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


def calculate_url_hash(url: str) -> str:
    """计算 URL MD5 哈希（用于去重）"""
    return hashlib.md5(url.encode()).hexdigest()


def calculate_content_hash(content: bytes) -> str:
    """计算内容 MD5 哈希"""
    return hashlib.md5(content).hexdigest()
