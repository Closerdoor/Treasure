# -*- coding: utf-8 -*-
"""
OMDb API 客户端
"""
import asyncio
import aiohttp
from typing import Dict, Any, Optional

import config
from utils import Logger


class OMDbClient:
    """OMDb API 客户端"""
    
    def __init__(self):
        self.api_key = config.OMDB_API_KEY
        self.base_url = "https://www.omdbapi.com"
        
    async def get_by_imdb(self, imdb_id: str) -> Dict:
        """
        通过 IMDb ID 获取数据
        
        Args:
            imdb_id: IMDb ID（如 tt0816692）
            
        Returns:
            电影数据
        """
        Logger.info(f"正在通过 IMDb ID 获取 OMDb 数据: {imdb_id}")
        
        params = {
            "apikey": self.api_key,
            "i": imdb_id,
            "plot": "full",
            "tomatoes": "true"
        }
        
        result = {
            "imdb_id": imdb_id,
            "source": "omdb"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data.get("Response", "False") == "True":
                            # 基本信息
                            result["title"] = data.get("Title", "")
                            result["year"] = data.get("Year", "")
                            result["rated"] = data.get("Rated", "")  # 分级
                            result["runtime"] = data.get("Runtime", "")
                            result["genres"] = data.get("Genre", "").split(", ") if data.get("Genre") else []
                            result["directors"] = data.get("Director", "").split(", ") if data.get("Director") else []
                            result["writers"] = data.get("Writer", "").split(", ") if data.get("Writer") else []
                            result["actors"] = data.get("Actors", "").split(", ") if data.get("Actors") else []
                            result["plot"] = data.get("Plot", "")
                            result["languages"] = data.get("Language", "").split(", ") if data.get("Language") else []
                            result["countries"] = data.get("Country", "").split(", ") if data.get("Country") else []
                            result["awards"] = data.get("Awards", "")
                            result["poster"] = data.get("Poster", "")
                            
                            # 评分
                            ratings = {}
                            for rating in data.get("Ratings", []):
                                source = rating.get("Source", "")
                                value = rating.get("Value", "")
                                
                                if source == "Internet Movie Database":
                                    # IMDb 评分（10 分制）
                                    imdb_rating = value.split("/")[0] if "/" in value else value
                                    ratings["imdb"] = {
                                        "value": float(imdb_rating),
                                        "scale": 10
                                    }
                                elif source == "Rotten Tomatoes":
                                    # 烂番茄评分（百分比）
                                    rt_value = int(value.replace("%", ""))
                                    ratings["rottenTomatoes"] = {
                                        "value": rt_value / 10,
                                        "scale": 10,
                                        "tomatometer": rt_value
                                    }
                                elif source == "Metacritic":
                                    # Metacritic 评分（100 分制）
                                    mc_value = int(value.split("/")[0] if "/" in value else value)
                                    ratings["metascore"] = {
                                        "value": mc_value / 10,
                                        "scale": 10,
                                        "raw": mc_value
                                    }
                            
                            # IMDb 评分（直接字段）
                            if data.get("imdbRating"):
                                ratings["imdb"] = {
                                    "value": float(data.get("imdbRating", "0")),
                                    "scale": 10
                                }
                            
                            # IMDb 评价人数
                            if data.get("imdbVotes"):
                                ratings["imdb_votes"] = data.get("imdbVotes", "").replace(",", "")
                            
                            result["ratings"] = ratings
                            
                            Logger.success(f"OMDb 数据获取完成")
                        else:
                            Logger.warning(f"OMDb 未找到电影: {imdb_id}")
                    else:
                        Logger.error(f"OMDb API 错误: {response.status}")
        except Exception as e:
            Logger.error(f"OMDb API 请求失败: {e}")
            
        return result