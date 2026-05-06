# -*- coding: utf-8 -*-
"""
Wikipedia 爬虫
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
            title: 电影标题（中文）
            original_title: 电影原名（英文）
            
        Returns:
            词条 URL 或 None
        """
        Logger.info(f"正在搜索 Wikipedia: {title}")
        
        # 先尝试用中文名搜索
        encoded_title = quote(title)
        url = f"{self.base_url}/wiki/{encoded_title}"
        
        try:
            await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
            
            # 检查是否跳转到搜索页面
            current_url = self.page.url
            if "search" in current_url or "Special:" in current_url:
                # 在搜索结果中查找
                content = await self.page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # 查找第一个搜索结果
                first_result = soup.select_one(".mw-search-result-heading a")
                if first_result:
                    href = first_result.get("href", "")
                    if href:
                        url = f"{self.base_url}{href}" if href.startswith("/") else href
                        await self.page.goto(url, timeout=30000, wait_until="domcontentloaded")
                        await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))
                else:
                    Logger.warning(f"Wikipedia 未找到词条: {title}")
                    return None
            
            Logger.success(f"找到 Wikipedia 词条: {url}")
            return url
            
        except Exception as e:
            Logger.error(f"Wikipedia 搜索失败: {e}")
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
            # 去除"[编辑]"等后缀
            title_text = re.sub(r'\[编辑\]$', '', title_text)
            result["title"] = title_text
            
            # 词条 ID（从 URL 提取）
            match = re.search(r"/wiki/(.+)$", url)
            if match:
                # URL 解码
                from urllib.parse import unquote
                wiki_id = unquote(match.group(1))
                result["wikipedia_id"] = wiki_id
            
            # 摘要（第一段）
            first_para = soup.select_one("#mw-content-text p")
            result["summary"] = first_para.text.strip() if first_para else ""
            
            # 剧情详解（查找"剧情"段落）
            plot_content = self._extract_plot_section(soup)
            if plot_content:
                result["plot"] = plot_content
            
            # 信息框
            infobox = soup.select_one(".infobox") or soup.select_one(".vevent")
            if infobox:
                rows = infobox.select("tr")
                for row in rows:
                    try:
                        th = row.select_one("th")
                        td = row.select_one("td")
                        if th and td:
                            key = th.text.strip()
                            value = td.text.strip()
                            result[key] = value
                    except:
                        continue
            
            # 获奖（查找获奖段落）
            awards = []
            award_heading = soup.find(string=re.compile("获奖|奖项|荣誉"))
            if award_heading:
                award_section = award_heading.find_parent(["h2", "h3"])
                if award_section:
                    next_elem = award_section.find_next_sibling()
                    while next_elem and next_elem.name not in ["h2", "h3"]:
                        if next_elem.name == "ul":
                            for li in next_elem.select("li"):
                                awards.append(li.text.strip())
                        next_elem = next_elem.find_next_sibling()
            result["awards"] = awards
            
            # 名言名句（查找引言段落）
            quotes = []
            quote_elems = soup.select("blockquote")
            for quote_elem in quote_elems:
                quote_text = quote_elem.text.strip()
                if quote_text:
                    quotes.append({
                        "text": quote_text,
                        "source": "wikipedia"
                    })
            result["quotes"] = quotes
            
            Logger.success(f"Wikipedia 内容获取完成")
            
        except Exception as e:
            Logger.error(f"Wikipedia 内容获取失败: {e}")
            
        return result
    
    def _extract_plot_section(self, soup: BeautifulSoup) -> str:
        """
        提取剧情段落内容
        
        Args:
            soup: BeautifulSoup 对象
            
        Returns:
            剧情内容
        """
        # 查找"剧情"标题
        plot_heading = None
        for heading in soup.find_all(["h2", "h3"]):
            heading_text = heading.text.strip()
            # 匹配"剧情"、"剧情简介"、"故事情节"等
            if re.search(r'剧情|故事|情节', heading_text):
                plot_heading = heading
                break
        
        if not plot_heading:
            return ""
        
        # 找到剧情标题后，查找内容容器
        # Wikipedia 的结构：标题在 h2/h3 中，内容在后续的 div 或直接在父容器中
        
        # 方法1：查找标题的父容器，然后找后续段落
        parent = plot_heading.parent
        if not parent:
            return ""
        
        # 查找内容区域（mw-content-text）
        content_div = soup.select_one("#mw-content-text")
        if not content_div:
            content_div = soup.select_one(".mw-parser-output")
        
        if not content_div:
            return ""
        
        # 收集剧情段落
        paragraphs = []
        found_heading = False
        
        for elem in content_div.descendants:
            if elem.name in ["h2", "h3"]:
                if elem == plot_heading:
                    found_heading = True
                    continue
                elif found_heading:
                    # 遇到下一个标题，停止
                    break
            
            if found_heading and elem.name == "p":
                text = elem.text.strip()
                if text and not text.startswith("目录"):
                    paragraphs.append(text)
        
        if not paragraphs:
            return ""
        
        # 合并所有段落
        plot_content = "\n\n".join(paragraphs)
        return plot_content
        
    async def crawl(self, title: str, original_title: str = "") -> Dict[str, Any]:
        """
        完整爬取流程
        
        Args:
            title: 电影标题（中文）
            original_title: 电影原名（英文）
            
        Returns:
            完整数据
        """
        result = {
            "title": title,
            "source": "wikipedia"
        }
        
        url = await self.search(title, original_title)
        if url:
            result = await self.get_detail(url)
            
        return result