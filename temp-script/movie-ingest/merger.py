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

import config
from utils import Logger, generate_work_id
from name_matcher import match_person, merge_person_data


class DataMerger:
    """数据合并器"""
    
    def __init__(self, output_dir: str = None):
        if output_dir is None:
            output_dir = config.STAGING_DIR
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

    def _normalize_douban_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """兼容旧扁平豆瓣数据和 crawl_all() 输出的嵌套豆瓣数据。"""
        if not payload:
            return {
                "detail": {},
                "celebrities": {},
                "comments": [],
                "reviews": [],
                "images": {},
                "trailers": []
            }

        detail = payload.get("detail")
        if not isinstance(detail, dict):
            detail = payload

        return {
            "detail": detail or {},
            "celebrities": payload.get("celebrities", {}),
            "comments": payload.get("comments", detail.get("comments", [])) or [],
            "reviews": payload.get("reviews", detail.get("reviews", [])) or [],
            "images": payload.get("images", detail.get("images", {})) or {},
            "trailers": payload.get("trailers", detail.get("trailers", [])) or []
        }

    def _normalize_douban_person(self, person: Any, role: Optional[str] = None) -> Dict[str, Any]:
        if isinstance(person, str):
            return {
                "name": person,
                "nameEn": None,
                "role": role,
                "avatar": None,
                "avatarSource": None,
                "profileLink": None
            }

        if not isinstance(person, dict):
            return {
                "name": "",
                "nameEn": None,
                "role": role,
                "avatar": None,
                "avatarSource": None,
                "profileLink": None
            }

        return {
            "name": person.get("name"),
            "nameEn": person.get("nameEn"),
            "role": person.get("role") or role,
            "avatar": person.get("avatar"),
            "avatarSource": "douban" if person.get("avatar") else None,
            "profileLink": person.get("profileLink"),
            "doubanId": person.get("doubanId"),
            "character": person.get("character"),
            "characterEn": person.get("characterEn")
        }

    def _normalize_douban_video(self, video: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "title": video.get("title") or video.get("name"),
            "url": video.get("url"),
            "thumbnail": video.get("thumbnail") or video.get("cover"),
            "duration": video.get("duration"),
            "source": video.get("source", "douban"),
            "sourceUrl": video.get("source_url"),
            "sourceId": video.get("trailerId")
        }
    
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
            "quotes": None,
            "baikeUrl": None,
            "baikeId": None,
            "wikipediaUrl": None,
            "wikipediaId": None
        }
        
        douban_source = raw_data.get("douban", {})
        douban_payload = self._normalize_douban_payload(douban_source)
        douban = douban_payload["detail"]
        douban_celebrities = douban_payload["celebrities"]
        douban_comments = douban_payload["comments"]
        douban_reviews = douban_payload["reviews"]
        douban_images = douban_payload["images"]
        douban_trailers = douban_payload["trailers"]
        if douban_source:
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
            
            # 演职人员优先使用 /celebrities 页完整结构，兜底兼容详情页上的姓名列表。
            douban_directors = douban_celebrities.get("directors") or douban.get("directors", [])
            douban_writers = douban_celebrities.get("writers") or douban.get("writers", [])
            douban_casts = douban_celebrities.get("cast") or douban.get("casts", [])
            
            result["director"] = [self._normalize_douban_person(d, "导演") for d in douban_directors]
            result["writer"] = [self._normalize_douban_person(w, "编剧") for w in douban_writers]
            # staging 仍沿用主创预览结构：主演前 10 位，其他演员第 11-30 位。
            result["cast"] = [self._normalize_douban_person(c, "演员") for c in douban_casts[:10]]
            result["otherCast"] = [self._normalize_douban_person(c, "演员") for c in douban_casts[10:30]]
            result["all_cast"] = [
                {
                    **self._normalize_douban_person(c, "演员"),
                    "order": index,
                    "isPrimary": index < 10
                }
                for index, c in enumerate(douban_casts)
            ]
            
            # 转换 recommendations 格式，添加 source 和 sourceId
            recommendations = douban.get("recommendations", [])
            similar = []
            for rec in recommendations:
                similar.append({
                    "title": rec.get("title"),
                    "source": rec.get("source", "douban"),
                    "sourceId": rec.get("sourceId", ""),
                    "year": None,  # 豆瓣推荐列表无年份
                    "rating": float(rec.get("rating")) if rec.get("rating") and rec.get("rating").isdigit() else None
                })
            result["similar"] = similar
            
            result["images"] = {
                "poster": "poster-main.jpg" if douban.get("main_poster_url") else None,
                "posters": [],
                "stills": [],
                "wallpapers": [],
                "postersTotal": douban_images.get("posters_total", 0),
                "stillsTotal": douban_images.get("stills_total", 0),
                "wallpapersTotal": douban_images.get("wallpapers_total", 0)
            }
            
            result["videos"] = [
                self._normalize_douban_video(v)
                for v in douban_trailers
                if v.get("url")
            ]
            
            if douban_comments:
                for c in douban_comments:
                    result["reviews"].append({
                        "author": c.get("author"),
                        "source": "豆瓣短评",
                        "date": c.get("date"),
                        "content": c.get("content"),
                        "url": c.get("url"),
                        "title": None
                    })
            
            if douban_reviews:
                for r in douban_reviews:
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
                # 合并 TMDB 补充信息（英文名、头像、角色等）
                result["director"] = self._merge_directors(result.get("director", []), credits)
                result["writer"] = self._merge_writers(result.get("writer", []), credits)
                result["cast"] = self._merge_cast(result.get("cast", []), credits)
                result["otherCast"] = self._merge_other_cast(result.get("otherCast", []), credits)
                result["producer"] = self._extract_producers(credits)
            
            if images:
                result["images"] = self._merge_images(result.get("images", {}), images)
            
            if videos:
                result["videos"].extend(videos)
            
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
        
        baike = raw_data.get("baike", {})
        if baike:
            if baike.get("url"):
                result["baikeUrl"] = baike.get("url")
            if baike.get("baike_id") or baike.get("title"):
                result["baikeId"] = baike.get("baike_id") or baike.get("title")
        
        wikipedia = raw_data.get("wikipedia", {})
        if wikipedia:
            if wikipedia.get("url"):
                result["wikipediaUrl"] = wikipedia.get("url")
            if wikipedia.get("wikipedia_id") or wikipedia.get("title"):
                result["wikipediaId"] = wikipedia.get("wikipedia_id") or wikipedia.get("title")
            
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
        
        result["links"] = {
            "douban": f"https://movie.douban.com/subject/{result.get('doubanId')}/" if result.get('doubanId') else None,
            "imdb": f"https://www.imdb.com/title/{result.get('imdbId')}/" if result.get('imdbId') else None,
            "tmdb": f"https://www.themoviedb.org/movie/{result.get('tmdbId')}" if result.get('tmdbId') else None
        }
        result["module"] = "video"
        result["submodule"] = "movie"
        result["createdAt"] = datetime.now().strftime("%Y-%m-%d")
        result["updatedAt"] = datetime.now().strftime("%Y-%m-%d")
        
        return result
    
    def _build_avatar_url(self, profile_path: str) -> Optional[str]:
        if profile_path:
            if profile_path.startswith("http"):
                return profile_path
            return f"https://image.tmdb.org/t/p/original{profile_path}"
        return None
    
    def _merge_directors(self, douban_directors: List[Dict], credits: Dict) -> List[Dict]:
        """合并导演：豆瓣中文名 + TMDB 补充信息（智能匹配）"""
        tmdb_directors = []
        for crew in credits.get("crew", []):
            if crew.get("job") == "Director":
                tmdb_directors.append({
                    "name": None,
                    "nameEn": crew.get("name", ""),
                    "role": "导演",
                    "avatar": self._build_avatar_url(crew.get("profile_path")),
                    "avatarSource": "tmdb" if crew.get("profile_path") else None,
                    "profileLink": None,
                    "_tmdb_data": crew
                })
        
        if not douban_directors:
            for d in tmdb_directors:
                if "_tmdb_data" in d:
                    del d["_tmdb_data"]
            return tmdb_directors
        
        douban_director_list = [{"name": d if isinstance(d, str) else d.get("name", ""), "nameEn": None} for d in douban_directors]
        douban_director_by_name = {
            d if isinstance(d, str) else d.get("name", ""): d
            for d in douban_directors
        }
        
        result = []
        matched_douban = set()
        
        for tmdb_dir in tmdb_directors:
            douban_match = match_person(tmdb_dir["_tmdb_data"], douban_director_list)
            
            entry = {
                "name": douban_match.get("name") if douban_match else None,
                "nameEn": tmdb_dir["nameEn"],
                "role": "导演",
                "avatar": tmdb_dir["avatar"] or self._normalize_douban_person(douban_director_by_name.get(douban_match.get("name")) if douban_match else {}, "导演").get("avatar"),
                "avatarSource": tmdb_dir["avatarSource"] or ("douban" if douban_match and self._normalize_douban_person(douban_director_by_name.get(douban_match.get("name")), "导演").get("avatar") else None),
                "profileLink": None
            }
            
            if douban_match:
                matched_douban.add(douban_match.get("name"))
            
            result.append(entry)
        
        for douban_name in douban_directors:
            name = douban_name if isinstance(douban_name, str) else douban_name.get("name", "")
            if name not in matched_douban:
                result.append(self._normalize_douban_person(douban_name, "导演"))
        
        return result
    
    def _merge_writers(self, douban_writers: List[Dict], credits: Dict) -> List[Dict]:
        """合并编剧：豆瓣中文名 + TMDB 补充信息（智能匹配）"""
        tmdb_writers = []
        for crew in credits.get("crew", []):
            if crew.get("department") == "Writing":
                role = crew.get("job", "编剧")
                if role == "Screenplay":
                    role = "编剧"
                elif role == "Story":
                    role = "故事"
                elif role == "Novel" or role == "Book":
                    role = "原著"
                tmdb_writers.append({
                    "name": None,
                    "nameEn": crew.get("name", ""),
                    "role": role,
                    "_tmdb_data": crew
                })
        
        if not douban_writers:
            for w in tmdb_writers:
                if "_tmdb_data" in w:
                    del w["_tmdb_data"]
            return tmdb_writers
        
        douban_writer_list = [{"name": w if isinstance(w, str) else w.get("name", ""), "nameEn": None} for w in douban_writers]
        
        result = []
        matched_douban = set()
        
        for tmdb_writer in tmdb_writers:
            douban_match = match_person(tmdb_writer["_tmdb_data"], douban_writer_list)
            
            entry = {
                "name": douban_match.get("name") if douban_match else None,
                "nameEn": tmdb_writer["nameEn"],
                "role": tmdb_writer["role"]
            }
            
            if douban_match:
                matched_douban.add(douban_match.get("name"))
            
            result.append(entry)
        
        for douban_name in douban_writers:
            name = douban_name if isinstance(douban_name, str) else douban_name.get("name", "")
            if name not in matched_douban:
                result.append(self._normalize_douban_person(douban_name, "编剧"))
        
        return result
    
    def _merge_cast(self, douban_cast: List[Dict], credits: Dict) -> List[Dict]:
        """合并主演：豆瓣中文名 + TMDB 补充信息（智能匹配）"""
        tmdb_cast = []
        for c in credits.get("cast", [])[:10]:
            tmdb_cast.append({
                "name": None,
                "nameEn": c.get("name", ""),
                "role": c.get("character", ""),
                "avatar": self._build_avatar_url(c.get("profile_path")),
                "avatarSource": "tmdb" if c.get("profile_path") else None,
                "_tmdb_data": c
            })
        
        if not douban_cast:
            for c in tmdb_cast:
                if "_tmdb_data" in c:
                    del c["_tmdb_data"]
            return tmdb_cast
        
        douban_cast_list = [{"name": c if isinstance(c, str) else c.get("name", ""), "nameEn": None} for c in douban_cast]
        douban_cast_by_name = {
            c if isinstance(c, str) else c.get("name", ""): c
            for c in douban_cast
        }
        
        result = []
        matched_douban = set()
        
        for tmdb_actor in tmdb_cast:
            douban_match = match_person(tmdb_actor["_tmdb_data"], douban_cast_list)
            
            entry = {
                "name": douban_match.get("name") if douban_match else None,
                "nameEn": tmdb_actor["nameEn"],
                "role": tmdb_actor["role"],
                "avatar": tmdb_actor["avatar"] or self._normalize_douban_person(douban_cast_by_name.get(douban_match.get("name")) if douban_match else {}, "演员").get("avatar"),
                "avatarSource": tmdb_actor["avatarSource"] or ("douban" if douban_match and self._normalize_douban_person(douban_cast_by_name.get(douban_match.get("name")), "演员").get("avatar") else None),
                "character": self._normalize_douban_person(douban_cast_by_name.get(douban_match.get("name")), "演员").get("character") if douban_match else None,
                "characterEn": self._normalize_douban_person(douban_cast_by_name.get(douban_match.get("name")), "演员").get("characterEn") if douban_match else None
            }
            
            if douban_match:
                matched_douban.add(douban_match.get("name"))
            
            result.append(entry)
        
        for douban_name in douban_cast[:10]:
            name = douban_name if isinstance(douban_name, str) else douban_name.get("name", "")
            if name not in matched_douban:
                result.append(self._normalize_douban_person(douban_name, "演员"))
        
        return result
    
    def _merge_other_cast(self, douban_other_cast: List[Dict], credits: Dict) -> List[Dict]:
        """合并其他演员：豆瓣中文名 + TMDB 补充信息（智能匹配）"""
        tmdb_other_cast = []
        for c in credits.get("cast", [])[10:30]:
            tmdb_other_cast.append({
                "name": None,
                "nameEn": c.get("name", ""),
                "role": c.get("character", ""),
                "_tmdb_data": c
            })
        
        if not douban_other_cast:
            for c in tmdb_other_cast:
                if "_tmdb_data" in c:
                    del c["_tmdb_data"]
            return tmdb_other_cast
        
        douban_other_cast_list = [{"name": c if isinstance(c, str) else c.get("name", ""), "nameEn": None} for c in douban_other_cast]
        
        result = []
        matched_douban = set()
        
        for tmdb_actor in tmdb_other_cast:
            douban_match = match_person(tmdb_actor["_tmdb_data"], douban_other_cast_list)
            
            entry = {
                "name": douban_match.get("name") if douban_match else None,
                "nameEn": tmdb_actor["nameEn"],
                "role": tmdb_actor["role"]
            }
            
            if douban_match:
                matched_douban.add(douban_match.get("name"))
            
            result.append(entry)
        
        for douban_name in douban_other_cast:
            name = douban_name if isinstance(douban_name, str) else douban_name.get("name", "")
            if name not in matched_douban:
                result.append(self._normalize_douban_person(douban_name, "演员"))
        
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
            "stillsTotal": 0,
            "wallpapersTotal": 0
        }
        result.setdefault("wallpapers", [])
        result.setdefault("wallpapersTotal", 0)
        
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
    
    def merge_credits(self, douban_celebs: Dict, tmdb_celebs: Dict) -> Dict:
        """
        合并豆瓣和 TMDB 演职员数据
        
        改进：支持单数据源
        - 如果 TMDB 失败，只使用豆瓣数据
        - 如果豆瓣失败，只使用 TMDB 数据
        - 只有两者都失败时才返回空
        
        Args:
            douban_celebs: 豆瓣演职员数据（来自 crawl_celebrities）
            tmdb_celebs: TMDB 演职员数据（来自 get_credits）
            
        Returns:
            合并后的演职员数据
        """
        result = {
            "directors": [],
            "writers": [],
            "cast": [],
            "all_cast": [],
            "source": "merged"
        }
        
        # 判断数据源可用性
        has_douban = bool(douban_celebs and (douban_celebs.get("directors") or douban_celebs.get("cast")))
        has_tmdb = bool(tmdb_celebs and (tmdb_celebs.get("crew") or tmdb_celebs.get("cast")))
        
        if not has_douban and not has_tmdb:
            Logger.warning("豆瓣和 TMDB 都没有演职员数据")
            return result
        
        # 只有豆瓣数据
        if has_douban and not has_tmdb:
            Logger.info("仅使用豆瓣数据（TMDB 不可用）")
            return self._merge_from_douban_only(douban_celebs)
        
        # 只有 TMDB 数据
        if has_tmdb and not has_douban:
            Logger.info("仅使用 TMDB 数据（豆瓣不可用）")
            return self._merge_from_tmdb_only(tmdb_celebs)
        
        # 两者都有，正常合并
        result["source"] = "douban+tmdb"
        
        # 合并导演
        tmdb_directors = [c for c in tmdb_celebs.get("crew", []) if c.get("job") == "Director"]
        douban_directors = douban_celebs.get("directors", [])
        
        for tmdb_dir in tmdb_directors:
            douban_match = match_person(tmdb_dir, douban_directors)
            merged = merge_person_data(tmdb_dir, douban_match)
            merged["department"] = "direction"
            merged["role"] = "导演"
            merged["isPrimary"] = True
            result["directors"].append(merged)
        
        # 合并编剧
        tmdb_writers = [c for c in tmdb_celebs.get("crew", []) if c.get("department") == "Writing"]
        douban_writers = douban_celebs.get("writers", [])
        
        for tmdb_writer in tmdb_writers:
            douban_match = match_person(tmdb_writer, douban_writers)
            merged = merge_person_data(tmdb_writer, douban_match)
            merged["department"] = "writing"
            
            job = tmdb_writer.get("job", "编剧")
            if job == "Screenplay":
                merged["role"] = "编剧"
            elif job == "Story":
                merged["role"] = "故事"
            elif job == "Novel":
                merged["role"] = "原著"
            else:
                merged["role"] = job
            
            merged["isPrimary"] = True
            result["writers"].append(merged)
        
        # 合并演员（全部）
        tmdb_cast = tmdb_celebs.get("cast", [])
        douban_cast = douban_celebs.get("cast", [])
        
        for tmdb_actor in tmdb_cast:
            douban_match = match_person(tmdb_actor, douban_cast)
            merged = merge_person_data(tmdb_actor, douban_match)
            merged["department"] = "cast"
            merged["role"] = "演员"
            
            order = tmdb_actor.get("order", 0)
            merged["isPrimary"] = order < 10
            
            result["all_cast"].append(merged)
        
        result["cast"] = result["all_cast"][:10]
        
        Logger.info(f"演职员合并完成: 导演 {len(result['directors'])} 人, "
                   f"编剧 {len(result['writers'])} 人, "
                   f"演员 {len(result['all_cast'])} 人")
        
        return result
    
    def _merge_from_douban_only(self, douban_celebs: Dict) -> Dict:
        """仅使用豆瓣数据"""
        result = {
            "directors": [],
            "writers": [],
            "cast": [],
            "all_cast": [],
            "source": "douban"
        }
        
        # 导演
        for director in douban_celebs.get("directors", []):
            entry = {
                "name": director.get("name"),
                "nameEn": director.get("nameEn"),
                "doubanId": director.get("doubanId"),
                "avatar": director.get("avatar"),
                "doubanAvatar": director.get("avatar"),
                "tmdbAvatar": None,
                "department": "direction",
                "role": "导演",
                "isPrimary": True
            }
            result["directors"].append(entry)
        
        # 编剧
        for writer in douban_celebs.get("writers", []):
            entry = {
                "name": writer.get("name"),
                "nameEn": writer.get("nameEn"),
                "doubanId": writer.get("doubanId"),
                "avatar": writer.get("avatar"),
                "doubanAvatar": writer.get("avatar"),
                "tmdbAvatar": None,
                "department": "writing",
                "role": "编剧",
                "isPrimary": True
            }
            result["writers"].append(entry)
        
        # 演员
        for i, actor in enumerate(douban_celebs.get("cast", [])):
            entry = {
                "name": actor.get("name"),
                "nameEn": actor.get("nameEn"),
                "doubanId": actor.get("doubanId"),
                "character": actor.get("character"),
                "characterEn": actor.get("characterEn"),
                "avatar": actor.get("avatar"),
                "doubanAvatar": actor.get("avatar"),
                "tmdbAvatar": None,
                "department": "cast",
                "role": "演员",
                "order": i,
                "isPrimary": i < 10
            }
            result["all_cast"].append(entry)
        
        result["cast"] = result["all_cast"][:10]
        
        Logger.info(f"豆瓣数据合并完成: 导演 {len(result['directors'])} 人, "
                   f"编剧 {len(result['writers'])} 人, "
                   f"演员 {len(result['all_cast'])} 人")
        
        return result
    
    def _merge_from_tmdb_only(self, tmdb_celebs: Dict) -> Dict:
        """仅使用 TMDB 数据"""
        result = {
            "directors": [],
            "writers": [],
            "cast": [],
            "all_cast": [],
            "source": "tmdb"
        }
        
        # 导演
        tmdb_directors = [c for c in tmdb_celebs.get("crew", []) if c.get("job") == "Director"]
        for director in tmdb_directors:
            avatar_url = f"https://image.tmdb.org/t/p/original{director.get('profile_path')}" if director.get("profile_path") else None
            entry = {
                "name": director.get("name"),
                "nameEn": director.get("name"),
                "tmdbId": director.get("id"),
                "avatar": avatar_url,
                "doubanAvatar": None,
                "tmdbAvatar": avatar_url,
                "department": "direction",
                "role": "导演",
                "isPrimary": True
            }
            result["directors"].append(entry)
        
        # 编剧
        tmdb_writers = [c for c in tmdb_celebs.get("crew", []) if c.get("department") == "Writing"]
        for writer in tmdb_writers:
            job = writer.get("job", "编剧")
            role = "编剧" if job == "Screenplay" else ("故事" if job == "Story" else ("原著" if job == "Novel" else job))
            avatar_url = f"https://image.tmdb.org/t/p/original{writer.get('profile_path')}" if writer.get("profile_path") else None
            
            entry = {
                "name": writer.get("name"),
                "nameEn": writer.get("name"),
                "tmdbId": writer.get("id"),
                "avatar": avatar_url,
                "doubanAvatar": None,
                "tmdbAvatar": avatar_url,
                "department": "writing",
                "role": role,
                "isPrimary": True
            }
            result["writers"].append(entry)
        
        # 演员
        for actor in tmdb_celebs.get("cast", []):
            order = actor.get("order", 0)
            avatar_url = f"https://image.tmdb.org/t/p/original{actor.get('profile_path')}" if actor.get("profile_path") else None
            entry = {
                "name": actor.get("name"),
                "nameEn": actor.get("name"),
                "tmdbId": actor.get("id"),
                "character": actor.get("character"),
                "characterEn": actor.get("character"),
                "avatar": avatar_url,
                "doubanAvatar": None,
                "tmdbAvatar": avatar_url,
                "department": "cast",
                "role": "演员",
                "order": order,
                "isPrimary": order < 10
            }
            result["all_cast"].append(entry)
        
        result["cast"] = result["all_cast"][:10]
        
        Logger.info(f"TMDB 数据合并完成: 导演 {len(result['directors'])} 人, "
                   f"编剧 {len(result['writers'])} 人, "
                   f"演员 {len(result['all_cast'])} 人")
        
        return result
    
    def save_raw_data(self, work_id: str, source: str, data: Dict):
        """保存原始数据"""
        raw_dir = config.RAW_DIR / work_id
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
