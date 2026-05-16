# -*- coding: utf-8 -*-
"""
Rotten Tomatoes single-source crawler.

Contract:
- Search Rotten Tomatoes by title and optional release year.
- Collect the movie page scorecard, synopsis, critics consensus and JSON-LD movie metadata.
- Collect critic reviews from `/reviews?type=top`; the only intentional limit is
  `review_count` because review collection is configured as top 20 in movie-ingest.
"""
import asyncio
import json
import random
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup, Tag
from playwright.async_api import Page

import config
from utils import Logger


class RottenTomatoesCrawler:
    """Crawler for Rotten Tomatoes movie score and review data."""

    def __init__(self, page: Page):
        self.page = page
        self.base_url = config.ROTTEN_TOMATOES_BASE_URL.rstrip("/")

    async def search(self, title: str, year: int = 0) -> Optional[str]:
        """Return the best movie URL for `title`, optionally matching `year`."""
        result = await self.search_with_candidates(title, year)
        return result.get("url") or None

    async def search_with_candidates(self, title: str, year: int = 0) -> Dict[str, Any]:
        """Search RT and return the selected URL plus all parsed candidates."""
        Logger.info(f"正在搜索 Rotten Tomatoes: {title}")

        search_url = f"{self.base_url}/search?search={quote(title)}"
        candidates: List[Dict[str, Any]] = []
        try:
            await self.page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            soup = BeautifulSoup(await self.page.content(), "html.parser")
            for row in soup.select("search-page-media-row"):
                candidate = self._parse_search_row(row)
                if candidate.get("url"):
                    candidates.append(candidate)

            selected = self._select_candidate(candidates, title, year)
            if selected:
                Logger.success(f"找到 Rotten Tomatoes 影片: {selected['url']}")
                return {
                    "url": selected["url"],
                    "search_url": search_url,
                    "candidates": candidates,
                    "selected_candidate": selected,
                }

            Logger.warning(f"Rotten Tomatoes 未找到匹配影片: {title}")
            return {
                "url": "",
                "search_url": search_url,
                "candidates": candidates,
                "selected_candidate": None,
            }
        except Exception as e:
            Logger.error(f"Rotten Tomatoes 搜索失败: {e}")
            return {
                "url": "",
                "search_url": search_url,
                "candidates": candidates,
                "selected_candidate": None,
                "error": str(e),
            }

    async def get_ratings(self, url: str) -> Dict[str, Any]:
        """Collect scorecard and movie page metadata."""
        Logger.info(f"正在获取 Rotten Tomatoes 影片页: {url}")

        result: Dict[str, Any] = {
            "url": url,
            "source": "rotten_tomatoes",
        }

        try:
            await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            soup = BeautifulSoup(await self.page.content(), "html.parser")
            result.update(self._extract_page_title(soup))
            result.update(self._extract_scorecard(soup))
            result["metadata"] = self._extract_metadata(soup)
            result["critics_consensus"] = self._extract_critics_consensus(soup)
            result["schema_movie"] = self._extract_schema_movie(soup)

            Logger.success("Rotten Tomatoes 影片页获取完成")
        except Exception as e:
            Logger.error(f"Rotten Tomatoes 影片页获取失败: {e}")
            result["error"] = str(e)

        return result

    async def get_reviews(self, url: str, count: int = 20) -> List[Dict[str, Any]]:
        """
        Collect critic reviews ordered by RT top reviews.

        `count` is an intentional configuration limit. Current product contract is
        top 20 reviews/comments per review source.
        """
        Logger.info(f"正在获取 Rotten Tomatoes 评论: {url}")

        reviews: List[Dict[str, Any]] = []
        reviews_url = f"{url.rstrip('/')}/reviews?type=top"

        try:
            await self.page.goto(reviews_url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))

            soup = BeautifulSoup(await self.page.content(), "html.parser")
            for item in soup.select("review-card-critic")[:count]:
                review = self._parse_review_card(item, reviews_url)
                if review.get("content") or review.get("author"):
                    reviews.append(review)

            Logger.success(f"Rotten Tomatoes 评论获取完成: {len(reviews)} 条")
        except Exception as e:
            Logger.error(f"Rotten Tomatoes 评论获取失败: {e}")

        return reviews

    async def crawl(self, title: str, year: int = 0, review_count: int = 20) -> Dict[str, Any]:
        """Complete single-source crawl."""
        result: Dict[str, Any] = {
            "title": title,
            "source": "rotten_tomatoes",
            "requested_year": year,
        }

        search_result = await self.search_with_candidates(title, year)
        result["search"] = {
            "url": search_result.get("search_url", ""),
            "candidates": search_result.get("candidates", []),
            "selected_candidate": search_result.get("selected_candidate"),
        }

        url = search_result.get("url")
        if not url:
            result["error"] = search_result.get("error") or "movie_not_found"
            return result

        ratings = await self.get_ratings(url)
        result["url"] = url
        result["ratings"] = ratings
        result["reviews"] = await self.get_reviews(url, review_count)
        result["review_order"] = "Rotten Tomatoes /reviews?type=top"
        result["review_limit"] = review_count
        return result

    def _parse_search_row(self, row: Tag) -> Dict[str, Any]:
        title_link = row.select_one("a[data-qa='info-name']") or row.select_one("a[slot='title']")
        poster_link = row.select_one("a[data-qa='thumbnail-link']") or row.select_one("a[slot='thumbnail']")
        image = row.select_one("img")

        href = ""
        if title_link and title_link.get("href"):
            href = title_link["href"]
        elif poster_link and poster_link.get("href"):
            href = poster_link["href"]

        release_year = self._parse_int(row.get("release-year", ""))
        score = self._parse_percent(row.get("tomatometer-score", ""))

        return {
            "title": self._clean_text(title_link.get_text(" ", strip=True)) if title_link else "",
            "url": urljoin(self.base_url, href) if href else "",
            "release_year": release_year,
            "cast": self._split_csv(row.get("cast", "")),
            "tomatometer_score": score,
            "tomatometer_is_certified": self._parse_bool(row.get("tomatometer-is-certified")),
            "tomatometer_sentiment": row.get("tomatometer-sentiment", ""),
            "poster": image.get("src", "") if image else "",
        }

    def _select_candidate(self, candidates: List[Dict[str, Any]], title: str, year: int = 0) -> Optional[Dict[str, Any]]:
        movie_candidates = [item for item in candidates if "/m/" in item.get("url", "")]
        candidates = movie_candidates or candidates
        if not candidates:
            return None

        normalized_title = self._normalize_title(title)

        def score(item: Dict[str, Any]) -> tuple[int, int, int]:
            item_title = self._normalize_title(item.get("title", ""))
            exact = 2 if item_title == normalized_title else 0
            contains = 1 if normalized_title and normalized_title in item_title else 0
            year_match = 2 if year and item.get("release_year") == year else 0
            year_penalty = -2 if year and item.get("release_year") and item.get("release_year") != year else 0
            rt_score = item.get("tomatometer_score") or 0
            return (exact + contains + year_match + year_penalty, year_match, rt_score)

        return sorted(candidates, key=score, reverse=True)[0]

    def _extract_page_title(self, soup: BeautifulSoup) -> Dict[str, str]:
        title = ""
        heading = soup.select_one("h1") or soup.select_one("[slot='title']")
        if heading:
            title = self._clean_text(heading.get_text(" ", strip=True))
        if not title and soup.title:
            title = re.sub(r"\s*-\s*Rotten Tomatoes.*$", "", soup.title.get_text(" ", strip=True))
        return {"title": title} if title else {}

    def _extract_scorecard(self, soup: BeautifulSoup) -> Dict[str, Any]:
        scorecard = soup.select_one("media-scorecard")
        result: Dict[str, Any] = {
            "rating": {},
        }
        if not scorecard:
            return result

        critics_score = self._parse_percent_from_text(self._slot_text(scorecard, "critics-score"))
        audience_score = self._parse_percent_from_text(self._slot_text(scorecard, "audience-score"))
        critics_reviews_text = self._slot_text(scorecard, "critics-reviews")
        audience_reviews_text = self._slot_text(scorecard, "audience-reviews")
        poster = self._slot_attr(scorecard, "poster-image", "src")
        synopsis = self._slot_text(scorecard, "description")

        if critics_score is not None:
            result["tomatometer"] = {
                "value": critics_score / 10,
                "scale": 10,
                "raw": critics_score,
                "reviews_count": self._parse_review_count(critics_reviews_text),
                "reviews_text": critics_reviews_text,
            }
            result["rating"]["rotten_tomatoes"] = result["tomatometer"]

        if audience_score is not None:
            result["audience_score"] = {
                "value": audience_score / 10,
                "scale": 10,
                "raw": audience_score,
                "ratings_count": self._parse_review_count(audience_reviews_text),
                "ratings_text": audience_reviews_text,
            }
            result["rating"]["rotten_tomatoes_audience"] = result["audience_score"]

        if poster:
            result["poster"] = poster
            result["images"] = {"poster": poster}
        if synopsis:
            result["synopsis"] = synopsis

        result["scorecard"] = {
            "critics_reviews_text": critics_reviews_text,
            "audience_reviews_text": audience_reviews_text,
        }
        return result

    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        text = soup.get_text("\n", strip=True)
        metadata: Dict[str, Any] = {}

        rating_match = re.search(r"\b(G|PG|PG-13|R|NC-17|NR),\s*(\d{4}),\s*([^,\n]+),\s*([^\n]+)", text)
        if rating_match:
            metadata["certification"] = rating_match.group(1)
            metadata["year"] = self._parse_int(rating_match.group(2))
            metadata["runtime"] = rating_match.group(3).strip()
            metadata["genres"] = self._split_slash(rating_match.group(4))

        return metadata

    def _extract_critics_consensus(self, soup: BeautifulSoup) -> str:
        text = soup.get_text("\n", strip=True)
        match = re.search(r"Critics Consensus\s*\n+(.+?)(?:\n+Read Critics Reviews|\n+Audience Says|\n+Synopsis)", text, re.S)
        if not match:
            return ""
        return self._clean_text(match.group(1))

    def _extract_schema_movie(self, soup: BeautifulSoup) -> Dict[str, Any]:
        for script in soup.select("script[type='application/ld+json']"):
            try:
                data = json.loads(script.string or script.get_text() or "{}")
            except json.JSONDecodeError:
                continue
            movie = self._find_schema_movie(data)
            if movie:
                return self._normalize_schema_movie(movie)
        return {}

    def _find_schema_movie(self, data: Any) -> Optional[Dict[str, Any]]:
        if isinstance(data, dict):
            if data.get("@type") == "Movie":
                return data
            for value in data.values():
                found = self._find_schema_movie(value)
                if found:
                    return found
        if isinstance(data, list):
            for item in data:
                found = self._find_schema_movie(item)
                if found:
                    return found
        return None

    def _normalize_schema_movie(self, movie: Dict[str, Any]) -> Dict[str, Any]:
        def names(value: Any) -> List[str]:
            if isinstance(value, dict):
                return [value.get("name", "")] if value.get("name") else []
            if isinstance(value, list):
                result = []
                for item in value:
                    result.extend(names(item))
                return [item for item in result if item]
            return []

        return {
            "name": movie.get("name", ""),
            "description": self._clean_text(movie.get("description", "")),
            "image": movie.get("image", ""),
            "date_published": movie.get("datePublished", ""),
            "genre": movie.get("genre", []),
            "directors": names(movie.get("director")),
            "actors": names(movie.get("actor")),
            "aggregate_rating": movie.get("aggregateRating", {}),
        }

    def _parse_review_card(self, item: Tag, reviews_url: str) -> Dict[str, Any]:
        author_link = item.select_one("rt-link[slot='name']")
        publication = item.select_one("[slot='publication']")
        timestamp = item.select_one("[slot='timestamp']")
        rating = item.select_one("[slot='rating']")
        content = item.select_one("[slot='review']")
        review_link = item.select_one("rt-link[slot='review-link']")
        sentiment_icon = item.select_one("score-icon-critics")

        href = review_link.get("href", "") if review_link else ""
        author_href = author_link.get("href", "") if author_link else ""

        return {
            "author": self._clean_text(author_link.get_text(" ", strip=True)) if author_link else "",
            "author_url": urljoin(self.base_url, author_href) if author_href else "",
            "publication": self._clean_text(publication.get_text(" ", strip=True)) if publication else "",
            "date": self._clean_text(timestamp.get_text(" ", strip=True)) if timestamp else "",
            "rating": self._clean_text(rating.get_text(" ", strip=True)) if rating else "",
            "sentiment": sentiment_icon.get("sentiment", "") if sentiment_icon else "",
            "top_critic": self._parse_bool(item.get("top-critic")),
            "top_publication": self._parse_bool(item.get("top-publication")),
            "approved_critic": self._parse_bool(item.get("approved-critic")),
            "content": self._clean_text(content.get_text(" ", strip=True)) if content else "",
            "url": urljoin(self.base_url, href) if href else reviews_url,
            "source": f"Rotten Tomatoes · {self._clean_text(publication.get_text(' ', strip=True))}" if publication else "Rotten Tomatoes",
            "title": None,
        }

    def _slot_text(self, parent: Tag, slot: str) -> str:
        elem = parent.select_one(f"[slot='{slot}']")
        return self._clean_text(elem.get_text(" ", strip=True)) if elem else ""

    def _slot_attr(self, parent: Tag, slot: str, attr: str) -> str:
        elem = parent.select_one(f"[slot='{slot}']")
        return elem.get(attr, "") if elem else ""

    def _parse_percent(self, value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        return self._parse_percent_from_text(str(value))

    def _parse_percent_from_text(self, text: str) -> Optional[int]:
        match = re.search(r"(\d{1,3})\s*%?", text or "")
        if not match:
            return None
        value = int(match.group(1))
        return value if 0 <= value <= 100 else None

    def _parse_review_count(self, text: str) -> Optional[int]:
        if not text:
            return None
        match = re.search(r"([\d,]+)", text)
        if not match:
            return None
        return int(match.group(1).replace(",", ""))

    def _parse_int(self, value: Any) -> Optional[int]:
        match = re.search(r"\d+", str(value or ""))
        return int(match.group(0)) if match else None

    def _parse_bool(self, value: Any) -> bool:
        return str(value).lower() in {"true", "1", "yes"}

    def _split_csv(self, text: str) -> List[str]:
        return [self._clean_text(item) for item in (text or "").split(",") if self._clean_text(item)]

    def _split_slash(self, text: str) -> List[str]:
        return [self._clean_text(item) for item in re.split(r"/|,", text or "") if self._clean_text(item)]

    def _normalize_title(self, title: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (title or "").lower())

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()
