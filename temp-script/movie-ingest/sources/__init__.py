# -*- coding: utf-8 -*-
from .douban import DoubanCrawler
from .tmdb import TMDBClient
from .omdb import OMDbClient
from .baike import BaikeCrawler
from .wikipedia import WikipediaCrawler
from .rotten_tomatoes import RottenTomatoesCrawler
from .metacritic import MetacriticCrawler

__all__ = [
    "DoubanCrawler",
    "TMDBClient",
    "OMDbClient",
    "BaikeCrawler",
    "WikipediaCrawler",
    "RottenTomatoesCrawler",
    "MetacriticCrawler",
]
