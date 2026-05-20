# -*- coding: utf-8 -*-
"""
百度百科爬虫

百度百科是演职员信息最完整的来源，包含：
- 导演、编剧、主演、全部演员
- 角色名（中英文对照）
- 头像图片 URL
- 备注信息
- 人物词条链接（lemmaId）
"""
import asyncio
import json
import random
import re
from typing import Dict, Any, Optional, List
from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.async_api import Page

import config
from utils import Logger


class BaikeCrawler:
    """百度百科爬虫"""
    
    def __init__(self, page: Page):
        self.page = page
        self.base_url = config.BAIKE_BASE_URL
        
    async def search(self, title: str) -> Optional[str]:
        """
        搜索词条
        
        Args:
            title: 电影标题
            
        Returns:
            词条 URL 或 None
        """
        Logger.info(f"正在搜索百度百科: {title}")
        
        # 直接访问词条页面
        encoded_title = quote(title)
        url = f"{self.base_url}/item/{encoded_title}"
        
        try:
            await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            # 检查是否跳转到搜索页面
            current_url = self.page.url
            if "search" in current_url:
                # 在搜索结果中查找
                content = await self.page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # 查找第一个搜索结果
                first_result = soup.select_one(".result-list .result-title a")
                if first_result:
                    href = first_result.get("href", "")
                    if href:
                        url = f"{self.base_url}{href}" if href.startswith("/") else href
                        await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                else:
                    Logger.warning(f"百度百科未找到词条: {title}")
                    return None
            
            Logger.success(f"找到百度百科词条: {url}")
            return url
            
        except Exception as e:
            Logger.error(f"百度百科搜索失败: {e}")
            return None
            
    async def get_detail(self, url: str) -> Dict[str, Any]:
        """
        获取词条内容，包括演职员 JSON 数据
        
        百度百科演职员数据来源：
        1. PAGE_DATA.card.left/right - 导演、编剧、主演、制片人（基本信息）
        2. PAGE_DATA.featureInfo.data.majorActors - 主要演员（带头像，数量少）
        3. HTML actor 模块 - 完整演员表（数量多，无头像）
        
        Args:
            url: 词条 URL
            
        Returns:
            词条数据（包含演职员信息）
        """
        Logger.info(f"正在获取百度百科内容: {url}")
        
        result = {
            "url": url,
            "source": "baike"
        }
        
        try:
            # 等待页面加载完成（role 模块需要更长时间）
            await asyncio.sleep(5)
            
            # 等待 role 模块加载
            try:
                await self.page.wait_for_selector('[data-module-type="role"]', timeout=10000)
            except:
                Logger.warning("role 模块未找到，继续尝试...")
            
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 词条名
            title_elem = soup.select_one("h1") or soup.select_one(".lemmaTitle") or soup.select_one(".lemma-title")
            title_text = title_elem.text.strip() if title_elem else ""
            if not title_text:
                match = re.search(r"/item/([^/]+)", url)
                if match:
                    from urllib.parse import unquote
                    title_text = unquote(match.group(1))
            result["title"] = title_text
            
            # 词条 ID
            match = re.search(r"/item/([^/]+)", url)
            if match:
                from urllib.parse import unquote
                baike_id = unquote(match.group(1))
                result["baike_id"] = baike_id
            
            # 摘要
            result["summary"] = self._extract_summary(soup, content)
            
            # 提取 PAGE_DATA JSON
            page_data = self._extract_page_data(content)
            basic_info = {}

            # 提取演职员数据
            credits_data = {}

            if page_data:
                basic_info.update(self._extract_basic_info_from_page_data(page_data))
                # 从 card 提取导演、编剧、主演、制片人
                credits_data = self._extract_credits_from_card(page_data)
                
                # 从 featureInfo 提取主要演员头像
                major_actors_avatars = self._extract_major_actors_avatars(page_data)
                
                # 合并头像到演员列表
                for actor in credits_data.get("cast", []):
                    name = actor.get("name", "")
                    if name in major_actors_avatars:
                        actor["avatar"] = major_actors_avatars[name]
            
            # 从 role 模块提取演员数据（优先）
            role_cast = self._extract_cast_from_role_module(soup)
            
            if role_cast:
                # 使用 role 模块数据
                credits_data["cast"] = role_cast
            else:
                # 从 HTML 提取完整演员表（补充角色名、备注）
                html_cast = self._extract_cast_from_html(soup)
                
                # 合并 HTML 数据到 credits_data
                if html_cast:
                    # 如果 card 中没有演员，使用 HTML 数据
                    if not credits_data.get("cast"):
                        credits_data["cast"] = html_cast
                    else:
                        # 合并：用 HTML 数据补充角色名、备注
                        for html_actor in html_cast:
                            name = html_actor.get("name", "")
                            # 查找是否已存在
                            existing = [a for a in credits_data["cast"] if a.get("name") == name]
                            if existing:
                                idx = credits_data["cast"].index(existing[0])
                                # 补充角色名、备注
                                if html_actor.get("character") and not credits_data["cast"][idx].get("character"):
                                    credits_data["cast"][idx]["character"] = html_actor["character"]
                                if html_actor.get("characterEn") and not credits_data["cast"][idx].get("characterEn"):
                                    credits_data["cast"][idx]["characterEn"] = html_actor["characterEn"]
                                if html_actor.get("note") and not credits_data["cast"][idx].get("note"):
                                    credits_data["cast"][idx]["note"] = html_actor["note"]
                            else:
                                # 新演员，添加到列表
                                credits_data["cast"].append(html_actor)

            basic_info.update({
                key: value
                for key, value in self._extract_basic_info_from_html(soup).items()
                if key not in basic_info or not basic_info.get(key)
            })
            basic_info.update({
                key: value
                for key, value in self._extract_basic_info_from_embedded_json(content).items()
                if key not in basic_info or not basic_info.get(key)
            })
            if basic_info:
                basic_info = self._filter_basic_info(basic_info)
                result["basic_info"] = basic_info
                result.update(self._normalize_basic_info(basic_info))
                self._augment_credits_from_basic_info(credits_data, result)

            if credits_data:
                credits_data = self._dedupe_credits(credits_data)
                result["credits"] = credits_data
                Logger.info(f"百度百科演职员数据: 导演 {len(credits_data.get('directors', []))} 人, "
                           f"编剧 {len(credits_data.get('writers', []))} 人, "
                           f"演员 {len(credits_data.get('cast', []))} 人")
            
            Logger.success(f"百度百科内容获取完成")
            
        except Exception as e:
            Logger.error(f"百度百科内容获取失败: {e}")
            import traceback
            traceback.print_exc()
            
        return result

    def _extract_summary(self, soup: BeautifulSoup, html_content: str) -> str:
        """Extract Baike summary from old/new layouts and metadata fallbacks."""
        selectors = [
            ".lemma-summary",
            ".J-summary",
            "[data-module-type='lemmaSummary']",
            "[data-module-type='summary']",
            ".para",
            "meta[name='description']",
            "meta[property='og:description']",
        ]
        for selector in selectors:
            elem = soup.select_one(selector)
            if not elem:
                continue
            text = elem.get("content", "") if elem.name == "meta" else elem.get_text(" ", strip=True)
            text = self._clean_text(text)
            if text:
                return text

        patterns = [
            r'"description"\s*:\s*"([^"]{20,})"',
            r'"lemmaDesc"\s*:\s*"([^"]{20,})"',
            r'"summary"\s*:\s*"([^"]{20,})"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html_content)
            if match:
                text = self._clean_text(match.group(1))
                if text:
                    return text
        return ""

    def _dedupe_credits(self, credits: Dict[str, List]) -> Dict[str, List]:
        """Deduplicate people inside each credit role while preserving first-seen data."""
        deduped: Dict[str, List] = {}
        for role, items in (credits or {}).items():
            if not isinstance(items, list):
                deduped[role] = items
                continue
            seen = set()
            role_items = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                name = self._clean_text(item.get("name", ""))
                if not name:
                    continue
                key = (name, self._clean_text(item.get("character", "")))
                if key in seen:
                    continue
                seen.add(key)
                normalized = dict(item)
                normalized["name"] = name
                role_items.append(normalized)
            deduped[role] = role_items
        return deduped

    def _extract_page_data(self, html_content: str) -> Optional[Dict]:
        """
        从百度百科页面提取 PAGE_DATA JSON
        
        Args:
            html_content: HTML 内容
            
        Returns:
            PAGE_DATA 字典
        """
        try:
            match = re.search(r'window\.PAGE_DATA\s*=\s*(\{.+?\});?\s*</script>', html_content, re.DOTALL)
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                Logger.info("成功提取 PAGE_DATA")
                return data
        except Exception as e:
            Logger.warning(f"PAGE_DATA 提取失败: {e}")

        return None

    def _extract_basic_info_from_page_data(self, page_data: Dict) -> Dict[str, str]:
        """从 PAGE_DATA.card 抽取百科基础信息表。"""
        basic_info = {}
        card = page_data.get("card", {}) or {}
        items = []

        for key in ("content", "left", "right"):
            value = card.get(key) or []
            if isinstance(value, list):
                items.extend(value)

        for item in items:
            if not isinstance(item, dict):
                continue
            label = (
                item.get("name")
                or item.get("label")
                or item.get("title")
                or item.get("key")
                or ""
            )
            label = self._clean_text(label)
            value = self._format_baike_data_list(item.get("data", []))
            if label and value:
                basic_info[label] = value

        return basic_info

    def _extract_basic_info_from_html(self, soup: BeautifulSoup) -> Dict[str, str]:
        """从 HTML 结构兜底抽取百科基础信息表。"""
        basic_info = {}

        for item in soup.select(".basicInfo-item, .basic-info .basicInfo-item"):
            name_elem = item.select_one(".basicInfo-item.name")
            value_elem = item.select_one(".basicInfo-item.value")
            if not name_elem or not value_elem:
                continue
            label = self._clean_text(name_elem.get_text(" ", strip=True))
            value = self._clean_text(value_elem.get_text(" ", strip=True))
            if label and value:
                basic_info[label] = value

        for dl in soup.select("dl"):
            children = [child for child in dl.children if getattr(child, "name", None) in ("dt", "dd")]
            for idx in range(0, len(children) - 1, 2):
                if children[idx].name != "dt" or children[idx + 1].name != "dd":
                    continue
                label = self._clean_text(children[idx].get_text(" ", strip=True))
                value = self._clean_text(children[idx + 1].get_text(" ", strip=True))
                if label and value and len(label) <= 20:
                    basic_info.setdefault(label, value)

        return basic_info

    def _extract_basic_info_from_embedded_json(self, html_content: str) -> Dict[str, str]:
        """从新版百科页面内嵌 JSON 片段抽取基础信息表。"""
        basic_info = {}
        decoder = json.JSONDecoder()
        for match in re.finditer(r'\{"key"\s*:', html_content):
            try:
                item, _ = decoder.raw_decode(html_content[match.start():])
            except Exception:
                continue

            if not isinstance(item, dict) or "title" not in item or "data" not in item:
                continue
            label = self._clean_text(item.get("title", ""))
            value = self._format_baike_data_list(item.get("data", []), item.get("delimiter", "、"))
            if label and value:
                basic_info[label] = value

        return basic_info

    def _format_baike_data_list(self, data_list: Any, delimiter: str = "、") -> str:
        values = []
        if not isinstance(data_list, list):
            return self._clean_text(str(data_list)) if data_list else ""

        for data in data_list:
            if not isinstance(data, dict):
                values.append(str(data))
                continue
            data_type = data.get("dataType")
            if "text" in data and isinstance(data.get("text"), list):
                text_parts = []
                for item in data.get("text", []):
                    if isinstance(item, dict):
                        text_parts.append(str(item.get("text", "")))
                    else:
                        text_parts.append(str(item))
                text = self._clean_text("".join(text_parts))
                if text:
                    values.append(text)
            elif data_type == "lemma":
                value = data.get("value", {}) or {}
                text = value.get("title") or value.get("lemmaTitle") or value.get("text")
                if text:
                    values.append(str(text))
            elif "value" in data:
                values.append(str(data.get("value")))

        delimiter = delimiter or "、"
        return self._clean_text(delimiter.join(v for v in values if v))

    def _normalize_basic_info(self, basic_info: Dict[str, str]) -> Dict[str, Any]:
        """把百科中文字段名规范化为便于合并/核对的字段。"""
        aliases = {
            "中文名": "title_cn",
            "外文名": "title_foreign",
            "其他译名": "other_titles",
            "类型": "genres",
            "出品公司": "production_companies",
            "制片地区": "production_region",
            "拍摄日期": "shooting_date",
            "发行公司": "distributors",
            "导演": "directors_text",
            "编剧": "writers_text",
            "制片人": "producers_text",
            "主演": "cast_text",
            "片长": "runtime",
            "上映时间": "release_time",
            "对白语言": "languages",
            "语言": "languages",
            "色彩": "color",
            "imdb编码": "imdb_id",
            "IMDb编码": "imdb_id",
            "出品时间": "production_year",
            "制片成本": "budget",
        }
        normalized = {}
        compact_map = {re.sub(r"\s+", "", key): value for key, value in basic_info.items()}

        for label, field in aliases.items():
            compact = re.sub(r"\s+", "", label)
            value = compact_map.get(compact)
            if not value:
                continue
            if field in {"other_titles", "genres", "production_companies", "distributors"}:
                normalized[field] = self._split_text_list(value)
            else:
                normalized[field] = value

        return normalized

    def _filter_basic_info(self, basic_info: Dict[str, str]) -> Dict[str, str]:
        allowed = {
            "中文名", "外文名", "其他译名", "类型", "出品公司", "制片地区", "拍摄日期",
            "发行公司", "导演", "编剧", "制片人", "主演", "片长", "上映时间",
            "对白语言", "语言", "色彩", "imdb编码", "IMDb编码", "出品时间", "制片成本",
        }
        compact_allowed = {re.sub(r"\s+", "", item) for item in allowed}
        filtered = {}
        for key, value in basic_info.items():
            compact = re.sub(r"\s+", "", key)
            if compact in compact_allowed:
                filtered[key] = value
        return filtered

    def _augment_credits_from_basic_info(self, credits: Dict[str, List], normalized: Dict[str, Any]):
        if not credits:
            credits.update({"directors": [], "writers": [], "cast": [], "producers": []})

        mappings = [
            ("directors_text", "directors"),
            ("writers_text", "writers"),
            ("producers_text", "producers"),
            ("cast_text", "cast"),
        ]
        for text_key, credit_key in mappings:
            existing = {item.get("name") for item in credits.get(credit_key, []) if isinstance(item, dict)}
            for name in self._split_person_names(normalized.get(text_key, "")):
                if name and name not in existing:
                    credits.setdefault(credit_key, []).append({"name": name, "source": "baike_basic_info"})
                    existing.add(name)

    def _split_person_names(self, value: str) -> List[str]:
        value = re.sub(r"\s*等$", "", value or "")
        return [
            item.strip()
            for item in re.split(r"[、,，/／;；]", value)
            if item.strip()
        ]

    def _split_text_list(self, value: str) -> List[str]:
        return [
            item.strip()
            for item in re.split(r"[/／、,，;；]", value)
            if item.strip()
        ]

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()
    
    def _extract_credits_from_card(self, page_data: Dict) -> Dict[str, List]:
        """
        从 PAGE_DATA.card 提取演职员数据
        
        Args:
            page_data: PAGE_DATA 字典
            
        Returns:
            演职员数据
        """
        credits = {
            "directors": [],
            "writers": [],
            "cast": [],
            "producers": []
        }
        
        card = page_data.get("card", {}) or {}
        
        # 百度百科有两种数据结构：
        # 1. card.left / card.right（旧版）
        # 2. card.content（新版）
        
        # 尝试从 content 提取
        content_items = card.get("content") or []
        if content_items:
            # 新版结构：所有字段在 content 数组中
            for item in content_items:
                key = item.get("key", "")
                data_list = item.get("data", [])
                
                if key == "director":
                    for d in data_list:
                        # 尝试 lemma 类型
                        if d.get("dataType") == "lemma":
                            name = d.get("value", {}).get("title", "")
                            lemma_id = d.get("value", {}).get("id", "")
                            if name:
                                credits["directors"].append({
                                    "name": name,
                                    "lemmaId": str(lemma_id),
                                    "link": f"/item/{name}/{lemma_id}" if lemma_id else None
                                })
                        # 尝试 text 类型
                        elif d.get("dataType") == "text":
                            text_list = d.get("text", [])
                            for t in text_list:
                                if t.get("tag") == "text":
                                    name = t.get("text", "").strip()
                                    if name:
                                        credits["directors"].append({
                                            "name": name,
                                            "lemmaId": None,
                                            "link": None
                                        })
                
                elif key == "scriptwriter":
                    for d in data_list:
                        if d.get("dataType") == "lemma":
                            name = d.get("value", {}).get("title", "")
                            lemma_id = d.get("value", {}).get("id", "")
                            if name:
                                credits["writers"].append({
                                    "name": name,
                                    "lemmaId": str(lemma_id),
                                    "link": f"/item/{name}/{lemma_id}" if lemma_id else None
                                })
                        elif d.get("dataType") == "text":
                            text_list = d.get("text", [])
                            for t in text_list:
                                if t.get("tag") == "text":
                                    name = t.get("text", "").strip()
                                    if name:
                                        credits["writers"].append({
                                            "name": name,
                                            "lemmaId": None,
                                            "link": None
                                        })
                
                elif key == "starring":
                    for d in data_list:
                        if d.get("dataType") == "lemma":
                            name = d.get("value", {}).get("title", "")
                            lemma_id = d.get("value", {}).get("id", "")
                            if name:
                                credits["cast"].append({
                                    "name": name,
                                    "lemmaId": str(lemma_id),
                                    "link": f"/item/{name}/{lemma_id}" if lemma_id else None
                                })
                        elif d.get("dataType") == "text":
                            text_list = d.get("text", [])
                            for t in text_list:
                                if t.get("tag") == "text":
                                    name = t.get("text", "").strip()
                                    if name:
                                        credits["cast"].append({
                                            "name": name,
                                            "lemmaId": None,
                                            "link": None
                                        })
                
                elif key == "producer":
                    for d in data_list:
                        if d.get("dataType") == "lemma":
                            name = d.get("value", {}).get("title", "")
                            lemma_id = d.get("value", {}).get("id", "")
                            if name:
                                credits["producers"].append({
                                    "name": name,
                                    "lemmaId": str(lemma_id) if lemma_id else None,
                                    "link": f"/item/{name}/{lemma_id}" if lemma_id else None
                                })
        
        # 如果 content 为空，尝试从 left/right 提取
        if not credits["directors"] and not credits["writers"] and not credits["cast"]:
            left_items = card.get("left") or []
            right_items = card.get("right") or []
            
            # 从 left 提取导演、编剧
            for item in left_items:
                key = item.get("key", "")
                data_list = item.get("data", [])
                
                if key == "director":
                    for d in data_list:
                        if d.get("dataType") == "lemma":
                            name = d.get("value", {}).get("title", "")
                            lemma_id = d.get("value", {}).get("id", "")
                            if name:
                                credits["directors"].append({
                                    "name": name,
                                    "lemmaId": str(lemma_id),
                                    "link": f"/item/{name}/{lemma_id}" if lemma_id else None
                                })
                        elif d.get("dataType") == "text":
                            text_list = d.get("text", [])
                            for t in text_list:
                                if t.get("tag") == "text":
                                    name = t.get("text", "").strip()
                                    if name:
                                        credits["directors"].append({
                                            "name": name,
                                            "lemmaId": None,
                                            "link": None
                                        })
                
                elif key == "scriptwriter":
                    for d in data_list:
                        if d.get("dataType") == "lemma":
                            name = d.get("value", {}).get("title", "")
                            lemma_id = d.get("value", {}).get("id", "")
                            if name:
                                credits["writers"].append({
                                    "name": name,
                                    "lemmaId": str(lemma_id),
                                    "link": f"/item/{name}/{lemma_id}" if lemma_id else None
                                })
                        elif d.get("dataType") == "text":
                            text_list = d.get("text", [])
                            for t in text_list:
                                if t.get("tag") == "text":
                                    name = t.get("text", "").strip()
                                    if name:
                                        credits["writers"].append({
                                            "name": name,
                                            "lemmaId": None,
                                            "link": None
                                        })
            
            # 从 right 提取主演、制片人
            for item in right_items:
                key = item.get("key", "")
                data_list = item.get("data", [])
                
                if key == "starring":
                    for d in data_list:
                        if d.get("dataType") == "lemma":
                            name = d.get("value", {}).get("title", "")
                            lemma_id = d.get("value", {}).get("id", "")
                            if name:
                                credits["cast"].append({
                                    "name": name,
                                    "lemmaId": str(lemma_id),
                                    "link": f"/item/{name}/{lemma_id}" if lemma_id else None
                                })
                        elif d.get("dataType") == "text":
                            text_list = d.get("text", [])
                            for t in text_list:
                                if t.get("tag") == "text":
                                    name = t.get("text", "").strip()
                                    if name:
                                        credits["cast"].append({
                                            "name": name,
                                            "lemmaId": None,
                                            "link": None
                                        })
                
                elif key == "producer":
                    for d in data_list:
                        if d.get("dataType") == "lemma":
                            name = d.get("value", {}).get("title", "")
                            lemma_id = d.get("value", {}).get("id", "")
                            if name:
                                credits["producers"].append({
                                    "name": name,
                                    "lemmaId": str(lemma_id) if lemma_id else None,
                                    "link": f"/item/{name}/{lemma_id}" if lemma_id else None
                                })
        
        return credits
    
    def _extract_major_actors_avatars(self, page_data: Dict) -> Dict[str, str]:
        """
        从 PAGE_DATA.featureInfo 提取主要演员头像
        
        Args:
            page_data: PAGE_DATA 字典
            
        Returns:
            {演员名: 头像URL} 字典
        """
        avatars = {}
        
        feature_info = page_data.get("modules", {}).get("featureInfo", {})
        major_actors = feature_info.get("data", {}).get("majorActors", [])
        
        for actor in major_actors:
            name = actor.get("title", "")
            pic_src = actor.get("pic", {}).get("src", "")
            if name and pic_src:
                # 构建完整 URL
                avatar_url = f"https://bkimg.cdn.bcebos.com/pic/{pic_src}"
                avatars[name] = avatar_url
        
        return avatars
    
    def _extract_cast_from_role_module(self, soup: BeautifulSoup) -> List[Dict]:
        """
        从 role 模块提取演员数据（data-module-type="role"）
        
        Args:
            soup: BeautifulSoup 对象
            
        Returns:
            演员列表
        """
        cast = []
        
        role_module = soup.find(attrs={'data-module-type': 'role'})
        if not role_module:
            return cast
        
        role_items = role_module.find_all(class_='roleItem_uMbCs')
        
        for item in role_items:
            try:
                # 角色名
                role_name_elem = item.find(class_='roleName_B15Qi')
                role_name = ""
                if role_name_elem:
                    text_span = role_name_elem.find('span', attrs={'data-text': 'true'})
                    if text_span:
                        role_name = text_span.get_text(strip=True)
                
                # 演员
                actor_elem = item.find(class_='roleActor_auylA')
                actor_name = ""
                actor_link = ""
                
                if actor_elem:
                    actor_link_elem = actor_elem.find('a')
                    if actor_link_elem:
                        actor_name = actor_link_elem.get_text(strip=True)
                        actor_link = actor_link_elem.get('href', '')
                
                if actor_name:
                    cast.append({
                        "name": actor_name,
                        "character": role_name,
                        "characterEn": None,
                        "lemmaId": self._extract_lemma_id(actor_link),
                        "link": actor_link if actor_link else None
                    })
                    
            except Exception:
                continue
        
        Logger.info(f"从 role 模块提取演员 {len(cast)} 人")
        return cast
    
    def _extract_lemma_id(self, link: str) -> Optional[str]:
        """从链接中提取 lemma ID"""
        if not link:
            return None
        
        match = re.search(r'/item/[^/]+/(\d+)', link)
        if match:
            return match.group(1)
        return None
    
    def _extract_cast_from_html(self, soup: BeautifulSoup) -> List[Dict]:
        """
        从 HTML actor 模块提取完整演员表
        
        Args:
            soup: BeautifulSoup 对象
            
        Returns:
            演员列表
        """
        cast = []
        
        actor_items = soup.select('.actorItem_EQB0t')
        
        for item in actor_items:
            try:
                # 姓名
                name_link = item.select_one('.info_aRpVI dt a.innerLink_k6w5Y')
                name = name_link.text.strip() if name_link else ""
                
                if not name:
                    continue
                
                # 角色名（第二个 span）
                spans = item.select('.info_aRpVI dt .text_hjH6n')
                character = ""
                character_en = ""
                
                if len(spans) > 1:
                    role_span = spans[1]
                    role_link = role_span.select_one('a.innerLink_k6w5Y')
                    if role_link:
                        character = role_link.text.strip()
                    else:
                        role_text = role_span.text.strip()
                        # 分离中英文
                        character, character_en = self._split_character_name(role_text)
                
                # 备注
                note_elems = item.select('.info_aRpVI dd')
                note = ""
                for dd in note_elems:
                    em = dd.select_one('em')
                    if em and '备注' in em.text:
                        span = dd.select_one('span')
                        if span:
                            note = span.text.strip()
                        break
                
                cast.append({
                    "name": name,
                    "character": character,
                    "characterEn": character_en,
                    "note": note
                })
                
            except Exception:
                continue
        
        return cast
    
    def _extract_credits_json(self, html_content: str) -> Optional[Dict[str, Any]]:
        """
        从百度百科页面提取演职员 JSON 数据
        
        百度百科页面内嵌 JSON 数据，包含完整的演职员信息：
        - director: 导演
        - scriptwriter: 编剧
        - starring: 主演
        - actor: 演员表（含角色、头像、备注）
        - producer: 制片人
        
        Args:
            html_content: HTML 内容
            
        Returns:
            演职员数据字典
        """
        credits = {
            "directors": [],
            "writers": [],
            "cast": [],
            "producers": []
        }
        
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            
            # 方法1: 查找 data-module-value 属性
            module_elements = soup.find_all(attrs={"data-module-value": True})
            for elem in module_elements:
                try:
                    module_value = elem.get("data-module-value", "")
                    if module_value:
                        data = json.loads(module_value)
                        self._parse_module_data(data, credits)
                except json.JSONDecodeError:
                    continue
            
            # 方法2: 查找页面中的 JSON 数据（在 script 标签或全局变量中）
            script_tags = soup.find_all("script")
            for script in script_tags:
                script_text = script.string or ""
                if not script_text:
                    continue
                
                # 查找包含演职员数据的 JSON
                if "director" in script_text or "actor" in script_text or "starring" in script_text:
                    try:
                        # 尝试提取 JSON 对象
                        json_match = re.search(r'\{[^{}]*"director"[^{}]*\}', script_text)
                        if json_match:
                            data = json.loads(json_match.group())
                            self._parse_module_data(data, credits)
                    except json.JSONDecodeError:
                        continue
            
            # 方法3: 从 HTML 结构中提取（备用方案）
            if not credits["cast"]:
                self._extract_credits_from_html(soup, credits)
            
            return credits if any(credits.values()) else None
            
        except Exception as e:
            Logger.warning(f"百度百科演职员 JSON 提取失败: {e}")
            return None
    
    def _parse_module_data(self, data: Dict, credits: Dict):
        """
        解析模块数据
        
        Args:
            data: JSON 数据
            credits: 输出的演职员数据
        """
        # 导演
        if "director" in data:
            director_data = data["director"]
            if isinstance(director_data, dict) and "data" in director_data:
                for item in director_data["data"]:
                    if item.get("dataType") == "lemma":
                        name = item.get("value", {}).get("title", "")
                        lemma_id = item.get("value", {}).get("id", "")
                        if name:
                            credits["directors"].append({
                                "name": name,
                                "lemmaId": lemma_id,
                                "link": f"/item/{name}/{lemma_id}" if lemma_id else None
                            })
        
        # 编剧
        if "scriptwriter" in data:
            writer_data = data["scriptwriter"]
            if isinstance(writer_data, dict) and "data" in writer_data:
                for item in writer_data["data"]:
                    if item.get("dataType") == "lemma":
                        name = item.get("value", {}).get("title", "")
                        lemma_id = item.get("value", {}).get("id", "")
                        if name:
                            credits["writers"].append({
                                "name": name,
                                "lemmaId": lemma_id,
                                "link": f"/item/{name}/{lemma_id}" if lemma_id else None
                            })
        
        # 主演
        if "starring" in data:
            starring_data = data["starring"]
            if isinstance(starring_data, dict) and "data" in starring_data:
                for item in starring_data["data"]:
                    if item.get("dataType") == "lemma":
                        name = item.get("value", {}).get("title", "")
                        lemma_id = item.get("value", {}).get("id", "")
                        if name:
                            credits["cast"].append({
                                "name": name,
                                "lemmaId": lemma_id,
                                "link": f"/item/{name}/{lemma_id}" if lemma_id else None
                            })
        
        # 演员表（详细）
        if "actor" in data:
            actor_data = data.get("actor", {})
            actor_img = data.get("actorImg", {})
            actor_role = data.get("actorRole", [])
            actor_note = data.get("actorNote", {})
            
            if actor_data.get("dataType") == "lemma":
                name = actor_data.get("value", {}).get("title", "")
                lemma_id = actor_data.get("value", {}).get("id", "")
                
                # 头像
                avatar = None
                if actor_img.get("dataType") == "image":
                    avatar = actor_img.get("value", {}).get("url", "")
                
                # 角色
                character = None
                character_en = None
                if actor_role and isinstance(actor_role, list):
                    for role_item in actor_role:
                        if role_item.get("dataType") == "lemma":
                            role_text = role_item.get("value", {}).get("title", "")
                            if role_text:
                                # 尝试分离中英文角色名
                                character, character_en = self._split_character_name(role_text)
                
                # 备注
                note = None
                if actor_note.get("dataType") == "text":
                    note = actor_note.get("text", [{}])[0].get("text", "")
                
                if name:
                    # 检查是否已存在，避免重复
                    existing = [c for c in credits["cast"] if c.get("name") == name]
                    if existing:
                        # 更新现有记录
                        idx = credits["cast"].index(existing[0])
                        credits["cast"][idx].update({
                            "character": character,
                            "characterEn": character_en,
                            "avatar": avatar,
                            "note": note
                        })
                    else:
                        credits["cast"].append({
                            "name": name,
                            "lemmaId": lemma_id,
                            "character": character,
                            "characterEn": character_en,
                            "avatar": avatar,
                            "note": note,
                            "link": f"/item/{name}/{lemma_id}" if lemma_id else None
                        })
        
        # 制片人
        if "producer" in data:
            producer_data = data["producer"]
            if isinstance(producer_data, dict) and "data" in producer_data:
                for item in producer_data["data"]:
                    if item.get("dataType") == "lemma":
                        name = item.get("value", {}).get("title", "")
                        lemma_id = item.get("value", {}).get("id", "")
                        if name:
                            credits["producers"].append({
                                "name": name,
                                "lemmaId": lemma_id,
                                "link": f"/item/{name}/{lemma_id}" if lemma_id else None
                            })
    
    def _split_character_name(self, role_text: str) -> tuple:
        """
        分离角色名的中英文
        
        示例: "Ellis Boyd \"Red\" Redding（埃利斯·\"瑞德\"·雷丁）"
        返回: ("埃利斯·\"瑞德\"·雷丁", "Ellis Boyd \"Red\" Redding")
        
        Args:
            role_text: 角色名文本
            
        Returns:
            (中文名, 英文名)
        """
        # 查找括号内的中文
        match = re.search(r'([^(]+)\（([^）]+)\）', role_text)
        if match:
            return (match.group(2), match.group(1))
        
        # 如果没有括号，判断是否是纯中文或纯英文
        if re.match(r'^[\u4e00-\u9fa5]+', role_text):
            return (role_text, None)
        elif re.match(r'^[A-Za-z]+', role_text):
            return (None, role_text)
        
        return (role_text, None)
    
    def _extract_credits_from_html(self, soup: BeautifulSoup, credits: Dict):
        """
        从 HTML 结构中提取演职员数据（备用方案）
        
        Args:
            soup: BeautifulSoup 对象
            credits: 输出的演职员数据
        """
        # 演员模块
        actor_modules = soup.find_all(attrs={"data-module-type": "actor"})
        for module in actor_modules:
            actor_items = module.select(".actorItem_EQB0t, .actorItem_Adj6G")
            for item in actor_items:
                try:
                    # 姓名
                    character = None
                    name_elem = item.select_one(".actorName_LnBCT a, .info_aRpVI dt a.innerLink_k6w5Y")
                    name = name_elem.text.strip() if name_elem else ""
                    
                    # 头像
                    avatar_elem = item.select_one(".actorImg_d70h2 img, .coverPic_B5ywr img")
                    avatar = avatar_elem.get("src") if avatar_elem else None
                    
                    # 角色名
                    role_elem = item.select_one(".info_aRpVI dt")
                    if role_elem:
                        role_text = role_elem.text.strip()
                        # 解析 "姓名 饰 角色名"
                        if "饰" in role_text:
                            parts = role_text.split("饰")
                            character = parts[1].strip() if len(parts) > 1 else None
                    
                    # 备注
                    note_elem = item.select_one(".info_aRpVI dd")
                    note = None
                    if note_elem:
                        note_text = note_elem.text.strip()
                        if "备注" in note_text:
                            note = note_text.replace("备注", "").strip()
                    
                    if name:
                        credits["cast"].append({
                            "name": name,
                            "avatar": avatar,
                            "character": character,
                            "note": note
                        })
                except Exception:
                    continue
    
    async def crawl(self, title: str) -> Dict[str, Any]:
        """
        完整爬取流程
        
        Args:
            title: 电影标题
            
        Returns:
            完整数据
        """
        result = {
            "title": title,
            "source": "baike"
        }
        
        url = await self.search(title)
        if url:
            result = await self.get_detail(url)
            
        return result
