# -*- coding: utf-8 -*-
"""
登录辅助脚本
帮助用户完成网站登录并保存 Cookie
"""
import asyncio
import json
import sys
import os

if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright

import config
from utils import Logger


COOKIE_DIR = Path(__file__).parent.parent / "data" / "cookies"
LOGIN_TIMEOUT = 120  # 登录超时时间（秒）


async def login_dangdang():
    """当当网登录辅助"""
    Logger.info("=" * 60)
    Logger.info("当当网登录辅助")
    Logger.info("=" * 60)
    
    cookie_file = COOKIE_DIR / "dangdang.json"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            proxy={"server": config.PROXY_URL} if config.PROXY_ENABLED else None
        )
        
        context = await browser.new_context()
        page = await context.new_page()
        
        Logger.info("正在打开当当网...")
        await page.goto("https://www.dangdang.com", timeout=30000)
        
        Logger.info("")
        Logger.info("请在浏览器中完成登录操作（2分钟内）：")
        Logger.info("1. 点击右上角'登录'")
        Logger.info("2. 使用手机号/微信/QQ登录")
        Logger.info("")
        
        # 等待登录完成（2分钟超时）
        try:
            await page.wait_for_selector(".login_info .name", timeout=LOGIN_TIMEOUT * 1000)
            Logger.success("检测到登录成功！")
        except Exception:
            Logger.warning("登录检测超时，继续保存当前 Cookie...")
        
        # 保存 Cookie
        cookies = await context.cookies()
        if cookies:
            cookie_file.parent.mkdir(parents=True, exist_ok=True)
            cookie_file.write_text(
                json.dumps(cookies, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            Logger.success(f"Cookie 已保存: {cookie_file}")
            Logger.success(f"共保存 {len(cookies)} 个 Cookie")
        else:
            Logger.warning("未获取到 Cookie")
        
        await browser.close()


async def login_qidian():
    """起点中文网登录辅助"""
    Logger.info("=" * 60)
    Logger.info("起点中文网登录辅助")
    Logger.info("=" * 60)
    
    cookie_file = COOKIE_DIR / "qidian.json"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            proxy={"server": config.PROXY_URL} if config.PROXY_ENABLED else None
        )
        
        context = await browser.new_context()
        page = await context.new_page()
        
        Logger.info("正在打开起点中文网...")
        await page.goto("https://www.qidian.com", timeout=30000)
        
        Logger.info("")
        Logger.info("请在浏览器中完成登录操作（2分钟内）：")
        Logger.info("1. 点击右上角'登录'")
        Logger.info("2. 使用QQ/微信登录")
        Logger.info("")
        
        # 等待登录完成（2分钟超时）
        try:
            await page.wait_for_selector(".user-avatar", timeout=LOGIN_TIMEOUT * 1000)
            Logger.success("检测到登录成功！")
        except Exception:
            Logger.warning("登录检测超时，继续保存当前 Cookie...")
        
        # 保存 Cookie
        cookies = await context.cookies()
        if cookies:
            cookie_file.parent.mkdir(parents=True, exist_ok=True)
            cookie_file.write_text(
                json.dumps(cookies, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            Logger.success(f"Cookie 已保存: {cookie_file}")
            Logger.success(f"共保存 {len(cookies)} 个 Cookie")
        else:
            Logger.warning("未获取到 Cookie")
        
        await browser.close()


async def login_all():
    """依次完成所有网站登录"""
    Logger.info("将依次引导你完成以下网站的登录：")
    Logger.info("1. 当当网")
    Logger.info("2. 起点")
    Logger.info("每个网站有 2 分钟登录时间")
    Logger.info("")
    
    await login_dangdang()
    Logger.info("")
    await login_qidian()
    
    Logger.info("=" * 60)
    Logger.success("所有网站登录完成！")
    Logger.info("=" * 60)


def main():
    """主入口"""
    if len(sys.argv) < 2:
        Logger.info("使用方法：")
        Logger.info("  python login_helper.py dangdang  - 当当网登录")
        Logger.info("  python login_helper.py qidian     - 起点")
        Logger.info("  python login_helper.py all        - 所有网站")
        return
    
    site = sys.argv[1].lower()
    
    if site == "dangdang":
        asyncio.run(login_dangdang())
    elif site == "qidian":
        asyncio.run(login_qidian())
    elif site == "all":
        asyncio.run(login_all())
    else:
        Logger.error(f"未知网站: {site}")


if __name__ == "__main__":
    main()