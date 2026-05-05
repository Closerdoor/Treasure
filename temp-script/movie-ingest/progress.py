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
            Logger.info(f"已加载进度: {self.progress.get('completed_count', 0)} 部已完成")
        else:
            self.progress = {
                "last_updated": "",
                "total": 0,
                "completed_count": 0,
                "movies": {}
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
        
    def init_movies(self, movie_list: List[Dict]):
        """
        初始化电影列表
        
        Args:
            movie_list: 电影列表（包含 douban_id, title）
        """
        self.progress["total"] = len(movie_list)
        
        for movie in movie_list:
            douban_id = movie.get("douban_id", "") or movie.get("id", "")
            if douban_id and douban_id not in self.progress["movies"]:
                self.progress["movies"][douban_id] = {
                    "title": movie.get("title", ""),
                    "work_id": None,
                    "status": "pending",
                    "sources": {
                        "douban": "pending",
                        "tmdb": "pending",
                        "omdb": "pending",
                        "baike": "pending",
                        "wikipedia": "pending",
                        "rotten_tomatoes": "pending",
                        "metacritic": "pending"
                    },
                    "images_downloaded": False,
                    "data_merged": False
                }
        
        self.save()
        Logger.info(f"已初始化 {len(movie_list)} 部电影")
        
    def update_source_status(self, douban_id: str, source: str, status: str):
        """
        更新来源状态
        
        Args:
            douban_id: 豆瓣 ID
            source: 来源名称
            status: 状态（pending, in_progress, done, error）
        """
        if douban_id in self.progress["movies"]:
            self.progress["movies"][douban_id]["sources"][source] = status
            self.save()
            
    def update_work_id(self, douban_id: str, work_id: str):
        """更新作品 ID"""
        if douban_id in self.progress["movies"]:
            self.progress["movies"][douban_id]["work_id"] = work_id
            self.save()
            
    def update_status(self, douban_id: str, status: str):
        """更新整体状态"""
        if douban_id in self.progress["movies"]:
            self.progress["movies"][douban_id]["status"] = status
            if status == "completed":
                self.progress["completed_count"] = self.progress.get("completed_count", 0) + 1
            self.save()
            
    def mark_images_downloaded(self, douban_id: str, downloaded: bool = True):
        """标记图片已下载"""
        if douban_id in self.progress["movies"]:
            self.progress["movies"][douban_id]["images_downloaded"] = downloaded
            self.save()
            
    def mark_data_merged(self, douban_id: str, merged: bool = True):
        """标记数据已合并"""
        if douban_id in self.progress["movies"]:
            self.progress["movies"][douban_id]["data_merged"] = merged
            self.save()
            
    def get_pending_movies(self) -> List[Dict]:
        """获取待处理电影列表"""
        result = []
        for douban_id, movie in self.progress.get("movies", {}).items():
            if movie.get("status") != "completed":
                result.append({
                    "douban_id": douban_id,
                    **movie
                })
        return result
        
    def get_next_pending_source(self, douban_id: str) -> Optional[str]:
        """获取下一个待处理的来源"""
        if douban_id not in self.progress["movies"]:
            return None
            
        sources = self.progress["movies"][douban_id].get("sources", {})
        for source, status in sources.items():
            if status == "pending":
                return source
        return None
        
    def is_movie_completed(self, douban_id: str) -> bool:
        """检查电影是否已完成"""
        if douban_id not in self.progress["movies"]:
            return False
        return self.progress["movies"][douban_id].get("status") == "completed"
        
    def get_movie_progress(self, douban_id: str) -> Optional[Dict]:
        """获取电影进度"""
        return self.progress.get("movies", {}).get(douban_id)
        
    def get_summary(self) -> Dict:
        """获取进度摘要"""
        total = self.progress.get("total", 0)
        completed = self.progress.get("completed_count", 0)
        
        sources_status = {}
        for movie in self.progress.get("movies", {}).values():
            for source, status in movie.get("sources", {}).items():
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