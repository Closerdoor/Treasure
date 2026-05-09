# -*- coding: utf-8 -*-
"""
数据合并模块

输出格式基于 Prisma Schema:
- works 表字段命名（驼峰转下划线）
- 生成 staging JSON 文件供后续导入
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils import Logger, generate_work_id


class DataMerger:
    """数据合并器"""
    
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            output_dir = Path(__file__).parent.parent.parent / ".local" / "staging" / "video" / "movie"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _extract_country_from_release_dates(self, release_dates: List[Dict]) -> str:
        """从上映日期中提取最早上映的地区"""
        if not release_dates:
            return ""
        
        valid_dates = []
        for rd in release_dates:
            location = rd.get("location", "")
            if any(keyword in location for keyword in ["电影节", "首映", "premiere", "festival", "limited"]):
                continue
            if location:
                valid_dates.append(rd)
        
        if not valid_dates:
            return release_dates[0].get("location", "")
        
        valid_dates.sort(key=lambda x: x.get("date", ""))
        return valid_dates[0].get("location", "")
    
    def merge(self, work_id: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并各来源数据，输出 staging JSON 格式
        
        输出字段命名规则：
        - 保持驼峰命名（与现有 staging JSON 一致）
        - 写入数据库时再转换为 Prisma schema 字段名
        
        Args:
            work_id: 作品 ID
            raw_data: 原始数据（各来源）
            
        Returns:
            合并后的数据
        """
        Logger.info(f"正在合并数据: {work_id}")
        
        result = {
            "id": work_id,
            "title": "",
            "originalTitle": None,
            "year": None,
            "country": None,
            "language": None,
            "runtime": None,
            "director": [],
            "writer": [],
            "cast": [],
            "otherCast": [],
            "producer": [],
            "genre": [],
            "tags": [],
            "aka": [],
            "releaseDate": [],
            "doubanId": None,
            "imdbId": None,
            "tmdbId": None,
            "doubanRating": None,
            "imdbRating": None,
            "tmdbRating": None,
            "rottenTomatoes": None,
            "metascore": None,
            "rated": None,
            "awards": None,
            "synopsis": None,
            "story": None,
            "videos": [],
            "images": None,
            "reviews": [],
            "soundtrack": None,
            "similar": [],
            "quotes": None
        }
        
        douban = raw_data.get("douban", {})
        if douban:
            result["title"] = douban.get("title", "")
            result["year"] = int(douban.get("year", 0)) if douban.get("year") else None
            result["originalTitle"] = douban.get("original_title")
            
            release_dates = douban.get("release_dates", [])
            country = self._extract_country_from_release_dates(release_dates)
            if not country and douban.get("countries"):
                country = douban.get("countries")
            result["country"] = country
            
            result["language"] = douban.get("languages", "")
            result["runtime"] = douban.get("runtime_minutes")
            
            if douban.get("summary"):
                result["synopsis"] = {
                    "text": douban.get("summary", ""),
                    "note": ""
                }
            
            result["aka"] = douban.get("aliases", [])
            result["releaseDate"] = release_dates
            result["doubanId"] = douban.get("douban_id")
            result["imdbId"] = douban.get("imdb_id")
            result["doubanRating"] = float(douban.get("rating")) if douban.get("rating") else None
            
            result["tags"] = douban.get("tags", [])
            result["genre"] = douban.get("genres", [])
            
            result["similar"] = douban.get("recommendations", [])
            
            images = douban.get("images", {})
            result["images"] = {
                "poster": "poster-main.jpg" if douban.get("main_poster_url") else None,
                "posters": [],
                "stills": [],
                "wallpapers": [],
                "postersTotal": images.get("posters_total", 0),
                "stillsTotal": images.get("stills_total", 0)
            }
            
            if douban.get("comments"):
                for c in douban.get("comments", []):
                    result["reviews"].append({
                        "author": c.get("author"),
                        "source": "豆瓣短评",
                        "date": c.get("date"),
                        "content": c.get("content"),
                        "url": None,
                        "title": None
                    })
            
            if douban.get("reviews"):
                for r in douban.get("reviews", []):
                    result["reviews"].append({
                        "author": r.get("author"),
                        "source": "豆瓣长评",
                        "date": r.get("date"),
                        "content": r.get("content"),
                        "url": r.get("url"),
                        "title": r.get("title")
                    })
        
        tmdb = raw_data.get("tmdb", {})
        if tmdb:
            detail = tmdb.get("detail", {})
            credits = tmdb.get("credits", {})
            images = tmdb.get("images", {})
            videos = tmdb.get("videos", [])
            
            if detail.get("original_title"):
                result["originalTitle"] = detail.get("original_title")
            
            if not result.get("year") and detail.get("year"):
                result["year"] = int(detail.get("year"))
            if not result.get("runtime") and detail.get("runtime_minutes"):
                result["runtime"] = detail.get("runtime_minutes")
            
            result["tmdbId"] = str(detail.get("tmdb_id")) if detail.get("tmdb_id") else None
            
            if detail.get("rating"):
                result["tmdbRating"] = detail.get("rating")
            
            if credits:
                result["director"] = self._extract_directors(credits)
                result["writer"] = self._extract_writers(credits)
                result["cast"] = self._extract_cast(credits)
                result["otherCast"] = self._extract_other_cast(credits)
                result["producer"] = self._extract_producers(credits)
            
            if images:
                result["images"] = self._merge_images(result.get("images", {}), images)
            
            if videos:
                result["videos"] = videos
            
            if tmdb.get("reviews"):
                for r in tmdb.get("reviews", []):
                    result["reviews"].append({
                        "author": r.get("author"),
                        "source": "TMDB",
                        "date": r.get("date"),
                        "content": r.get("content"),
                        "url": r.get("url"),
                        "title": None
                    })
        
        omdb = raw_data.get("omdb", {})
        if omdb:
            ratings = omdb.get("ratings", {})
            
            if ratings.get("imdb"):
                imdb_data = ratings.get("imdb")
                if isinstance(imdb_data, dict):
                    result["imdbRating"] = imdb_data.get("value")
                else:
                    result["imdbRating"] = imdb_data
            
            if ratings.get("rottenTomatoes"):
                rt_data = ratings.get("rottenTomatoes")
                if isinstance(rt_data, dict):
                    result["rottenTomatoes"] = rt_data.get("value")
                else:
                    result["rottenTomatoes"] = rt_data
            
            if ratings.get("metascore"):
                ms_data = ratings.get("metascore")
                if isinstance(ms_data, dict):
                    result["metascore"] = ms_data.get("value")
                else:
                    result["metascore"] = ms_data
            
            if omdb.get("rated"):
                result["rated"] = omdb.get("rated")
            
            if omdb.get("awards"):
                result["awards"] = omdb.get("awards")
        
        wikipedia = raw_data.get("wikipedia", {})
        if wikipedia:
            if wikipedia.get("plot"):
                result["story"] = {
                    "text": wikipedia.get("plot", ""),
                    "note": ""
                }
            elif wikipedia.get("summary"):
                result["story"] = {
                    "text": wikipedia.get("summary", ""),
                    "note": ""
                }
            
            if wikipedia.get("quotes"):
                result["quotes"] = wikipedia.get("quotes", [])
            
            if wikipedia.get("awards"):
                if result.get("awards"):
                    result["awards"] += f"\n{'; '.join(wikipedia.get('awards', []))}"
                else:
                    result["awards"] = "; ".join(wikipedia.get("awards", []))
        
        rotten_tomatoes = raw_data.get("rotten_tomatoes", {})
        if rotten_tomatoes:
            ratings = rotten_tomatoes.get("ratings", {})
            if ratings.get("tomatometer"):
                rt_data = ratings.get("tomatometer")
                if isinstance(rt_data, dict):
                    result["rottenTomatoes"] = rt_data.get("value")
                else:
                    result["rottenTomatoes"] = rt_data
            
            if rotten_tomatoes.get("reviews"):
                for r in rotten_tomatoes.get("reviews", []):
                    result["reviews"].append({
                        "author": r.get("author"),
                        "source": f"烂番茄 · {r.get('source', '')}",
                        "date": r.get("date"),
                        "content": r.get("content"),
                        "url": r.get("url"),
                        "title": None
                    })
        
        metacritic = raw_data.get("metacritic", {})
        if metacritic:
            rating = metacritic.get("rating", {})
            if rating.get("metascore"):
                ms_data = rating.get("metascore")
                if isinstance(ms_data, dict):
                    result["metascore"] = ms_data.get("value")
                else:
                    result["metascore"] = ms_data
            
            if metacritic.get("reviews"):
                for r in metacritic.get("reviews", []):
                    result["reviews"].append({
                        "author": r.get("author"),
                        "source": f"Metacritic · {r.get('source', '')}",
                        "date": r.get("date"),
                        "content": r.get("content"),
                        "url": r.get("url"),
                        "title": None
                    })
        
        Logger.success(f"数据合并完成: {work_id}")
        return result
    
    def _extract_directors(self, credits: Dict) -> List[Dict]:
        """提取导演"""
        directors = []
        for crew in credits.get("crew", []):
            if crew.get("job") == "Director":
                directors.append({
                    "name": crew.get("name", ""),
                    "nameEn": crew.get("name", ""),
                    "avatar": None,
                    "avatarSource": "tmdb" if crew.get("profile_path") else None,
                    "works": []
                })
        return directors
    
    def _extract_writers(self, credits: Dict) -> List[Dict]:
        """提取编剧"""
        writers = []
        for crew in credits.get("crew", []):
            if crew.get("department") == "Writing":
                role = crew.get("job", "编剧")
                if role == "Screenplay":
                    role = "编剧"
                elif role == "Story":
                    role = "故事"
                elif role == "Novel":
                    role = "原著"
                
                writers.append({
                    "name": crew.get("name", ""),
                    "nameEn": crew.get("name", ""),
                    "role": role,
                    "baike": None
                })
        return writers
    
    def _extract_cast(self, credits: Dict) -> List[Dict]:
        """提取主演（前 10 位）"""
        cast = []
        for c in credits.get("cast", [])[:10]:
            cast.append({
                "name": c.get("name", ""),
                "nameEn": c.get("name", ""),
                "role": c.get("character", ""),
                "avatar": None,
                "avatarSource": "tmdb" if c.get("profile_path") else None
            })
        return cast
    
    def _extract_other_cast(self, credits: Dict) -> List[Dict]:
        """提取其他演员（第 11 位起）"""
        other_cast = []
        for c in credits.get("cast", [])[10:30]:
            other_cast.append({
                "name": c.get("name", ""),
                "nameEn": c.get("name", ""),
                "role": c.get("character", "")
            })
        return other_cast
    
    def _extract_producers(self, credits: Dict) -> List[Dict]:
        """提取制片人"""
        producers = []
        for crew in credits.get("crew", []):
            if crew.get("department") == "Production" and crew.get("job") in ["Producer", "Executive Producer"]:
                role = "制片人" if crew.get("job") == "Producer" else "执行制片人"
                producers.append({
                    "name": crew.get("name", ""),
                    "nameEn": crew.get("name", ""),
                    "role": role,
                    "baike": None
                })
        return producers
    
    def _merge_images(self, existing: Dict, tmdb_images: Dict) -> Dict:
        """合并图片数据"""
        result = existing or {
            "poster": None,
            "posters": [],
            "stills": [],
            "wallpapers": [],
            "postersTotal": 0,
            "stillsTotal": 0
        }
        
        for poster in tmdb_images.get("posters", [])[:10]:
            result["posters"].append({
                "url": poster.get("url", ""),
                "width": poster.get("width", 0),
                "height": poster.get("height", 0)
            })
        
        for backdrop in tmdb_images.get("backdrops", [])[:10]:
            result["stills"].append({
                "url": backdrop.get("url", ""),
                "width": backdrop.get("width", 0),
                "height": backdrop.get("height", 0)
            })
        
        return result
    
    def detect_conflicts(self, raw_data: Dict[str, Any]) -> List[Dict]:
        """检测字段冲突"""
        conflicts = []
        
        douban_runtime = raw_data.get("douban", {}).get("runtime_minutes", 0)
        tmdb_runtime = raw_data.get("tmdb", {}).get("detail", {}).get("runtime_minutes", 0)
        
        if douban_runtime and tmdb_runtime and abs(douban_runtime - tmdb_runtime) > 5:
            conflicts.append({
                "field": "runtime",
                "sources": {
                    "douban": douban_runtime,
                    "tmdb": tmdb_runtime
                }
            })
        
        douban_year = raw_data.get("douban", {}).get("year", "")
        tmdb_year = raw_data.get("tmdb", {}).get("detail", {}).get("year", "")
        
        if douban_year and tmdb_year and str(douban_year) != str(tmdb_year):
            conflicts.append({
                "field": "year",
                "sources": {
                    "douban": douban_year,
                    "tmdb": tmdb_year
                }
            })
        
        return conflicts
    
    def save_raw_data(self, work_id: str, source: str, data: Dict):
        """保存原始数据"""
        raw_dir = self.output_dir.parent.parent / "raw" / work_id
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = raw_dir / f"{source}.json"
        filepath.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        Logger.info(f"已保存原始数据: {filepath}")
    
    def save_merged_data(self, work_id: str, data: Dict):
        """保存合并后的数据到 staging 目录"""
        filepath = self.output_dir / f"{work_id}.json"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        filepath.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        Logger.success(f"已保存 staging 数据: {filepath}")
