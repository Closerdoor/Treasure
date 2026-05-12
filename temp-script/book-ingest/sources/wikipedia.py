# -*- coding: utf-8 -*-
"""
Wikipedia 爬虫（书籍专用）
"""
import asyncio
import random
import re
from typing import Dict, Any, Optional, List
from urllib.parse import quote

from bs4 import BeautifulSoup
from playwright.async_api import Page

import config
from utils import Logger


class WikipediaCrawler:
    """Wikipedia 爬虫"""
    
    def __init__(self, page: Page):
        self.page = page
        self.base_url = config.WIKIPEDIA_BASE_URL
        
    async def search(self, title: str, original_title: str = "") -> Optional[str]:
        """
        搜索词条
        
        Args:
            title: 书名（中文）
            original_title: 书原名（外文）
            
        Returns:
            词条 URL 或 None
        """
        Logger.info(f"正在搜索 Wikipedia: {title}")
        
        search_strategies = []
        
        # 策略1: 访问"标题_(小说)"（优先，避免歧义）
        search_strategies.append(f"{self.base_url}/wiki/{quote(title)}_(小说)")
        
        # 策略2: 访问"标题_(书)"
        search_strategies.append(f"{self.base_url}/wiki/{quote(title)}_(书)")
        
        # 策略3: 直接访问中文标题
        search_strategies.append(f"{self.base_url}/wiki/{quote(title)}")
        
        # 策略4: 如果有原标题，尝试访问原标题
        if original_title:
            search_strategies.append(f"{self.base_url}/wiki/{quote(original_title)}")
        
        # 策略5: 搜索"标题 小说"
        search_strategies.append(f"{self.base_url}/w/index.php?search={quote(title + ' 小说')}&fulltext=1")
        
        for i, url in enumerate(search_strategies):
            try:
                Logger.info(f"尝试策略 {i+1}: {url}")
                await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
                await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                
                current_url = self.page.url
                content = await self.page.content()
                
                # 检查是否是搜索结果页面
                if "search" in current_url or "Special:" in current_url:
                    # 尝试从搜索结果中选择
                    soup = BeautifulSoup(content, "html.parser")
                    results = soup.select(".mw-search-result-heading a")
                    
                    if results:
                        # 优先选择包含"小说"或书名的结果
                        best_result = None
                        for result in results:
                            result_text = result.text.strip()
                            if title in result_text and any(kw in result_text for kw in ["小说", "书", "作品", "文学"]):
                                best_result = result
                                break
                        
                        if not best_result:
                            for result in results:
                                if title in result.text:
                                    best_result = result
                                    break
                        
                        if best_result:
                            href = best_result.get("href", "")
                            if href:
                                found_url = f"{self.base_url}{href}" if href.startswith("/") else href
                                Logger.success(f"找到 Wikipedia 词条: {found_url}")
                                return found_url
                    
                    continue
                
                # 检查是否是有效词条页面（不是"您可以新建这个页面"）
                if "您可以新建这个页面" in content or "新建这个页面" in content:
                    continue
                
                # 检查是否有词条内容
                soup = BeautifulSoup(content, "html.parser")
                content_div = soup.select_one("#mw-content-text")
                if content_div:
                    # 提取词条标题作为原标题
                    title_elem = soup.select_one("#firstHeading") or soup.select_one("h1")
                    if title_elem:
                        wiki_title = title_elem.text.strip()
                        wiki_title = re.sub(r'\[编辑\]$', '', wiki_title)
                        # 如果词条标题不是中文，可能是原文标题
                        if wiki_title != title and not re.match(r'^[\u4e00-\u9fa5]', wiki_title):
                            # 存储原标题供后续使用
                            self._original_title = wiki_title
                    
                    Logger.success(f"找到 Wikipedia 词条: {current_url}")
                    return current_url
                
            except Exception as e:
                Logger.warning(f"策略 {i+1} 失败: {e}")
                continue
        
        Logger.warning(f"Wikipedia 未找到词条: {title}")
        return None
            
    async def get_detail(self, url: str) -> Dict[str, Any]:
        """
        获取词条内容
        
        Args:
            url: 词条 URL
            
        Returns:
            词条数据
        """
        Logger.info(f"正在获取 Wikipedia 内容: {url}")
        
        result = {
            "url": url,
            "source": "wikipedia"
        }
        
        try:
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 词条名
            title_elem = soup.select_one("#firstHeading") or soup.select_one("h1")
            title_text = title_elem.text.strip() if title_elem else ""
            title_text = re.sub(r'\[编辑\]$', '', title_text)
            result["title"] = title_text
            
            # 如果词条标题不是中文，可能是原文标题
            if not re.match(r'^[\u4e00-\u9fa5]', title_text):
                result["title_original"] = title_text
            
            # 词条 ID
            wiki_id_match = re.search(r'/wiki/(.+)$', url)
            if wiki_id_match:
                result["wikipedia_id"] = wiki_id_match.group(1)
            
            # 简介（第一段有效内容）
            content_div = soup.select_one("#mw-content-text")
            if content_div:
                # 获取所有段落，跳过空段落和提示信息
                paragraphs = content_div.select("p")
                for para in paragraphs:
                    para_text = para.text.strip()
                    # 跳过空段落、提示信息、坐标等
                    if para_text and len(para_text) > 20:
                        # 跳过常见的提示信息
                        if not any(skip in para_text for skip in [
                            "可能出现此提示的其他原因",
                            "维基百科目前没有",
                            "您可以新建这个页面",
                            "本条目需要扩充",
                            "本条目需要精通"
                        ]):
                            result["summary"] = para_text
                            break
            
            # 获取信息框
            infobox = soup.select_one(".infobox")
            if infobox:
                rows = infobox.select("tr")
                info = {}
                for row in rows:
                    th = row.select_one("th")
                    td = row.select_one("td")
                    if th and td:
                        key = th.text.strip()
                        value = td.text.strip()
                        info[key] = value
                
                result["info"] = info
                
                # 提取原名（原文标题）
                if "原名" in info:
                    result["title_original"] = info.get("原名")
                elif "Original title" in info:
                    result["title_original"] = info.get("Original title")
                
                # 提取作者
                if "作者" in info or "Author" in info:
                    result["author"] = info.get("作者") or info.get("Author")
                
                # 提取国家
                if "国家" in info or "Country" in info:
                    result["country"] = info.get("国家") or info.get("Country")
                
                # 提取语言
                if "语言" in info or "Language" in info:
                    result["language"] = info.get("语言") or info.get("Language")
            
            # 获取获奖信息
            awards = []
            award_section = soup.find("span", {"id": re.compile(r"获奖|奖项|Awards", re.I)})
            if award_section:
                award_list = award_section.find_next("ul")
                if award_list:
                    for li in award_list.select("li")[:10]:
                        awards.append(li.text.strip())
            
            if awards:
                result["awards"] = awards
            
            # 获取经典语录
            quotes = []
            quote_section = soup.find("span", {"id": re.compile(r"名言|语录|Quotes", re.I)})
            if quote_section:
                quote_list = quote_section.find_next("ul")
                if quote_list:
                    for li in quote_list.select("li")[:10]:
                        quote_text = li.text.strip()
                        quotes.append({"text": quote_text, "source": title_text})
            
            if quotes:
                result["quotes"] = quotes
            
            Logger.success(f"Wikipedia 数据获取完成")
            
        except Exception as e:
            Logger.error(f"Wikipedia 解析失败: {e}")
            
        return result
