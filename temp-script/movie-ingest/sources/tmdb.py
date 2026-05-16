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
        self.max_retries = 3
        self.retry_delay = 2.0

    async def _request_with_retry(self, url: str, params: Dict, timeout: int = 30) -> Optional[Dict]:
        """
        带重试机制的 API 请求

        Args:
            url: 请求 URL
            params: 请求参数
            timeout: 超时时间（秒）

        Returns:
            JSON 响应数据或 None
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(url, params=params, proxy=self.proxy, timeout=timeout) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            last_error = f"HTTP {response.status}"
                            Logger.warning(f"TMDB API 错误 (尝试 {attempt+1}/{self.max_retries}): {response.status}")
            except asyncio.TimeoutError:
                last_error = "请求超时"
                Logger.warning(f"TMDB API 超时 (尝试 {attempt+1}/{self.max_retries})")
            except aiohttp.ClientError as e:
                last_error = str(e)
                Logger.warning(f"TMDB API 连接失败 (尝试 {attempt+1}/{self.max_retries}): {e}")
            except Exception as e:
                last_error = str(e)
                Logger.warning(f"TMDB API 未知错误 (尝试 {attempt+1}/{self.max_retries}): {e}")

            # 重试前等待
            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (attempt + 1)  # 递增延迟
                Logger.info(f"等待 {delay} 秒后重试...")
                await asyncio.sleep(delay)

        Logger.error(f"TMDB API 请求失败（已重试 {self.max_retries} 次）: {last_error}")
        return None

    async def _get_paginated_results(
        self,
        url: str,
        params: Dict,
        count: Optional[int] = None
    ) -> Dict[str, Any]:
        """读取 TMDB 分页结果；count 为 None 时读取全部页，并记录完整性。"""
        results = []
        page = 1
        total_pages = 1
        complete = True

        while page <= total_pages:
            page_params = dict(params)
            page_params["page"] = page
            data = await self._request_with_retry(url, page_params)
            if not data:
                complete = False
                break

            results.extend(data.get("results", []))
            total_pages = int(data.get("total_pages") or 1)
            if page == 1 or page % 20 == 0 or page == total_pages:
                Logger.info(f"TMDB 分页进度: {page}/{total_pages} 页，累计 {len(results)} 条")
            if count and len(results) >= count:
                return {
                    "items": results[:count],
                    "page_count": page,
                    "total_pages": total_pages,
                    "complete": True,
                    "limited_to": count
                }

            page += 1

        return {
            "items": results,
            "page_count": min(page - 1, total_pages),
            "total_pages": total_pages,
            "complete": complete,
            "limited_to": count
        }

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

        data = await self._request_with_retry(url, params)
        if data:
            movie_results = data.get("movie_results", [])
            if movie_results:
                movie = movie_results[0]
                Logger.success(f"找到 TMDB 电影: {movie.get('title', '')}")
                return movie

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

        data = await self._request_with_retry(url, params)
        if data:
            result["title"] = data.get("title", "")
            result["original_title"] = data.get("original_title", "")
            result["year"] = data.get("release_date", "")[:4] if data.get("release_date") else ""
            result["release_date"] = data.get("release_date", "")
            result["overview"] = data.get("overview", "")
            result["runtime_minutes"] = data.get("runtime", 0)
            result["genres"] = [g.get("name", "") for g in data.get("genres", [])]
            result["countries"] = [c.get("name", "") for c in data.get("production_countries", [])]
            result["languages"] = [l.get("name", "") for l in data.get("spoken_languages", [])]
            result["production_companies"] = [c.get("name", "") for c in data.get("production_companies", [])]
            result["production_company_details"] = data.get("production_companies", [])
            result["rating"] = data.get("vote_average", 0)
            result["rating_count"] = data.get("vote_count", 0)
            result["popularity"] = data.get("popularity", 0)
            result["status"] = data.get("status", "")
            result["tagline"] = data.get("tagline", "")
            result["homepage"] = data.get("homepage", "")
            result["budget"] = data.get("budget", 0)
            result["revenue"] = data.get("revenue", 0)
            result["imdb_id"] = data.get("imdb_id", "")
            result["poster"] = f"{self.image_base_url}{data.get('poster_path', '')}" if data.get("poster_path") else ""
            result["backdrop"] = f"{self.image_base_url}{data.get('backdrop_path', '')}" if data.get("backdrop_path") else ""

            Logger.success(f"TMDB 详情获取完成")

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

        data = await self._request_with_retry(url, params)
        if data:
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
            "include_image_language": "zh,en,null"
        }

        result = {
            "tmdb_id": tmdb_id,
            "source": "tmdb",
            "posters": [],
            "backdrops": [],
            "logos": []
        }

        data = await self._request_with_retry(url, params)
        if data:
            for poster in data.get("posters", []):
                result["posters"].append({
                    "url": f"{self.image_base_url}{poster.get('file_path', '')}",
                    "width": poster.get("width", 0),
                    "height": poster.get("height", 0),
                    "language": poster.get("iso_639_1", ""),
                    "vote_average": poster.get("vote_average", 0),
                    "vote_count": poster.get("vote_count", 0)
                })

            for backdrop in data.get("backdrops", []):
                result["backdrops"].append({
                    "url": f"{self.image_base_url}{backdrop.get('file_path', '')}",
                    "width": backdrop.get("width", 0),
                    "height": backdrop.get("height", 0),
                    "language": backdrop.get("iso_639_1", ""),
                    "vote_average": backdrop.get("vote_average", 0),
                    "vote_count": backdrop.get("vote_count", 0)
                })

            for logo in data.get("logos", []):
                result["logos"].append({
                    "url": f"{self.image_base_url}{logo.get('file_path', '')}",
                    "width": logo.get("width", 0),
                    "height": logo.get("height", 0),
                    "language": logo.get("iso_639_1", ""),
                    "vote_average": logo.get("vote_average", 0),
                    "vote_count": logo.get("vote_count", 0)
                })

            Logger.success(
                f"获取海报 {len(result['posters'])} 张，"
                f"背景图 {len(result['backdrops'])} 张，"
                f"Logo {len(result['logos'])} 张"
            )

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
        reviews_payload = await self._get_paginated_results(url, params, count=count)
        raw_reviews = reviews_payload.get("items", [])
        for review in raw_reviews:
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
                "title": None,
                "author_details": review.get("author_details", {})
            })

        Logger.success(f"获取 TMDB 评论 {len(reviews)} 条")

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

        result = []
        seen_keys = set()
        url = f"{self.base_url}/movie/{tmdb_id}/videos"

        for language in ["zh-CN", "en-US", ""]:
            params = {"api_key": self.api_key}
            if language:
                params["language"] = language
            data = await self._request_with_retry(url, params)
            if not data:
                continue

            for video in data.get("results", []):
                key = video.get("key", "")
                if video.get("site", "") != "YouTube" or not key or key in seen_keys:
                    continue
                seen_keys.add(key)
                result.append({
                    "type": video.get("type", ""),
                    "name": video.get("name", ""),
                    "source": "youtube",
                    "site": video.get("site", ""),
                    "key": key,
                    "url": f"https://www.youtube.com/watch?v={key}",
                    "thumbnail": f"https://img.youtube.com/vi/{key}/maxresdefault.jpg",
                    "language": language or None,
                    "official": video.get("official"),
                    "published_at": video.get("published_at", ""),
                    "size": video.get("size")
                })

        Logger.success(f"获取视频 {len(result)} 个")

        return result

    async def get_external_ids(self, tmdb_id: int) -> Dict:
        """获取 TMDB 外部 ID。"""
        Logger.info(f"正在获取 TMDB 外部 ID: {tmdb_id}")
        url = f"{self.base_url}/movie/{tmdb_id}/external_ids"
        params = {"api_key": self.api_key}
        data = await self._request_with_retry(url, params)
        result = {
            "tmdb_id": tmdb_id,
            "source": "tmdb"
        }
        if data:
            result.update({
                "imdb_id": data.get("imdb_id", ""),
                "wikidata_id": data.get("wikidata_id", ""),
                "facebook_id": data.get("facebook_id", ""),
                "instagram_id": data.get("instagram_id", ""),
                "twitter_id": data.get("twitter_id", "")
            })
        return result

    async def get_release_dates(self, tmdb_id: int) -> Dict:
        """获取 TMDB 上映日期与分级信息。"""
        Logger.info(f"正在获取 TMDB 上映日期/分级: {tmdb_id}")
        url = f"{self.base_url}/movie/{tmdb_id}/release_dates"
        params = {"api_key": self.api_key}
        data = await self._request_with_retry(url, params)
        result = {
            "tmdb_id": tmdb_id,
            "source": "tmdb",
            "results": []
        }
        if data:
            for item in data.get("results", []):
                result["results"].append({
                    "country": item.get("iso_3166_1", ""),
                    "release_dates": item.get("release_dates", [])
                })
        return result

    async def get_keywords(self, tmdb_id: int) -> List[Dict]:
        """获取 TMDB 关键词。"""
        Logger.info(f"正在获取 TMDB 关键词: {tmdb_id}")
        url = f"{self.base_url}/movie/{tmdb_id}/keywords"
        params = {"api_key": self.api_key}
        data = await self._request_with_retry(url, params)
        return data.get("keywords", []) if data else []

    async def get_recommendations(self, tmdb_id: int, count: int = None) -> Dict[str, Any]:
        """获取 TMDB 推荐作品；默认全量分页获取。"""
        Logger.info(f"正在获取 TMDB 推荐作品: {tmdb_id}")
        url = f"{self.base_url}/movie/{tmdb_id}/recommendations"
        params = {"api_key": self.api_key, "language": "zh-CN"}
        return await self._get_paginated_results(url, params, count=count)

    async def get_similar(self, tmdb_id: int, count: int = None) -> Dict[str, Any]:
        """获取 TMDB 相似作品；默认全量分页获取。"""
        Logger.info(f"正在获取 TMDB 相似作品: {tmdb_id}")
        url = f"{self.base_url}/movie/{tmdb_id}/similar"
        params = {"api_key": self.api_key, "language": "zh-CN"}
        return await self._get_paginated_results(url, params, count=count)

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

        (
            detail,
            credits,
            images,
            videos,
            reviews,
            external_ids,
            release_dates,
            keywords,
            recommendations,
            similar
        ) = await asyncio.gather(
            self.get_detail(tmdb_id),
            self.get_credits(tmdb_id),
            self.get_images(tmdb_id),
            self.get_videos(tmdb_id),
            self.get_reviews(tmdb_id),
            self.get_external_ids(tmdb_id),
            self.get_release_dates(tmdb_id),
            self.get_keywords(tmdb_id),
            self.get_recommendations(tmdb_id),
            self.get_similar(tmdb_id)
        )

        result["detail"] = detail
        result["credits"] = credits
        result["images"] = images
        result["videos"] = videos
        result["reviews"] = reviews
        result["external_ids"] = external_ids
        result["release_dates"] = release_dates
        result["keywords"] = keywords
        result["recommendations"] = recommendations.get("items", [])
        result["recommendations_meta"] = {
            "page_count": recommendations.get("page_count", 0),
            "total_pages": recommendations.get("total_pages", 0),
            "complete": recommendations.get("complete", False),
            "limited_to": recommendations.get("limited_to")
        }
        result["similar"] = similar.get("items", [])
        result["similar_meta"] = {
            "page_count": similar.get("page_count", 0),
            "total_pages": similar.get("total_pages", 0),
            "complete": similar.get("complete", False),
            "limited_to": similar.get("limited_to")
        }

        return result
