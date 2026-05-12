# -*- coding: utf-8 -*-
"""
哈希计算工具
"""
import hashlib

def calculate_md5(content: bytes) -> str:
    """
    计算内容的 MD5 哈希值
    
    Args:
        content: 字节内容
        
    Returns:
        MD5 哈希字符串
    """
    return hashlib.md5(content).hexdigest()