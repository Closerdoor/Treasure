# -*- coding: utf-8 -*-
"""
OMDb API 客户端。

OMDb 主要用于补充 IMDb / Rotten Tomatoes / Metacritic 评分、分级、奖项、
票房、完整英文剧情和英文演职员文本。
"""
import asyncio
import re
from typing import Any, Dict, List, Optional

import aiohttp

import config
from utils import Logger


class OMDbClient:
    """OMDb API 客户端。"""

    def __init__(self):
        self.api_key = config.OMDB_API_KEY
        self.base_url = "https://www.omdbapi.com"
        self.max_retries = 3
        self.retry_delay = 2.0

    async def _request_with_retry(self, params: Dict[str, Any], timeout: int = 30) -> Optional[Dict[str, Any]]:
        """带重试机制的 API 请求。"""
        if not self.api_key:
            Logger.warning("OMDb API Key 未配置，跳过 OMDb 数据源")
            return None

        last_error = None
        for attempt in range(self.max_retries):
            try:
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.get(self.base_url, params=params, timeout=timeout) as response:
                        if response.status == 200:
                            return await response.json()
                        last_error = f"HTTP {response.status}"
                        Logger.warning(f"OMDb API 错误 (尝试 {attempt + 1}/{self.max_retries}): {response.status}")
            except asyncio.TimeoutError:
                last_error = "请求超时"
                Logger.warning(f"OMDb API 超时 (尝试 {attempt + 1}/{self.max_retries})")
            except aiohttp.ClientError as e:
                last_error = str(e)
                Logger.warning(f"OMDb API 连接失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
            except Exception as e:
                last_error = str(e)
                Logger.warning(f"OMDb API 未知错误 (尝试 {attempt + 1}/{self.max_retries}): {e}")

            if attempt < self.max_retries - 1:
                delay = self.retry_delay * (attempt + 1)
                Logger.info(f"等待 {delay} 秒后重试 OMDb...")
                await asyncio.sleep(delay)

        Logger.error(f"OMDb API 请求失败（已重试 {self.max_retries} 次）: {last_error}")
        return None

    async def get_by_imdb(self, imdb_id: str) -> Dict[str, Any]:
        """
        通过 IMDb ID 获取数据。

        Args:
            imdb_id: IMDb ID，例如 tt1285016
        """
        Logger.info(f"正在通过 IMDb ID 获取 OMDb 数据: {imdb_id}")

        result: Dict[str, Any] = {
            "imdb_id": imdb_id,
            "source": "omdb"
        }
        params = {
            "apikey": self.api_key,
            "i": imdb_id,
            "plot": "full",
            "tomatoes": "true"
        }

        data = await self._request_with_retry(params)
        if not data:
            return result

        result["raw"] = data
        if data.get("Response", "False") != "True":
            result["error"] = self._clean_value(data.get("Error"))
            Logger.warning(f"OMDb 未找到电影 {imdb_id}: {result['error']}")
            return result

        result.update({
            "title": self._clean_value(data.get("Title")),
            "year": self._clean_value(data.get("Year")),
            "rated": self._clean_value(data.get("Rated")),
            "released": self._clean_value(data.get("Released")),
            "runtime": self._clean_value(data.get("Runtime")),
            "runtime_minutes": self._parse_runtime(data.get("Runtime")),
            "genres": self._split_list(data.get("Genre")),
            "directors": self._split_list(data.get("Director")),
            "writers": self._split_list(data.get("Writer")),
            "actors": self._split_list(data.get("Actors")),
            "plot": self._clean_value(data.get("Plot")),
            "languages": self._split_list(data.get("Language")),
            "countries": self._split_list(data.get("Country")),
            "awards": self._clean_value(data.get("Awards")),
            "poster": self._clean_url(data.get("Poster")),
            "metascore": self._parse_int(data.get("Metascore")),
            "imdb_rating": self._parse_float(data.get("imdbRating")),
            "imdb_votes": self._parse_int(data.get("imdbVotes")),
            "imdb_id": self._clean_value(data.get("imdbID")) or imdb_id,
            "type": self._clean_value(data.get("Type")),
            "dvd": self._clean_value(data.get("DVD")),
            "box_office": self._clean_value(data.get("BoxOffice")),
            "production": self._clean_value(data.get("Production")),
            "website": self._clean_url(data.get("Website")),
            "ratings": self._parse_ratings(data),
            "tomatoes": self._parse_tomatoes(data),
        })

        total_seasons = self._parse_int(data.get("totalSeasons"))
        if total_seasons is not None:
            result["total_seasons"] = total_seasons

        Logger.success("OMDb 数据获取完成")
        return result

    def _parse_ratings(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ratings: Dict[str, Any] = {}
        for rating in data.get("Ratings", []):
            source = rating.get("Source", "")
            value = rating.get("Value", "")

            if source == "Internet Movie Database":
                imdb_rating = self._parse_float(value.split("/")[0] if "/" in value else value)
                if imdb_rating is not None:
                    ratings["imdb"] = {"value": imdb_rating, "scale": 10}
            elif source == "Rotten Tomatoes":
                rt_value = self._parse_percent(value)
                if rt_value is not None:
                    ratings["rottenTomatoes"] = {
                        "value": rt_value / 10,
                        "scale": 10,
                        "tomatometer": rt_value
                    }
            elif source == "Metacritic":
                mc_value = self._parse_int(value.split("/")[0] if "/" in value else value)
                if mc_value is not None:
                    ratings["metascore"] = {
                        "value": mc_value / 10,
                        "scale": 10,
                        "raw": mc_value
                    }

        imdb_rating = self._parse_float(data.get("imdbRating"))
        if imdb_rating is not None:
            ratings["imdb"] = {"value": imdb_rating, "scale": 10}

        imdb_votes = self._parse_int(data.get("imdbVotes"))
        if imdb_votes is not None:
            ratings["imdb_votes"] = imdb_votes

        return ratings

    def _parse_tomatoes(self, data: Dict[str, Any]) -> Dict[str, str]:
        tomatoes = {}
        for key, value in data.items():
            if key.startswith("tomato") and self._clean_value(value):
                tomatoes[key] = self._clean_value(value)
        return tomatoes

    def _split_list(self, value: Any) -> List[str]:
        value = self._clean_value(value)
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]

    def _parse_runtime(self, value: Any) -> Optional[int]:
        value = self._clean_value(value)
        if not value:
            return None
        match = re.search(r"(\d+)", value)
        return int(match.group(1)) if match else None

    def _parse_percent(self, value: Any) -> Optional[int]:
        value = self._clean_value(value)
        if not value:
            return None
        return self._parse_int(value.replace("%", ""))

    def _parse_int(self, value: Any) -> Optional[int]:
        value = self._clean_value(value)
        if not value:
            return None
        value = value.replace(",", "").replace("$", "")
        match = re.search(r"-?\d+", value)
        return int(match.group(0)) if match else None

    def _parse_float(self, value: Any) -> Optional[float]:
        value = self._clean_value(value)
        if not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None

    def _clean_url(self, value: Any) -> str:
        value = self._clean_value(value)
        return value if value and value.lower() != "n/a" else ""

    def _clean_value(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        return "" if text.lower() == "n/a" else text
