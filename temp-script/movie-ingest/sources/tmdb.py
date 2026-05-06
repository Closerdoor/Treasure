# -*- coding: utf-8 -*-
"""
TMDB API 客户端
"""
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional

import config
from utils import Logger


class TMDBClient:
    """TMDB API 客户端"""
    
    def __init__(self):
        self.api_key = config.TMDB_API_KEY
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p/original"
        self.proxy = config.PROXY_URL if config.PROXY_ENABLED else None
        
    async def search_by_imdb(self, imdb_id: str) -> Optional[Dict]:
        """
        通过 IMDb ID 搜索电影
        
        Args:
            imdb_id: IMDb ID（如 tt0816692）
            
        Returns:
            电影数据或 None
        """
        Logger.info(f"正在通过 IMDb ID 搜索 TMDB: {imdb_id}")
        
        url = f"{self.base_url}/find/{imdb_id}"
        params = {
            "api_key": self.api_key,
            "external_source": "imdb_id"
        }
        
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params, proxy=self.proxy) as response:
                    if response.status == 200:
                        data = await response.json()
                        movie_results = data.get("movie_results", [])
                        if movie_results:
                            movie = movie_results[0]
                            Logger.success(f"找到 TMDB 电影: {movie.get('title', '')}")
                            return movie
                    else:
                        Logger.error(f"TMDB API 错误: {response.status}")
        except Exception as e:
            Logger.error(f"TMDB API 请求失败: {e}")
            
        return None
        
    async def get_detail(self, tmdb_id: int) -> Dict:
        """
        获取电影详情
        
        Args:
            tmdb_id: TMDB 电影 ID
            
        Returns:
            电影详情数据
        """
        Logger.info(f"正在获取 TMDB 详情: {tmdb_id}")
        
        url = f"{self.base_url}/movie/{tmdb_id}"
        params = {
            "api_key": self.api_key,
            "language": "zh-CN"
        }
        
        result = {
            "tmdb_id": tmdb_id,
            "source": "tmdb"
        }
        
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params, proxy=self.proxy) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        result["title"] = data.get("title", "")
                        result["original_title"] = data.get("original_title", "")
                        result["year"] = data.get("release_date", "")[:4] if data.get("release_date") else ""
                        result["overview"] = data.get("overview", "")
                        result["runtime_minutes"] = data.get("runtime", 0)
                        result["genres"] = [g.get("name", "") for g in data.get("genres", [])]
                        result["countries"] = [c.get("name", "") for c in data.get("production_countries", [])]
                        result["languages"] = [l.get("name", "") for l in data.get("spoken_languages", [])]
                        result["production_companies"] = [c.get("name", "") for c in data.get("production_companies", [])]
                        result["rating"] = data.get("vote_average", 0)
                        result["rating_count"] = data.get("vote_count", 0)
                        result["imdb_id"] = data.get("imdb_id", "")
                        result["poster"] = f"{self.image_base_url}{data.get('poster_path', '')}" if data.get("poster_path") else ""
                        result["backdrop"] = f"{self.image_base_url}{data.get('backdrop_path', '')}" if data.get("backdrop_path") else ""
                        
                        Logger.success(f"TMDB 详情获取完成")
                    else:
                        Logger.error(f"TMDB API 错误: {response.status}")
        except Exception as e:
            Logger.error(f"TMDB API 请求失败: {e}")
            
        return result
        
    async def get_credits(self, tmdb_id: int) -> Dict:
        """
        获取演职人员
        
        Args:
            tmdb_id: TMDB 电影 ID
            
        Returns:
            演职人员数据
        """
        Logger.info(f"正在获取 TMDB 演职人员: {tmdb_id}")
        
        url = f"{self.base_url}/movie/{tmdb_id}/credits"
        params = {
            "api_key": self.api_key
        }
        
        result = {
            "tmdb_id": tmdb_id,
            "source": "tmdb",
            "cast": [],
            "crew": []
        }
        
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params, proxy=self.proxy) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # 演员
                        for cast in data.get("cast", []):
                            result["cast"].append({
                                "id": cast.get("id", 0),
                                "name": cast.get("name", ""),
                                "character": cast.get("character", ""),
                                "order": cast.get("order", 0),
                                "profile_path": f"{self.image_base_url}{cast.get('profile_path', '')}" if cast.get("profile_path") else ""
                            })
                        
                        # 演职人员
                        for crew in data.get("crew", []):
                            result["crew"].append({
                                "id": crew.get("id", 0),
                                "name": crew.get("name", ""),
                                "job": crew.get("job", ""),
                                "department": crew.get("department", ""),
                                "profile_path": f"{self.image_base_url}{crew.get('profile_path', '')}" if crew.get("profile_path") else ""
                            })
                        
                        Logger.success(f"获取演员 {len(result['cast'])} 人，演职人员 {len(result['crew'])} 人")
                    else:
                        Logger.error(f"TMDB API 错误: {response.status}")
        except Exception as e:
            Logger.error(f"TMDB API 请求失败: {e}")
            
        return result
        
    async def get_images(self, tmdb_id: int) -> Dict:
        """
        获取图片
        
        Args:
            tmdb_id: TMDB 电影 ID
            
        Returns:
            图片数据
        """
        Logger.info(f"正在获取 TMDB 图片: {tmdb_id}")
        
        url = f"{self.base_url}/movie/{tmdb_id}/images"
        params = {
            "api_key": self.api_key,
            "include_image_language": "zh,null"
        }
        
        result = {
            "tmdb_id": tmdb_id,
            "source": "tmdb",
            "posters": [],
            "backdrops": []
        }
        
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params, proxy=self.proxy) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for poster in data.get("posters", []):
                            result["posters"].append({
                                "url": f"{self.image_base_url}{poster.get('file_path', '')}",
                                "width": poster.get("width", 0),
                                "height": poster.get("height", 0),
                                "language": poster.get("iso_639_1", "")
                            })
                        
                        for backdrop in data.get("backdrops", []):
                            result["backdrops"].append({
                                "url": f"{self.image_base_url}{backdrop.get('file_path', '')}",
                                "width": backdrop.get("width", 0),
                                "height": backdrop.get("height", 0),
                                "language": backdrop.get("iso_639_1", "")
                            })
                        
                        Logger.success(f"获取海报 {len(result['posters'])} 张，剧照 {len(result['backdrops'])} 张")
                    else:
                        Logger.error(f"TMDB API 错误: {response.status}")
        except Exception as e:
            Logger.error(f"TMDB API 请求失败: {e}")
            
        return result
        
    async def get_reviews(self, tmdb_id: int, count: int = 20) -> List[Dict]:
        """
        获取用户评论
        
        Args:
            tmdb_id: TMDB 电影 ID
            count: 评论数量
            
        Returns:
            评论列表
        """
        Logger.info(f"正在获取 TMDB 评论: {tmdb_id}")
        
        url = f"{self.base_url}/movie/{tmdb_id}/reviews"
        params = {
            "api_key": self.api_key,
            "language": "en-US"
        }
        
        reviews = []
        
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params, proxy=self.proxy) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for review in data.get("results", [])[:count]:
                            author = review.get("author", "")
                            content = review.get("content", "")
                            rating = review.get("author_details", {}).get("rating", None)
                            created_at = review.get("created_at", "")
                            review_url = review.get("url", "")
                            
                            reviews.append({
                                "author": author,
                                "source": "TMDB",
                                "date": created_at[:10] if created_at else "",
                                "content": content,
                                "rating": rating / 2 if rating else None,
                                "url": review_url,
                                "title": None
                            })
                        
                        Logger.success(f"获取 TMDB 评论 {len(reviews)} 条")
                    else:
                        Logger.error(f"TMDB API 错误: {response.status}")
        except Exception as e:
            Logger.error(f"TMDB API 请求失败: {e}")
            
        return reviews
        
    async def get_videos(self, tmdb_id: int) -> List[Dict]:
        """
        获取视频
        
        Args:
            tmdb_id: TMDB 电影 ID
            
        Returns:
            视频列表
        """
        Logger.info(f"正在获取 TMDB 视频: {tmdb_id}")
        
        url = f"{self.base_url}/movie/{tmdb_id}/videos"
        params = {
            "api_key": self.api_key,
            "language": "zh-CN"
        }
        
        result = []
        
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, params=params, proxy=self.proxy) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        for video in data.get("results", []):
                            if video.get("site", "") == "YouTube":
                                result.append({
                                    "type": video.get("type", ""),
                                    "name": video.get("name", ""),
                                    "source": "youtube",
                                    "key": video.get("key", ""),
                                    "url": f"https://www.youtube.com/watch?v={video.get('key', '')}",
                                    "thumbnail": f"https://img.youtube.com/vi/{video.get('key', '')}/maxresdefault.jpg"
                                })
                        
                        Logger.success(f"获取视频 {len(result)} 个")
                    else:
                        Logger.error(f"TMDB API 错误: {response.status}")
        except Exception as e:
            Logger.error(f"TMDB API 请求失败: {e}")
            
        return result
        
    async def get_all(self, imdb_id: str) -> Dict:
        """
        获取所有 TMDB 数据
        
        Args:
            imdb_id: IMDb ID
            
        Returns:
            完整数据
        """
        result = {
            "imdb_id": imdb_id,
            "source": "tmdb"
        }
        
        # 搜索电影
        movie = await self.search_by_imdb(imdb_id)
        if not movie:
            Logger.warning(f"未找到 TMDB 电影: {imdb_id}")
            return result
            
        tmdb_id = movie.get("id", 0)
        
        # 获取详情
        detail = await self.get_detail(tmdb_id)
        result["detail"] = detail
        
        # 获取演职人员
        credits = await self.get_credits(tmdb_id)
        result["credits"] = credits
        
        # 获取图片
        images = await self.get_images(tmdb_id)
        result["images"] = images
        
        # 获取视频
        videos = await self.get_videos(tmdb_id)
        result["videos"] = videos
        
        # 获取评论
        reviews = await self.get_reviews(tmdb_id)
        result["reviews"] = reviews
        
        return result