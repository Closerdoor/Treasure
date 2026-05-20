# -*- coding: utf-8 -*-
"""
Metacritic single-source crawler.

Contract:
- Metacritic is a score/review source in movie-ingest.
- Collect page-level Metascore and user score.
- Collect critic reviews from the critic reviews page. The intentional limit is
  `review_count` because review/comment sources are configured as top 20.
- Keep search URL, selected URL and candidates only for traceability.
"""
import asyncio
import json
import random
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin, urlparse

from bs4 import BeautifulSoup, Tag
from playwright.async_api import Page

import config
from utils import Logger


class MetacriticCrawler:
    """Crawler for Metacritic movie score and critic review data."""

    def __init__(self, page: Page):
        self.page = page
        self.base_url = config.METACRITIC_BASE_URL.rstrip("/")

    async def search(self, title: str, original_title: str = "", year: int = 0) -> Optional[str]:
        result = await self.search_with_candidates(title, original_title, year)
        return result.get("url") or None

    async def search_with_candidates(self, title: str, original_title: str = "", year: int = 0) -> Dict[str, Any]:
        search_title = original_title or title
        Logger.info(f"正在搜索 Metacritic: {search_title}")

        search_urls = [
            f"{self.base_url}/search/{quote(search_title)}/?page=1",
            f"{self.base_url}/search/movie/{quote(search_title)}/results",
        ]
        candidates: List[Dict[str, Any]] = []
        last_error = ""

        for search_url in search_urls:
            try:
                await self.page.goto(search_url, timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                soup = BeautifulSoup(await self.page.content(), "html.parser")

                parsed = self._parse_search_candidates(soup)
                for candidate in parsed:
                    if candidate.get("url") and candidate["url"] not in {item.get("url") for item in candidates}:
                        candidates.append(candidate)

                selected = self._select_candidate(candidates, search_title, year)
                if selected:
                    Logger.success(f"找到 Metacritic 电影: {selected['url']}")
                    return {
                        "url": selected["url"],
                        "search_url": search_url,
                        "candidates": candidates,
                        "selected_candidate": selected,
                    }
            except Exception as e:
                last_error = str(e)
                Logger.warning(f"Metacritic 搜索入口失败: {search_url} - {e}")

        Logger.warning(f"Metacritic 未找到电影: {search_title}")
        return {
            "url": "",
            "search_url": search_urls[0],
            "candidates": candidates,
            "selected_candidate": None,
            "error": last_error or "movie_not_found",
        }

    async def get_rating(self, url: str) -> Dict[str, Any]:
        """Collect page-level Metascore and user score."""
        Logger.info(f"正在获取 Metacritic 评分: {url}")

        result: Dict[str, Any] = {
            "url": url,
            "source": "metacritic",
        }

        try:
            await self.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            soup = BeautifulSoup(await self.page.content(), "html.parser")

            title = self._extract_title(soup)
            if title:
                result["title"] = title

            schema = self._extract_schema_movie(soup)
            if schema:
                result["schema_movie"] = schema

            metascore = self._extract_metascore(soup)
            if metascore:
                result["metascore"] = metascore
                result.setdefault("rating", {})["metacritic"] = metascore

            user_score = self._extract_user_score(soup)
            if user_score:
                result["user_score"] = user_score
                result.setdefault("rating", {})["metacritic_user"] = user_score

            result["score_summary"] = self._extract_score_summary(soup)
            Logger.success("Metacritic 评分获取完成")
        except Exception as e:
            Logger.error(f"Metacritic 评分获取失败: {e}")
            result["error"] = str(e)

        return result

    async def get_reviews(self, url: str, count: int = 20) -> List[Dict[str, Any]]:
        """
        Collect critic reviews from Metacritic.

        `count` is an intentional configuration limit. Current product contract is
        top 20 reviews/comments per review source.
        """
        Logger.info(f"正在获取 Metacritic 影评: {url}")

        reviews_url = f"{url.rstrip('/')}/critic-reviews"
        reviews: List[Dict[str, Any]] = []

        try:
            await self.page.goto(reviews_url, timeout=60000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            soup = BeautifulSoup(await self.page.content(), "html.parser")

            review_items = self._select_review_items(soup)
            for item in review_items[:count]:
                review = self._parse_review_item(item, reviews_url)
                if review.get("content") or review.get("author") or review.get("rating"):
                    reviews.append(review)

            if len(reviews) < count:
                api_reviews = await self._fetch_reviews_api(url, count)
                if len(api_reviews) > len(reviews):
                    reviews = api_reviews[:count]

            Logger.success(f"Metacritic 影评获取完成: {len(reviews)} 条")
        except Exception as e:
            Logger.error(f"Metacritic 影评获取失败: {e}")

        return reviews

    async def _fetch_reviews_api(self, url: str, count: int) -> List[Dict[str, Any]]:
        """Use Metacritic's page-backed JSON endpoint to load beyond the first 10 cards."""
        slug = self._movie_slug(url)
        if not slug:
            return []

        reviews: List[Dict[str, Any]] = []
        offset = 0
        page_size = 10
        total = None

        while len(reviews) < count and (total is None or offset < total):
            api_url = (
                "https://backend.metacritic.com/reviews/metacritic/critic/"
                f"movies/{quote(slug)}/web?offset={offset}&limit={page_size}"
                "&filterBySentiment=all&sort=score"
                "&componentName=critic-reviews"
                "&componentDisplayName=critic+Reviews"
                "&componentType=ReviewList"
            )
            try:
                await self.page.goto(api_url, timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                body_text = await self.page.locator("body").inner_text()
                data = json.loads(body_text)
            except Exception as e:
                Logger.warning(f"Metacritic 影评 API 获取失败 offset={offset}: {e}")
                break

            payload = data.get("data", {}) if isinstance(data, dict) else {}
            items = payload.get("items", []) if isinstance(payload, dict) else []
            total = payload.get("totalResults", total) if isinstance(payload, dict) else total
            if not items:
                break

            for item in items:
                review = self._parse_api_review_item(item)
                if review.get("content") or review.get("author") or review.get("rating"):
                    reviews.append(review)
                    if len(reviews) >= count:
                        break

            offset += page_size

        return reviews

    def _movie_slug(self, url: str) -> str:
        path = urlparse(url).path.strip("/")
        parts = path.split("/")
        if len(parts) >= 2 and parts[0] == "movie":
            return parts[1]
        return ""

    def _parse_api_review_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        score = item.get("score")
        rating = str(score) if score is not None else ""
        publication = self._clean_text(item.get("publicationName", ""))
        return {
            "author": self._clean_author(item.get("author", "")),
            "publication": publication,
            "source": f"Metacritic 路 {publication}" if publication else "Metacritic",
            "date": item.get("date") or "",
            "rating": rating,
            "rating_parsed": self._parse_review_rating(rating),
            "content": self._clean_text(item.get("quote", "")),
            "url": item.get("url") or "",
            "title": None,
        }

    async def crawl(self, title: str, original_title: str = "", year: int = 0, review_count: int = 20) -> Dict[str, Any]:
        """Complete single-source crawl."""
        result: Dict[str, Any] = {
            "title": title,
            "source": "metacritic",
            "requested_year": year,
        }

        search_result = await self.search_with_candidates(title, original_title, year)
        result["search"] = {
            "url": search_result.get("search_url", ""),
            "candidates": search_result.get("candidates", []),
            "selected_candidate": search_result.get("selected_candidate"),
        }

        url = search_result.get("url")
        if not url:
            result["error"] = search_result.get("error") or "movie_not_found"
            return result

        result["url"] = url
        result["rating"] = await self.get_rating(url)
        result["reviews"] = await self.get_reviews(url, review_count)
        result["review_order"] = "Metacritic critic-reviews page order"
        result["review_limit"] = review_count
        return result

    def _parse_search_candidates(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        selectors = [
            ".c-search-item",
            "[data-testid='search-result']",
            ".g-grid-container .c-finderProductCard",
            "a[href*='/movie/']",
        ]

        seen = set()
        for selector in selectors:
            for item in soup.select(selector):
                candidate = self._parse_search_item(item)
                url = candidate.get("url")
                if url and url not in seen:
                    candidates.append(candidate)
                    seen.add(url)
        return candidates

    def _parse_search_item(self, item: Tag) -> Dict[str, Any]:
        link = item if item.name == "a" else item.select_one("a[href*='/movie/']")
        href = link.get("href", "") if link else ""
        text = self._clean_text(item.get_text(" ", strip=True))
        title = ""
        for selector in [".c-search-item__title", "h3", "h2", "[class*='title']", "[data-testid*='title']"]:
            elem = item.select_one(selector)
            if elem:
                title = self._clean_text(elem.get_text(" ", strip=True))
                break
        if not title:
            title = self._clean_search_title(text)

        return {
            "title": title,
            "url": urljoin(self.base_url, href) if href else "",
            "year": self._parse_year(text),
            "score": self._parse_score_100(text),
            "raw_text": text[:500],
        }

    def _select_candidate(self, candidates: List[Dict[str, Any]], title: str, year: int = 0) -> Optional[Dict[str, Any]]:
        movie_candidates = [item for item in candidates if "/movie/" in item.get("url", "")]
        candidates = movie_candidates or candidates
        if not candidates:
            return None

        normalized_title = self._normalize_title(title)

        def score(item: Dict[str, Any]) -> tuple[int, int, int]:
            item_title = self._normalize_title(item.get("title", ""))
            exact = 3 if item_title == normalized_title else 0
            contains = 1 if normalized_title and normalized_title in item_title else 0
            year_match = 3 if year and item.get("year") == year else 0
            year_penalty = -2 if year and item.get("year") and item.get("year") != year else 0
            metascore = item.get("score") or 0
            return (exact + contains + year_match + year_penalty, year_match, metascore)

        return sorted(candidates, key=score, reverse=True)[0]

    def _extract_title(self, soup: BeautifulSoup) -> str:
        heading = soup.select_one("h1") or soup.select_one("[data-testid*='title']")
        if heading:
            return self._clean_text(heading.get_text(" ", strip=True))
        if soup.title:
            return re.sub(r"\s*Reviews?.*$", "", self._clean_text(soup.title.get_text(" ", strip=True)))
        return ""

    def _extract_metascore(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        page_text = soup.get_text(" ", strip=True)
        labeled = re.search(r"Based on\s+[\d,]+\s+Critic Reviews?\s+(\d{1,3})\b", page_text, re.I)
        if labeled:
            value = int(labeled.group(1))
            if 0 <= value <= 100:
                return {
                    "value": value / 10,
                    "scale": 10,
                    "raw": value,
                    "raw_text": labeled.group(0),
                }

        candidates = []
        for elem in soup.select("[data-testid*='metascore'], [class*='metascore'], [class*='score']"):
            text = self._clean_text(
                elem.get("title", "")
                or elem.get("aria-label", "")
                or elem.get_text(" ", strip=True)
            )
            if not text:
                continue
            if "user" in text.lower() and "metascore" not in text.lower():
                continue
            value = self._parse_score_100(text)
            if value is not None:
                candidates.append((value, text))

        if not candidates:
            match = re.search(r"Metascore\s+(\d{1,3})", page_text, re.I)
            if match:
                candidates.append((int(match.group(1)), match.group(0)))

        if not candidates:
            return None

        value, raw_text = candidates[0]
        return {
            "value": value / 10,
            "scale": 10,
            "raw": value,
            "raw_text": raw_text,
        }

    def _extract_user_score(self, soup: BeautifulSoup) -> Optional[Dict[str, Any]]:
        text = soup.get_text(" ", strip=True)
        match = re.search(r"User score.*?Based on\s+[\d,]+\s+User Ratings?\s+([0-9]+(?:\.[0-9]+)?)", text, re.I)
        if not match:
            match = re.search(r"User score\s+([0-9]+(?:\.[0-9]+)?)", text, re.I)
        if match:
            value = float(match.group(1))
            if 0 <= value <= 10:
                return {"value": value, "scale": 10, "raw": value}

        for elem in soup.select("[data-testid*='user'], [class*='user']"):
            elem_text = self._clean_text(elem.get_text(" ", strip=True))
            if not elem_text or "user" not in elem_text.lower():
                continue
            score_match = re.search(r"([0-9]+(?:\.[0-9]+)?)", elem_text)
            if score_match:
                value = float(score_match.group(1))
                if 0 <= value <= 10:
                    return {"value": value, "scale": 10, "raw": value, "raw_text": elem_text}
        return None

    def _extract_score_summary(self, soup: BeautifulSoup) -> Dict[str, str]:
        text = soup.get_text("\n", strip=True)
        summary: Dict[str, str] = {}
        critics_match = re.search(r"(\d+)\s+critic reviews", text, re.I)
        user_match = re.search(r"(\d+)\s+user ratings?", text, re.I)
        if critics_match:
            summary["critic_reviews_text"] = critics_match.group(0)
        if user_match:
            summary["user_ratings_text"] = user_match.group(0)
        return summary

    def _extract_schema_movie(self, soup: BeautifulSoup) -> Dict[str, Any]:
        for script in soup.select("script[type='application/ld+json']"):
            try:
                data = json.loads(script.string or script.get_text() or "{}")
            except json.JSONDecodeError:
                continue
            movie = self._find_schema_movie(data)
            if movie:
                return {
                    "name": movie.get("name", ""),
                    "description": self._clean_text(movie.get("description", "")),
                    "date_published": movie.get("datePublished", ""),
                    "image": movie.get("image", ""),
                    "aggregate_rating": movie.get("aggregateRating", {}),
                }
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

    def _select_review_items(self, soup: BeautifulSoup) -> List[Tag]:
        selectors = [
            ".c-siteReview",
            "[data-testid='review-card']",
            ".review-card",
            "[data-testid*='critic-review']",
            "[class*='criticReview']",
            ".review",
        ]
        for selector in selectors:
            items = soup.select(selector)
            if items:
                return items
        return []

    def _parse_review_item(self, item: Tag, reviews_url: str) -> Dict[str, Any]:
        author = self._first_text(item, [
            ".movie-review-footer__author",
            ".c-siteReview_author",
            "[class*='author']",
            "[data-testid*='author']",
        ])
        publication = self._first_text(item, [
            ".review-card__header",
            ".c-siteReview_source",
            "[class*='source']",
            "[class*='publication']",
            "[data-testid*='publication']",
        ])
        publication = self._clean_publication(publication)
        date = self._first_text(item, [
            ".c-siteReview_date",
            "time",
            "[class*='date']",
        ])
        content = self._first_text(item, [
            ".review-card__quote",
            ".c-siteReview_quote",
            "[class*='quote']",
            "[class*='summary']",
            ".review-body",
            "blockquote",
        ])
        rating_text = self._first_text(item, [
            ".c-siteReviewScore span",
            ".c-siteReviewScore",
            ".c-siteReview_score",
            "[class*='score']",
            ".metascore_w",
        ])
        rating = self._parse_review_rating(rating_text)

        href = self._extract_review_href(item)

        return {
            "author": self._clean_author(author),
            "publication": publication,
            "source": f"Metacritic 路 {publication}" if publication else "Metacritic",
            "date": date,
            "rating": rating_text,
            "rating_parsed": rating,
            "content": content,
            "url": urljoin(self.base_url, href) if href else reviews_url,
            "title": None,
        }

    def _clean_author(self, text: str) -> str:
        return re.sub(r"^By\s+", "", self._clean_text(text), flags=re.I)

    def _clean_publication(self, text: str) -> str:
        text = re.sub(r"^\d{1,3}\s+", "", text or "")
        return self._clean_text(text)

    def _extract_review_href(self, item: Tag) -> str:
        links = item.select("a[href]")
        for link in links:
            href = link.get("href", "")
            label = self._clean_text(link.get_text(" ", strip=True)).lower()
            if href and (href.startswith("http") or "full review" in label):
                return href
        for link in links:
            href = link.get("href", "")
            if href and not href.startswith("/publication/") and not href.startswith("/critic/"):
                return href
        return ""

    def _parse_review_rating(self, text: str) -> Dict[str, Any]:
        text = self._clean_text(text)
        if not text:
            return {}
        value = self._parse_score_100(text)
        if value is None:
            return {"raw": text}
        return {
            "value": value / 10,
            "scale": 10,
            "raw": value,
            "raw_text": text,
        }

    def _first_text(self, item: Tag, selectors: List[str]) -> str:
        for selector in selectors:
            elem = item.select_one(selector)
            if elem:
                text = self._clean_text(elem.get_text(" ", strip=True))
                if text:
                    return text
        return ""

    def _clean_search_title(self, text: str) -> str:
        text = re.sub(r"\b(movie|film)\b", "", text, flags=re.I)
        text = re.sub(r"\b\d{4}\b.*$", "", text)
        text = re.sub(r"\b\d{1,3}\b.*$", "", text)
        return self._clean_text(text)

    def _parse_score_100(self, text: str) -> Optional[int]:
        values = []
        for number in re.findall(r"\b\d{1,3}\b", text or ""):
            value = int(number)
            if 0 <= value <= 100:
                values.append(value)
        if values:
            return values[-1]
        return None

    def _parse_year(self, text: str) -> Optional[int]:
        match = re.search(r"\b(19|20)\d{2}\b", text or "")
        return int(match.group(0)) if match else None

    def _normalize_title(self, title: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", (title or "").lower())

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()
