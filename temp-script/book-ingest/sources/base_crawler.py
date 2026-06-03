# -*- coding: utf-8 -*-
"""
公共浏览器管理基类

每个数据源爬虫继承此基类，获得独立的浏览器实例管理能力。
核心原则：每个数据源一个浏览器上下文，一次性完成全部信息获取。
"""
import asyncio
import json
import random
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

import config
from utils import Logger


class BaseCrawler:
    """公共浏览器管理基类"""

    def __init__(self, source_name: str = "unknown"):
        self.source_name = source_name
        self.playwright: Optional[object] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def init_browser(self) -> Page:
        """启动浏览器并创建独立上下文，返回 Page"""
        Logger.info(f"[{self.source_name}] 正在启动浏览器...")

        self.playwright = await async_playwright().start()

        launch_options = {
            "headless": config.HEADLESS,
            "slow_mo": config.SLOW_MO,
        }

        if config.USE_CHROME and hasattr(config, "CHROME_PATH"):
            launch_options["executable_path"] = config.CHROME_PATH

        try:
            self.browser = await self.playwright.chromium.launch(**launch_options)
        except Exception as e:
            Logger.error(f"[{self.source_name}] 浏览器启动失败: {e}")
            raise

        user_agent = random.choice(config.USER_AGENTS)

        context_options = {
            "user_agent": user_agent,
            "viewport": {"width": 1920, "height": 1080},
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
        }

        if config.PROXY_ENABLED and config.PROXY_URL:
            context_options["proxy"] = {"server": config.PROXY_URL}
            Logger.info(f"[{self.source_name}] 使用代理: {config.PROXY_URL}")

        self.context = await self.browser.new_context(**context_options)

        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
            window.chrome = { runtime: {} };
        """)

        self.page = await self.context.new_page()
        Logger.info(f"[{self.source_name}] 浏览器已启动")
        return self.page

    async def load_cookies(self, cookie_file: Path) -> bool:
        """加载指定 Cookie 文件"""
        if cookie_file.exists():
            try:
                cookies = json.loads(cookie_file.read_text(encoding="utf-8"))
                same_site_map = {
                    "strict": "Strict",
                    "lax": "Lax",
                    "none": "None",
                    "no_restriction": "None",
                    "unspecified": "Lax",
                }
                for cookie in cookies:
                    same_site = cookie.get("sameSite")
                    if isinstance(same_site, str):
                        cookie["sameSite"] = same_site_map.get(same_site.lower(), same_site)
                await self.context.add_cookies(cookies)
                Logger.info(f"[{self.source_name}] 已加载 Cookie: {cookie_file}")
                return True
            except Exception as e:
                Logger.warning(f"[{self.source_name}] Cookie 加载失败: {e}")
                return False
        return False

    async def save_cookies(self, cookie_file: Path):
        """保存当前 Cookie 到指定文件"""
        if not self.context:
            return
        cookies = await self.context.cookies()
        cookie_file.parent.mkdir(parents=True, exist_ok=True)
        cookie_file.write_text(
            json.dumps(cookies, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        Logger.info(f"[{self.source_name}] Cookie 已保存: {cookie_file}")

    async def close(self):
        """关闭浏览器"""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            Logger.warning(f"[{self.source_name}] 关闭浏览器时出错: {e}")
        finally:
            self.playwright = None
            self.browser = None
            self.context = None
            self.page = None
        Logger.info(f"[{self.source_name}] 浏览器已关闭")

    async def goto_with_retry(
        self,
        url: str,
        max_retries: int = 3,
        timeout: int = 60000,
        wait_until: str = "domcontentloaded",
        delay_range: tuple = (2.0, 5.0),
    ) -> str:
        """带重试的页面访问"""
        retry_intervals = [5, 10, 30]

        for attempt in range(max_retries):
            try:
                Logger.info(
                    f"[{self.source_name}] 访问: {url} (尝试 {attempt + 1}/{max_retries})"
                )
                await self.page.goto(url, timeout=timeout, wait_until=wait_until)
                await asyncio.sleep(random.uniform(*delay_range))
                return self.page.url
            except Exception as e:
                Logger.error(
                    f"[{self.source_name}] 访问失败 (尝试 {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    wait_time = retry_intervals[attempt]
                    Logger.info(f"[{self.source_name}] 等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                else:
                    raise

    async def random_delay(self, min_delay: float = None, max_delay: float = None):
        """随机延迟"""
        min_d = min_delay or config.MIN_DELAY
        max_d = max_delay or config.MAX_DELAY
        await asyncio.sleep(random.uniform(min_d, max_d))

    def save_raw_data(self, book_id: str, source: str, data: dict):
        """保存原始数据到 data/raw/{book_id}/{source}.json"""
        raw_dir = Path(config.OUTPUT_DIR) / "raw" / book_id
        raw_dir.mkdir(parents=True, exist_ok=True)

        filepath = raw_dir / f"{source}.json"
        filepath.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        Logger.info(f"[{self.source_name}] 已保存原始数据: {filepath}")
