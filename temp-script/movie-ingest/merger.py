# -*- coding: utf-8 -*-
"""
数据合并模块
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils import Logger, generate_work_id


class DataMerger:
    """数据合并器"""
    
    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _extract_country_from_release_dates(self, release_dates: List[Dict]) -> str:
        """
        从上映日期中提取最早上映的地区
        
        Args:
            release_dates: 上映日期列表
            
        Returns:
            国家/地区名称
        """
        if not release_dates:
            return ""
        
        # 过滤掉电影节等特殊上映
        valid_dates = []
        for rd in release_dates:
            location = rd.get("location", "")
            # 忽略电影节、首映等特殊上映
            if any(keyword in location for keyword in ["电影节", "首映", "premiere", "festival", "limited"]):
                continue
            if location:
                valid_dates.append(rd)
        
        if not valid_dates:
            # 如果没有有效上映日期，返回第一个
            return release_dates[0].get("location", "")
        
        # 按日期排序，取最早的
        valid_dates.sort(key=lambda x: x.get("date", ""))
        return valid_dates[0].get("location", "")
        
    def merge(self, work_id: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并各来源数据
        
        Args:
            work_id: 作品 ID
            raw_data: 原始数据（各来源）
            
        Returns:
            合并后的数据
        """
        Logger.info(f"正在合并数据: {work_id}")
        
        result = {
            "id": work_id,
            "module": "video",
            "submodule": "movie",
            "schema_type": "live_action_movie",
            "status": "published",
            "created_at": datetime.now().strftime("%Y-%m-%d"),
            "updated_at": datetime.now().strftime("%Y-%m-%d"),
            "assetDir": f"video/movie/{work_id}"
        }
        
        # 豆瓣数据（优先级最高）
        douban = raw_data.get("douban", {})
        if douban:
            result["title"] = douban.get("title", "")
            result["year"] = int(douban.get("year", 0)) if douban.get("year") else 0
            
            # 原名：优先从豆瓣获取
            if douban.get("original_title"):
                result["original_title"] = douban.get("original_title")
            
            # 国家：从上映日期中提取最早上映的地区
            release_dates = douban.get("release_dates", [])
            country = self._extract_country_from_release_dates(release_dates)
            # 如果上映日期中没有找到，使用豆瓣的国家字段
            if not country and douban.get("countries"):
                country = douban.get("countries")
            result["country"] = country
            
            result["language"] = douban.get("languages", "")
            result["runtime_minutes"] = douban.get("runtime_minutes", 0)
            result["synopsis_text"] = douban.get("summary", "")
            
            # 别名
            result["aliases_json"] = douban.get("aliases", [])
            
            # 上映日期
            result["release_dates_json"] = release_dates
            
            # 标识符
            result["identifiers_json"] = {
                "douban": douban.get("douban_id", ""),
                "imdb": douban.get("imdb_id", "")
            }
            
            # 链接
            result["links_json"] = {
                "douban": douban.get("url", "")
            }
            
            # 评分
            douban_rating = douban.get("rating", "")
            result["ratings_json"] = {
                "douban": {
                    "value": float(douban_rating) if douban_rating else None,
                    "scale": 10
                }
            }
            
            # 标签
            result["tags"] = douban.get("tags", [])
            result["genres"] = douban.get("genres", [])
            
            # 相关推荐
            recommendations = douban.get("recommendations", [])
            result["relations_json"] = {
                "series": [],
                "similar": recommendations
            }
            
            # 出品公司
            result["production_companies_json"] = [
                {"name": c, "country": ""} for c in douban.get("production_companies", [])
            ]
            
            # 图片总数
            images = douban.get("images", {})
            result["images_json"] = {
                "poster": "",  # 稍后设置
                "posters": [],
                "stills": [],
                "postersTotal": images.get("posters_total", 0),
                "stillsTotal": images.get("stills_total", 0),
                "assetDir": f"video/movie/{work_id}"
            }
            
            # 设置主海报（豆瓣主海报优先）
            if douban.get("poster"):
                result["images_json"]["poster"] = "poster-main.jpg"
        
        # TMDB 数据
        tmdb = raw_data.get("tmdb", {})
        if tmdb:
            detail = tmdb.get("detail", {})
            credits = tmdb.get("credits", {})
            images = tmdb.get("images", {})
            videos = tmdb.get("videos", [])
            
            # 原名（TMDB 优先）
            if detail.get("original_title"):
                result["original_title"] = detail.get("original_title", "")
            
            # 补充基本信息
            if not result.get("year") and detail.get("year"):
                result["year"] = int(detail.get("year", 0))
            if not result.get("runtime_minutes") and detail.get("runtime_minutes"):
                result["runtime_minutes"] = detail.get("runtime_minutes", 0)
            
            # 标识符
            if detail.get("tmdb_id"):
                result["identifiers_json"]["tmdb"] = str(detail.get("tmdb_id", ""))
            
            # 链接
            if detail.get("tmdb_id"):
                result["links_json"]["tmdb"] = f"https://www.themoviedb.org/movie/{detail.get('tmdb_id', '')}"
            
            # 评分
            if detail.get("rating"):
                result["ratings_json"]["tmdb"] = {
                    "value": detail.get("rating", 0),
                    "scale": 10
                }
            
            # 演职人员
            result["credits"] = self._process_credits(credits)
            
            # 图片
            result["images"] = self._process_images(images)
            
            # 视频
            result["videos_json"] = videos
            
            # 出品公司
            if detail.get("production_companies"):
                result["production_companies_json"] = [
                    {"name": c, "country": ""} for c in detail.get("production_companies", [])
                ]
        
        # OMDb 数据
        omdb = raw_data.get("omdb", {})
        if omdb:
            ratings = omdb.get("ratings", {})
            
            # IMDb 评分
            if ratings.get("imdb"):
                result["ratings_json"]["imdb"] = ratings.get("imdb")
            
            # 烂番茄评分
            if ratings.get("rottenTomatoes"):
                result["ratings_json"]["rottenTomatoes"] = ratings.get("rottenTomatoes")
            
            # Metacritic 评分
            if ratings.get("metascore"):
                result["ratings_json"]["metascore"] = ratings.get("metascore")
            
            # 分级
            if omdb.get("rated"):
                result["ratings_json"]["certification"] = {
                    "value": omdb.get("rated", "")
                }
            
            # 获奖
            if omdb.get("awards"):
                result["ratings_json"]["awards"] = {
                    "value": omdb.get("awards", "")
                }
        
        # 百度百科
        baike = raw_data.get("baike", {})
        if baike:
            if baike.get("url"):
                result["links_json"]["baike"] = baike.get("url", "")
            # 百度百科 ID：只记录搜索关键词
            if baike.get("title"):
                result["identifiers_json"]["baike"] = baike.get("title", "")
        
        # Wikipedia
        wikipedia = raw_data.get("wikipedia", {})
        if wikipedia:
            if wikipedia.get("url"):
                result["links_json"]["wikipedia_zh"] = wikipedia.get("url", "")
            # Wikipedia ID：只记录搜索关键词
            if wikipedia.get("title"):
                result["identifiers_json"]["wikipedia_zh"] = wikipedia.get("title", "")
            
            # 剧情详解（从 Wikipedia 获取）
            if wikipedia.get("summary"):
                result["story_text"] = wikipedia.get("summary", "")
            
            # 名言名句
            if wikipedia.get("quotes"):
                result["quotes_json"] = wikipedia.get("quotes", [])
            
            # 获奖
            if wikipedia.get("awards"):
                if result["ratings_json"].get("awards"):
                    result["ratings_json"]["awards"]["value"] += f"\n{'; '.join(wikipedia.get('awards', []))}"
                else:
                    result["ratings_json"]["awards"] = {
                        "value": "; ".join(wikipedia.get("awards", []))
                    }
        
        # 烂番茄
        rotten_tomatoes = raw_data.get("rotten_tomatoes", {})
        if rotten_tomatoes:
            ratings = rotten_tomatoes.get("ratings", {})
            reviews = rotten_tomatoes.get("reviews", [])
            
            if ratings.get("url"):
                result["links_json"]["rottenTomatoes"] = ratings.get("url", "")
            
            if ratings.get("tomatometer"):
                result["ratings_json"]["rottenTomatoes"] = ratings.get("tomatometer")
            
            # 评论
            if not result.get("reviews_json"):
                result["reviews_json"] = []
            result["reviews_json"].extend(reviews)
        
        # Metacritic
        metacritic = raw_data.get("metacritic", {})
        if metacritic:
            rating = metacritic.get("rating", {})
            reviews = metacritic.get("reviews", [])
            
            if rating.get("url"):
                result["links_json"]["metacritic"] = rating.get("url", "")
            
            if rating.get("metascore"):
                result["ratings_json"]["metascore"] = rating.get("metascore")
            
            # 评论
            if not result.get("reviews_json"):
                result["reviews_json"] = []
            result["reviews_json"].extend(reviews)
        
        # 豆瓣评论
        douban = raw_data.get("douban", {})
        if douban:
            if not result.get("reviews_json"):
                result["reviews_json"] = []
            
            # 短评
            comments = douban.get("comments", [])
            result["reviews_json"].extend(comments)
            
            # 长评
            reviews = douban.get("reviews", [])
            result["reviews_json"].extend(reviews)
        
        Logger.success(f"数据合并完成: {work_id}")
        return result
        
    def convert_credits_to_db_format(self, credits: Dict, work_id: str) -> Dict:
        """
        将演职人员转换为数据库格式
        
        Args:
            credits: 演职人员数据
            work_id: 作品 ID
            
        Returns:
            数据库格式的演职人员数据
        """
        result = {
            "people": [],
            "work_credits": []
        }
        
        if not credits:
            return result
        
        person_id_counter = 1
        
        # TMDB 部门映射
        department_map = {
            "Directing": ("direction", "director", "导演"),
            "Writing": ("writing", "writer", "编剧"),
            "Production": ("production", "producer", "制片人"),
            "Camera": ("camera", "cinematographer", "摄影"),
            "Editing": ("editing", "editor", "剪辑"),
            "Art": ("art", "production_designer", "美术"),
            "Costume & Make-Up": ("costume", "costume_designer", "服装设计"),
            "Visual Effects": ("vfx", "vfx_supervisor", "视觉特效"),
            "Sound": ("sound", "sound_designer", "音效"),
            "Actors": ("cast", "actor", "演员")
        }
        
        # 处理演员
        for idx, cast in enumerate(credits.get("cast", [])[:50]):  # 限制前 50 个演员
            tmdb_id = cast.get("id", 0)
            name = cast.get("name", "")
            character = cast.get("character", "")
            profile_path = cast.get("profile_path", "")
            
            person_code = f"p{person_id_counter:06d}"
            person_id_counter += 1
            
            # 添加人物
            result["people"].append({
                "id": person_id_counter - 1,
                "person_code": person_code,
                "name": name,
                "name_en": name,
                "avatar_path": f"people/{person_code}-avatar.jpg" if profile_path else None,
                "profile_link": None,
                "notes": None,
                "extra_json": {
                    "tmdb_id": tmdb_id,
                    "avatarSource": "tmdb"
                }
            })
            
            # 添加演职关系
            result["work_credits"].append({
                "work_id": work_id,
                "person_id": person_id_counter - 1,
                "department": "cast",
                "credit_type": "actor",
                "display_label": "演员",
                "character_name": character,
                "sort_order": idx,
                "is_primary": 1 if idx < 5 else 0,  # 前 5 个为主演
                "link_override": None,
                "extra_json": {
                    "avatarSource": "tmdb"
                }
            })
        
        # 处理演职人员
        for crew in credits.get("crew", []):
            department = crew.get("department", "")
            job = crew.get("job", "")
            name = crew.get("name", "")
            tmdb_id = crew.get("id", 0)
            profile_path = crew.get("profile_path", "")
            
            # 映射部门
            if department in department_map:
                dept, credit_type, label = department_map[department]
            else:
                dept = "crew"
                credit_type = job.lower().replace(" ", "_")
                label = job
            
            person_code = f"p{person_id_counter:06d}"
            person_id_counter += 1
            
            # 添加人物
            result["people"].append({
                "id": person_id_counter - 1,
                "person_code": person_code,
                "name": name,
                "name_en": name,
                "avatar_path": f"people/{person_code}-avatar.jpg" if profile_path else None,
                "profile_link": None,
                "notes": None,
                "extra_json": {
                    "tmdb_id": tmdb_id,
                    "avatarSource": "tmdb"
                }
            })
            
            # 添加演职关系
            result["work_credits"].append({
                "work_id": work_id,
                "person_id": person_id_counter - 1,
                "department": dept,
                "credit_type": credit_type,
                "display_label": label,
                "character_name": None,
                "sort_order": 0,
                "is_primary": 1 if job in ["Director", "Writer"] else 0,
                "link_override": None,
                "extra_json": {
                    "avatarSource": "tmdb"
                }
            })
        
        return result
        
    def _process_credits(self, credits: Dict) -> Dict:
        """处理演职人员"""
        result = {
            "cast": [],
            "crew": []
        }
        
        if not credits:
            return result
        
        # 演员
        for cast in credits.get("cast", []):
            result["cast"].append({
                "id": cast.get("id", 0),
                "name": cast.get("name", ""),
                "character": cast.get("character", ""),
                "order": cast.get("order", 0),
                "profile_path": cast.get("profile_path", "")
            })
        
        # 演职人员
        for crew in credits.get("crew", []):
            result["crew"].append({
                "id": crew.get("id", 0),
                "name": crew.get("name", ""),
                "job": crew.get("job", ""),
                "department": crew.get("department", ""),
                "profile_path": crew.get("profile_path", "")
            })
        
        return result
        
    def _process_images(self, images: Dict) -> Dict:
        """处理图片"""
        result = {
            "posters": [],
            "backdrops": []
        }
        
        if not images:
            return result
        
        for poster in images.get("posters", []):
            result["posters"].append({
                "url": poster.get("url", ""),
                "width": poster.get("width", 0),
                "height": poster.get("height", 0),
                "language": poster.get("language", "")
            })
        
        for backdrop in images.get("backdrops", []):
            result["backdrops"].append({
                "url": backdrop.get("url", ""),
                "width": backdrop.get("width", 0),
                "height": backdrop.get("height", 0),
                "language": backdrop.get("language", "")
            })
        
        return result
        
    def detect_conflicts(self, raw_data: Dict[str, Any]) -> List[Dict]:
        """
        检测字段冲突
        
        Args:
            raw_data: 原始数据
            
        Returns:
            冲突列表
        """
        conflicts = []
        
        # 检测片长冲突
        douban_runtime = raw_data.get("douban", {}).get("runtime_minutes", 0)
        tmdb_runtime = raw_data.get("tmdb", {}).get("detail", {}).get("runtime_minutes", 0)
        
        if douban_runtime and tmdb_runtime and abs(douban_runtime - tmdb_runtime) > 5:
            conflicts.append({
                "field": "runtime_minutes",
                "sources": {
                    "douban": douban_runtime,
                    "tmdb": tmdb_runtime
                }
            })
        
        # 检测年份冲突
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
        raw_dir = self.output_dir / work_id / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = raw_dir / f"{source}.json"
        filepath.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        Logger.info(f"已保存原始数据: {filepath}")
        
    def save_merged_data(self, work_id: str, data: Dict):
        """保存合并后的数据"""
        filepath = self.output_dir / work_id / "data.json"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        filepath.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        Logger.success(f"已保存合并数据: {filepath}")