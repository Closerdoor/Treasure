# -*- coding: utf-8 -*-
"""
进度管理模块
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

import config
from utils import Logger


class ProgressManager:
    """进度管理器"""
    
    def __init__(self, progress_file: str = None):
        self.progress_file = Path(progress_file or config.PROGRESS_FILE)
        self.progress: Dict[str, Any] = {}
        
    def load(self) -> Dict[str, Any]:
        """加载进度"""
        if self.progress_file.exists():
            self.progress = json.loads(self.progress_file.read_text(encoding="utf-8"))
            Logger.info(f"已加载进度: {self.progress.get('completed_count', 0)} 本已完成")
        else:
            self.progress = {
                "last_updated": "",
                "total": 0,
                "completed_count": 0,
                "books": {}
            }
        return self.progress
        
    def save(self):
        """保存进度"""
        self.progress["last_updated"] = datetime.now().isoformat()
        self.progress_file.write_text(
            json.dumps(self.progress, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        Logger.info("进度已保存")
        
    def init_books(self, book_list: List[Dict]):
        """
        初始化书籍列表
        
        Args:
            book_list: 书籍列表（包含 douban_id, title）
        """
        self.progress["total"] = len(book_list)
        
        for book in book_list:
            douban_id = book.get("douban_id", "") or book.get("id", "")
            if douban_id and douban_id not in self.progress["books"]:
                self.progress["books"][douban_id] = {
                    "title": book.get("title", ""),
                    "book_id": None,
                    "status": "pending",
                    "sources": {
                        "douban": "pending",
                        "openlibrary": "pending",
                        "baike": "pending",
                        "wikipedia": "pending",
                        "goodreads": "pending",
                        "dangdang": "pending",
                        "qidian": "pending",
                        "bookchina": "pending"
                    },
                    "basic_crawled": False,
                    "reviews_crawled": False,
                    "images_crawled": False,
                    "images_downloaded": False,
                    "data_merged": False
                }
        
        self.save()
        Logger.info(f"已初始化 {len(book_list)} 本书")
        
    def update_source_status(self, douban_id: str, source: str, status: str):
        """
        更新来源状态
        
        Args:
            douban_id: 豆瓣 ID
            source: 来源名称
            status: 状态（pending, in_progress, done, error）
        """
        if douban_id in self.progress["books"]:
            self.progress["books"][douban_id]["sources"][source] = status
            self.save()
            
    def update_book_id(self, douban_id: str, book_id: str):
        """更新书籍 ID"""
        if douban_id in self.progress["books"]:
            self.progress["books"][douban_id]["book_id"] = book_id
            self.save()
            
    def get_book_id(self, douban_id: str) -> Optional[str]:
        """获取书籍 ID"""
        if douban_id in self.progress["books"]:
            return self.progress["books"][douban_id].get("book_id")
        return None
            
    def update_status(self, douban_id: str, status: str):
        """更新整体状态"""
        if douban_id in self.progress["books"]:
            self.progress["books"][douban_id]["status"] = status
            if status == "completed":
                self.progress["completed_count"] = self.progress.get("completed_count", 0) + 1
            self.save()
            
    def mark_images_downloaded(self, douban_id: str, downloaded: bool = True):
        """标记图片已下载"""
        if douban_id in self.progress["books"]:
            self.progress["books"][douban_id]["images_downloaded"] = downloaded
            self.save()
            
    def mark_data_merged(self, douban_id: str, merged: bool = True):
        """标记数据已合并"""
        if douban_id in self.progress["books"]:
            self.progress["books"][douban_id]["data_merged"] = merged
            self.save()
            
    def mark_basic_completed(self, douban_id: str, completed: bool = True):
        """标记基本信息已爬取"""
        if douban_id in self.progress["books"]:
            self.progress["books"][douban_id]["basic_crawled"] = completed
            self.save()
            
    def mark_reviews_completed(self, douban_id: str, completed: bool = True):
        """标记书评已爬取"""
        if douban_id in self.progress["books"]:
            self.progress["books"][douban_id]["reviews_crawled"] = completed
            self.save()
            
    def mark_images_completed(self, douban_id: str, completed: bool = True):
        """标记图片已爬取"""
        if douban_id in self.progress["books"]:
            self.progress["books"][douban_id]["images_crawled"] = completed
            self.save()
            
    def is_basic_completed(self, douban_id: str) -> bool:
        """检查基本信息是否已爬取"""
        if douban_id not in self.progress["books"]:
            return False
        return self.progress["books"][douban_id].get("basic_crawled", False)
        
    def is_reviews_completed(self, douban_id: str) -> bool:
        """检查书评是否已爬取"""
        if douban_id not in self.progress["books"]:
            return False
        return self.progress["books"][douban_id].get("reviews_crawled", False)
        
    def is_images_completed(self, douban_id: str) -> bool:
        """检查图片是否已爬取"""
        if douban_id not in self.progress["books"]:
            return False
        return self.progress["books"][douban_id].get("images_crawled", False)
        
    def get_pending_books(self) -> List[Dict]:
        """获取待处理书籍列表"""
        result = []
        for douban_id, book in self.progress.get("books", {}).items():
            if book.get("status") != "completed":
                result.append({
                    "douban_id": douban_id,
                    **book
                })
        return result
        
    def get_next_pending_source(self, douban_id: str) -> Optional[str]:
        """获取下一个待处理的来源"""
        if douban_id not in self.progress["books"]:
            return None
            
        sources = self.progress["books"][douban_id].get("sources", {})
        for source, status in sources.items():
            if status == "pending":
                return source
        return None
        
    def is_book_completed(self, douban_id: str) -> bool:
        """检查书籍是否已完成"""
        if douban_id not in self.progress["books"]:
            return False
        return self.progress["books"][douban_id].get("status") == "completed"
        
    def get_book_progress(self, douban_id: str) -> Optional[Dict]:
        """获取书籍进度"""
        book_progress = self.progress.get("books", {}).get(douban_id)
        if book_progress is None:
            return {"sources": {}}
        return book_progress
        
    def get_summary(self) -> Dict:
        """获取进度摘要"""
        total = self.progress.get("total", 0)
        completed = self.progress.get("completed_count", 0)
        
        sources_status = {}
        for book in self.progress.get("books", {}).values():
            for source, status in book.get("sources", {}).items():
                if source not in sources_status:
                    sources_status[source] = {"done": 0, "pending": 0, "error": 0}
                if status == "done":
                    sources_status[source]["done"] += 1
                elif status == "error":
                    sources_status[source]["error"] += 1
                else:
                    sources_status[source]["pending"] += 1
        
        return {
            "total": total,
            "completed": completed,
            "pending": total - completed,
            "sources": sources_status
        }
