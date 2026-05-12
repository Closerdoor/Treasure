# -*- coding: utf-8 -*-
"""
下载缺失的头像文件

从 TMDB API 获取人物头像并下载
"""
import os
import sys

if sys.platform == 'win32':
    os.environ['PYTHONUTF8'] = '1'

import asyncio
import aiohttp
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Set

import config
from utils import Logger


class AvatarDownloader:
    """头像下载器"""
    
    def __init__(self):
        self.db_path = Path(__file__).parent.parent.parent / ".local" / "treasure.db"
        self.avatar_dir = Path(__file__).parent.parent.parent / ".local" / "assets" / "people"
        self.conn = None
        
        self.tmdb_api_key = config.TMDB_API_KEY
        self.tmdb_base_url = "https://api.themoviedb.org/3"
        self.tmdb_image_url = "https://image.tmdb.org/t/p/original"
        self.proxy = config.PROXY_URL if config.PROXY_ENABLED else None
        
        # 速率控制
        self.semaphore = asyncio.Semaphore(10)
        self.last_call = 0
        self.min_interval = 0.1
        
        # 统计
        self.stats = {
            'total_missing': 0,
            'downloaded': 0,
            'no_profile': 0,
            'failed': 0,
        }
    
    def connect(self):
        if not self.conn:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
    
    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def get_existing_avatars(self) -> Set[str]:
        """获取已存在的头像文件"""
        if not self.avatar_dir.exists():
            self.avatar_dir.mkdir(parents=True, exist_ok=True)
            return set()
        
        return set(f.name for f in self.avatar_dir.iterdir() 
                   if f.suffix in ['.jpg', '.webp'])
    
    def get_missing_avatars(self) -> List[Dict]:
        """获取有 TMDB ID 但无头像文件的人物"""
        self.connect()
        
        existing = self.get_existing_avatars()
        
        cursor = self.conn.execute("""
            SELECT id, person_id, name, name_en, source_ids
            FROM person
            WHERE source_ids IS NOT NULL AND source_ids LIKE ?
        """, ('%tmdb%',))
        
        missing = []
        for row in cursor.fetchall():
            person = dict(row)
            source_ids = json.loads(person['source_ids'] or '{}')
            tmdb_id = source_ids.get('tmdb')
            
            if tmdb_id and tmdb_id != 'NO_MATCH':
                expected_file = f"tmdb-{tmdb_id}-avatar.jpg"
                if expected_file not in existing:
                    missing.append({
                        'id': person['id'],
                        'name': person['name'],
                        'tmdb_id': tmdb_id,
                    })
        
        return missing
    
    async def download_avatar(self, tmdb_id: str, person_name: str) -> bool:
        """下载单个头像"""
        async with self.semaphore:
            # 先获取人物详情
            url = f"{self.tmdb_base_url}/person/{tmdb_id}"
            params = {'api_key': self.tmdb_api_key}
            
            try:
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(connector=connector) as session:
                    # 获取人物信息
                    async with session.get(url, params=params, proxy=self.proxy, 
                                          timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status != 200:
                            return False
                        
                        data = await response.json()
                        profile_path = data.get('profile_path')
                        
                        if not profile_path:
                            self.stats['no_profile'] += 1
                            return False
                        
                        # 下载头像
                        image_url = f"{self.tmdb_image_url}{profile_path}"
                        async with session.get(image_url, proxy=self.proxy,
                                              timeout=aiohttp.ClientTimeout(total=60)) as img_response:
                            if img_response.status == 200:
                                content = await img_response.read()
                                
                                # 保存文件
                                output_file = self.avatar_dir / f"tmdb-{tmdb_id}-avatar.jpg"
                                with open(output_file, 'wb') as f:
                                    f.write(content)
                                
                                self.stats['downloaded'] += 1
                                return True
                            else:
                                self.stats['failed'] += 1
                                return False
            
            except Exception as e:
                self.stats['failed'] += 1
                return False
    
    async def process_batch(self, persons: List[Dict], start: int, batch_size: int):
        """处理一批人物"""
        end = min(start + batch_size, len(persons))
        
        for i in range(start, end):
            person = persons[i]
            Logger.info(f"[{i+1}/{len(persons)}] {person['name']} (tmdb:{person['tmdb_id']})")
            
            success = await self.download_avatar(person['tmdb_id'], person['name'])
            
            if success:
                Logger.success(f"  下载成功")
            else:
                Logger.warning(f"  下载失败或无头像")
            
            # 进度报告
            if (i + 1) % 100 == 0:
                Logger.info(f"进度: 已下载 {self.stats['downloaded']}, 无头像 {self.stats['no_profile']}, 失败 {self.stats['failed']}")
    
    async def run(self):
        """执行下载"""
        Logger.info("=== 开始下载缺失头像 ===")
        
        # 获取缺失列表
        missing = self.get_missing_avatars()
        self.stats['total_missing'] = len(missing)
        
        Logger.info(f"缺失头像: {len(missing)} 人")
        
        if not missing:
            Logger.info("无缺失头像")
            return
        
        # 分批下载
        batch_size = 500
        for start in range(0, len(missing), batch_size):
            await self.process_batch(missing, start, batch_size)
            
            # 批次间休息
            if start + batch_size < len(missing):
                Logger.info("批次休息 5 秒...")
                await asyncio.sleep(5)
        
        # 输出统计
        Logger.info("=== 下载完成 ===")
        Logger.info(f"总缺失: {self.stats['total_missing']}")
        Logger.info(f"已下载: {self.stats['downloaded']}")
        Logger.info(f"无头像: {self.stats['no_profile']}")
        Logger.info(f"失败: {self.stats['failed']}")
        
        self.close()


async def main():
    downloader = AvatarDownloader()
    await downloader.run()


if __name__ == '__main__':
    asyncio.run(main())