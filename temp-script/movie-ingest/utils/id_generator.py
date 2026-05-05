# -*- coding: utf-8 -*-
"""
ID 生成工具
"""
from typing import Dict


_work_id_counter: Dict[str, int] = {}
_person_id_counter: int = 0
_term_id_counter: int = 0


def generate_work_id(module: str = "video", submodule: str = "movie") -> str:
    """
    生成作品 ID
    格式：MMSSNNNNNN
    - MM: 一级模块编号（01-04）
    - SS: 子模块编号（01-05）
    - NNNNNN: 递增序号
    """
    module_map = {
        "video": "01",
        "book": "02",
        "music": "03",
        "game": "04"
    }
    
    submodule_map = {
        "movie": "01",
        "tv": "02",
        "anime": "03",
        "documentary": "04",
        "short": "05"
    }
    
    mm = module_map.get(module, "01")
    ss = submodule_map.get(submodule, "01")
    key = f"{mm}{ss}"
    
    if key not in _work_id_counter:
        _work_id_counter[key] = 1
    else:
        _work_id_counter[key] += 1
    
    nn = _work_id_counter[key]
    return f"{mm}{ss}{nn:06d}"


def generate_person_code() -> str:
    """
    生成人物编码
    格式：pNNNNNN
    """
    global _person_id_counter
    _person_id_counter += 1
    return f"p{_person_id_counter:06d}"


def generate_term_code(term_type: str = "tag") -> str:
    """
    生成词项编码
    格式：gNNNNNN（类型）或 tNNNNNN（标签）
    """
    global _term_id_counter
    _term_id_counter += 1
    
    prefix = "g" if term_type == "genre" else "t"
    return f"{prefix}{_term_id_counter:06d}"


def reset_counters():
    """重置计数器（用于测试）"""
    global _work_id_counter, _person_id_counter, _term_id_counter
    _work_id_counter = {}
    _person_id_counter = 0
    _term_id_counter = 0
