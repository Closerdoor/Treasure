# -*- coding: utf-8 -*-
"""
百度百科爬虫
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
        获取词条内容
        
        Args:
            url: 词条 URL
            
        Returns:
            词条数据
        """
        Logger.info(f"正在获取百度百科内容: {url}")
        
        result = {
            "url": url,
            "source": "baike"
        }
        
        try:
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # 词条名（多种选择器尝试）
            title_elem = soup.select_one("h1") or soup.select_one(".lemmaTitle") or soup.select_one(".lemma-title")
            title_text = title_elem.text.strip() if title_elem else ""
            # 如果标题为空，从 URL 提取
            if not title_text:
                match = re.search(r"/item/([^/]+)", url)
                if match:
                    from urllib.parse import unquote
                    title_text = unquote(match.group(1))
            result["title"] = title_text
            
            # 词条 ID（从 URL 提取，URL 解码）
            match = re.search(r"/item/([^/]+)", url)
            if match:
                from urllib.parse import unquote
                baike_id = unquote(match.group(1))
                result["baike_id"] = baike_id
            
            # 基本信息（右侧信息框）
            info_box = soup.select_one(".basicInfo-block") or soup.select_one(".lemma-summary")
            if info_box:
                info_items = info_box.select(".basicInfo-block")
                for item in info_items:
                    try:
                        name_elem = item.select_one(".basicInfo-item.name")
                        value_elem = item.select_one(".basicInfo-item.value")
                        if name_elem and value_elem:
                            name = name_elem.text.strip().rstrip("：:")
                            value = value_elem.text.strip()
                            result[name] = value
                    except:
                        continue
            
            # 摘要
            summary_elem = soup.select_one(".lemma-summary") or soup.select_one(".para")
            result["summary"] = summary_elem.text.strip() if summary_elem else ""
            
            Logger.success(f"百度百科内容获取完成")
            
        except Exception as e:
            Logger.error(f"百度百科内容获取失败: {e}")
            
        return result
        
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