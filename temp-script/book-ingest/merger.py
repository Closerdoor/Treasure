# -*- coding: utf-8 -*-
"""
数据合并模块
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils import Logger, generate_book_id


class DataMerger:
    """数据合并器"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path(__file__).parent / "data"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.raw_dir = self.data_dir / "raw"
        self.staging_dir = self.data_dir / "staging"
        self.assets_dir = self.data_dir / "assets"
        
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
    
    def merge(self, book_id: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并各来源数据
        
        Args:
            book_id: 书籍 ID
            raw_data: 原始数据（各来源）
            
        Returns:
            合并后的数据
        """
        Logger.info(f"正在合并数据: {book_id}")
        
        result = {
            "id": book_id,
            "title": "",
            "titleOriginal": None,
            "otherTitles": None,
            "isbn": None,
            "year": None,
            "country": None,
            "language": None,
            "wordCount": None,
            "publisher": None,
            "summary": None,
            "quotes": None,
            "seriesId": None,
            "seriesOrder": None,
            "scores": None,
            "externalSource": None,
            "images": None,
            "reviews": [],
            "related": None,
            "status": "draft"
        }
        
        # 豆瓣数据（主源）
        douban = raw_data.get("douban", {})
        if douban:
            result["title"] = douban.get("title", "")
            result["titleOriginal"] = douban.get("title_original")
            result["year"] = douban.get("year")
            result["isbn"] = douban.get("isbn")
            result["publisher"] = douban.get("publisher")
            result["summary"] = douban.get("summary")
            
            # 作者
            authors = douban.get("authors", [])
            translators = douban.get("translators", [])
            result["_authors"] = authors
            result["_translators"] = translators
            
            # 标签
            tags = douban.get("tags", [])
            result["_tags"] = tags
            
            # 评分
            rating = douban.get("rating")
            if rating:
                result["scores"] = {"douban": float(rating)}
            
            # 封面
            cover_url = douban.get("main_cover_url")
            if cover_url:
                result["images"] = {
                    "cover": "cover-main.jpg",
                    "covers": [],
                    "assetDir": book_id
                }
            
            # 相关推荐
            recommendations = douban.get("recommendations", [])
            if recommendations:
                related = {"similar": [], "series": [], "sameAuthor": []}
                for rec in recommendations:
                    related["similar"].append({
                        "title": rec.get("title"),
                        "year": None,
                        "rating": float(rec.get("rating")) if rec.get("rating") and rec.get("rating").isdigit() else None,
                        "bookId": None
                    })
                result["related"] = related
            
            # 外部来源
            external = []
            if douban.get("douban_id"):
                external.append({
                    "name": "豆瓣",
                    "id": douban.get("douban_id"),
                    "link": f"https://book.douban.com/subject/{douban.get('douban_id')}/"
                })
            if douban.get("isbn"):
                external.append({
                    "name": "ISBN",
                    "id": douban.get("isbn"),
                    "link": None
                })
            result["externalSource"] = external if external else None
        
        # 如果没有豆瓣数据，从其他来源获取标题
        if not result.get("title"):
            # 优先从百度百科获取中文标题
            baike = raw_data.get("baike", {})
            if baike and baike.get("baike_title"):
                result["title"] = baike.get("baike_title")
            elif baike and baike.get("title"):
                result["title"] = baike.get("title")
            
            # 如果还没有，从 Wikipedia 获取
            if not result.get("title"):
                wiki = raw_data.get("wikipedia", {})
                if wiki and wiki.get("title"):
                    result["title"] = wiki.get("title")
            
            # 最后从 OpenLibrary 获取
            if not result.get("title"):
                ol = raw_data.get("openlibrary", {})
                if ol and ol.get("title"):
                    result["title"] = ol.get("title")
        
        # OpenLibrary 数据（补充）
        openlibrary = raw_data.get("openlibrary", {})
        if openlibrary:
            # 原名（优先级最低，因为通常是罗马化标题）
            # 且如果是中文，则不使用（中文书籍无外文名）
            if openlibrary.get("title") and not result.get("titleOriginal"):
                title_orig = openlibrary.get("title")
                if not re.match(r'^[\u4e00-\u9fa5]+$', title_orig):
                    result["titleOriginal"] = title_orig
            
            # 补充 ISBN
            if not result.get("isbn") and openlibrary.get("isbn"):
                result["isbn"] = openlibrary.get("isbn")
            
            # 补充简介
            if not result.get("summary") and openlibrary.get("description"):
                result["summary"] = openlibrary.get("description")
            
            # 补充年份（优先级最低）
            if not result.get("year") and openlibrary.get("first_publish_year"):
                result["year"] = openlibrary.get("first_publish_year")
            
            # 补充封面
            if openlibrary.get("cover_urls"):
                if not result.get("images"):
                    result["images"] = {
                        "cover": "cover-main.jpg",
                        "covers": [],
                        "assetDir": book_id
                    }
                result["images"]["covers"] = [f"cover-{i+2:03d}.jpg" for i in range(len(openlibrary.get("cover_urls", [])[:3]))]
            
            # 主题标签
            subjects = openlibrary.get("subjects", [])
            if subjects:
                result["_subjects"] = subjects
            
            # 外部来源
            if openlibrary.get("openlibrary_id"):
                if not result.get("externalSource"):
                    result["externalSource"] = []
                result["externalSource"].append({
                    "name": "OpenLibrary",
                    "id": openlibrary.get("openlibrary_id"),
                    "link": f"https://openlibrary.org/works/{openlibrary.get('openlibrary_id')}"
                })
            
            # 评分
            if openlibrary.get("rating"):
                if not result.get("scores"):
                    result["scores"] = {}
                result["scores"]["openlibrary"] = openlibrary.get("rating")
        
        # 百度百科数据
        baike = raw_data.get("baike", {})
        if baike:
            # 简介（中文书籍优先使用百度百科）
            if baike.get("summary"):
                result["summary"] = baike.get("summary")
            
            # 首版时间（优先级最高）
            if baike.get("year"):
                result["year"] = baike.get("year")
            
            # 字数
            if baike.get("word_count"):
                result["wordCount"] = baike.get("word_count")
            
            # 外文名（百度百科的外文名通常是官方英文译名，优先级高于 OpenLibrary）
            # 但如果是中文，则不使用（中文书籍无外文名）
            if baike.get("title_original"):
                title_orig = baike.get("title_original")
                # 检查是否为中文（如果是中文则置空）
                if not re.match(r'^[\u4e00-\u9fa5]+$', title_orig):
                    result["titleOriginal"] = title_orig
            
            # 别名（作品别名）
            if baike.get("info"):
                info = baike.get("info")
                if info.get("作品别名"):
                    result["otherTitles"] = [str(info.get("作品别名"))]
            
            # 出版社
            if baike.get("publisher"):
                result["publisher"] = baike.get("publisher")
            
            # 语言
            if baike.get("language"):
                result["language"] = baike.get("language")
            
            # 国家（从作者信息推断）
            if baike.get("country"):
                result["country"] = baike.get("country")
            
            # 作者
            if baike.get("author"):
                if not result.get("_authors"):
                    result["_authors"] = []
                if baike.get("author") not in result["_authors"]:
                    result["_authors"].append(baike.get("author"))
            
            # 外部来源
            if baike.get("url"):
                if not result.get("externalSource"):
                    result["externalSource"] = []
                result["externalSource"].append({
                    "name": "百度百科",
                    "id": baike.get("baike_id") or baike.get("title"),
                    "link": baike.get("url")
                })
        
        # Wikipedia 数据
        wikipedia = raw_data.get("wikipedia", {})
        if wikipedia:
            # 简介（如果百度百科没有，使用 Wikipedia）
            if not result.get("summary") and wikipedia.get("summary"):
                result["summary"] = wikipedia.get("summary")
            
            # 原标题（维基百科标题通常是原文，优先级最高）
            # 但如果是中文，则不使用（中文书籍无外文名）
            if wikipedia.get("title_original"):
                title_orig = wikipedia.get("title_original")
                if not re.match(r'^[\u4e00-\u9fa5]+$', title_orig):
                    result["titleOriginal"] = title_orig
            
            # 从 info 获取更多信息
            if wikipedia.get("info"):
                info = wikipedia.get("info")
                if info.get("原名") and not result.get("titleOriginal"):
                    title_orig = info.get("原名")
                    if not re.match(r'^[\u4e00-\u9fa5]+$', title_orig):
                        result["titleOriginal"] = title_orig
                if info.get("作者") and not result.get("_authors"):
                    result["_authors"] = [info.get("作者")]
                if info.get("出版机构") and not result.get("publisher"):
                    result["publisher"] = info.get("出版机构")
                if info.get("语言") and not result.get("language"):
                    result["language"] = str(info.get("语言"))
                # 从"地点"或"出版地"推断国家
                if not result.get("country"):
                    if info.get("地点"):
                        result["country"] = self._normalize_country(info.get("地点"))
                    elif info.get("出版地"):
                        result["country"] = self._normalize_country(info.get("出版地"))
            
            # 国家
            if wikipedia.get("country") and not result.get("country"):
                result["country"] = wikipedia.get("country")
            
            # 名句
            if wikipedia.get("quotes"):
                result["quotes"] = wikipedia.get("quotes")
            
            # 外部来源
            if wikipedia.get("url"):
                if not result.get("externalSource"):
                    result["externalSource"] = []
                result["externalSource"].append({
                    "name": "维基百科",
                    "id": wikipedia.get("wikipedia_id") or wikipedia.get("title"),
                    "link": wikipedia.get("url")
                })
        
        # Goodreads 数据
        goodreads = raw_data.get("goodreads", {})
        if goodreads:
            detail = goodreads.get("detail", {})
            if detail:
                # 原名（英文）
                if detail.get("title") and not result.get("titleOriginal"):
                    result["titleOriginal"] = detail.get("title")
                
                # 评分
                if detail.get("rating"):
                    if not result.get("scores"):
                        result["scores"] = {}
                    result["scores"]["goodreads"] = detail.get("rating")
                
                # 系列
                if detail.get("series"):
                    series_info = detail.get("series")
                    result["_series"] = series_info
                
                # 获奖
                awards = detail.get("awards", [])
                if awards:
                    result["_awards"] = awards
                
                # 类型标签
                genres = detail.get("genres", [])
                if genres:
                    result["_genres"] = genres
                
                # 外部来源
                if detail.get("goodreads_id"):
                    if not result.get("externalSource"):
                        result["externalSource"] = []
                    result["externalSource"].append({
                        "name": "Goodreads",
                        "id": detail.get("goodreads_id"),
                        "link": detail.get("url")
                    })
            
            # Goodreads 书评
            gr_reviews = goodreads.get("reviews", [])
            if gr_reviews:
                if not result.get("reviews"):
                    result["reviews"] = []
                result["reviews"].extend(gr_reviews)
        
        # 当当网数据
        dangdang = raw_data.get("dangdang", {})
        if dangdang:
            detail = dangdang.get("detail", {})
            if detail:
                # 字数（当当网优先）
                if detail.get("word_count"):
                    result["wordCount"] = detail.get("word_count")
                
                # 页数
                if detail.get("pages") and not result.get("pageCount"):
                    result["pageCount"] = detail.get("pages")
                
                # 获奖
                awards = detail.get("awards", [])
                if awards:
                    if not result.get("_awards"):
                        result["_awards"] = []
                    for award in awards:
                        if award not in result["_awards"]:
                            result["_awards"].append(award)
                
                # 系列
                if detail.get("series") and not result.get("_series"):
                    result["_series"] = {"name": detail.get("series")}
                
                # 简介（补充）
                if detail.get("summary") and not result.get("summary"):
                    result["summary"] = detail.get("summary")
                
                # 外部来源
                if detail.get("dangdang_id"):
                    if not result.get("externalSource"):
                        result["externalSource"] = []
                    result["externalSource"].append({
                        "name": "当当网",
                        "id": detail.get("dangdang_id"),
                        "link": detail.get("url")
                    })
        
        # 中国图书网数据
        bookchina = raw_data.get("bookchina", {})
        if bookchina:
            detail = bookchina.get("detail", {})
            if detail:
                # 字数（补充）
                if detail.get("word_count") and not result.get("wordCount"):
                    result["wordCount"] = detail.get("word_count")
                
                # 页数（补充）
                if detail.get("pages") and not result.get("pageCount"):
                    result["pageCount"] = detail.get("pages")
                
                # 出版社（补充）
                if detail.get("publisher") and not result.get("publisher"):
                    result["publisher"] = detail.get("publisher")
                
                # 外部来源
                if detail.get("bookchina_id"):
                    if not result.get("externalSource"):
                        result["externalSource"] = []
                    result["externalSource"].append({
                        "name": "中国图书网",
                        "id": detail.get("bookchina_id"),
                        "link": detail.get("url")
                    })
        
        # 当当网数据（出版社优先）
        dangdang = raw_data.get("dangdang", {})
        if dangdang:
            # 出版社（当当网优先）
            if dangdang.get("publisher"):
                result["publisher"] = dangdang.get("publisher")
            
            # 价格
            if dangdang.get("price"):
                if not result.get("_prices"):
                    result["_prices"] = {}
                result["_prices"]["dangdang"] = dangdang.get("price")
            
            # 页数
            if dangdang.get("pages"):
                result["pageCount"] = dangdang.get("pages")
            
            # 装帧
            if dangdang.get("binding"):
                result["binding"] = dangdang.get("binding")
            
            # 外部来源
            if dangdang.get("url"):
                if not result.get("externalSource"):
                    result["externalSource"] = []
                result["externalSource"].append({
                    "name": "当当网",
                    "id": dangdang.get("isbn") or "",
                    "link": dangdang.get("url")
                })
        
        # 起点中文网/网络小说数据
        qidian = raw_data.get("qidian", {})
        if qidian:
            # 网络小说：连载平台作为"出版社"
            if qidian.get("platform"):
                result["publisher"] = qidian.get("platform")
            
            # 字数（网络小说字数更准确）
            if qidian.get("word_count"):
                result["wordCount"] = qidian.get("word_count")
            
            # 连载状态
            if qidian.get("status"):
                result["_status"] = qidian.get("status")
            
            # 分类
            if qidian.get("category"):
                if not result.get("_categories"):
                    result["_categories"] = []
                result["_categories"].append(qidian.get("category"))
            
            # 简介
            if qidian.get("summary") and not result.get("summary"):
                result["summary"] = qidian.get("summary")
            
            # 外部来源
            if qidian.get("url"):
                if not result.get("externalSource"):
                    result["externalSource"] = []
                result["externalSource"].append({
                    "name": "起点中文网",
                    "id": qidian.get("title") or "",
                    "link": qidian.get("url")
                })
        
        # 书评
        reviews = raw_data.get("reviews", [])
        if reviews:
            result["reviews"] = reviews
        
        # 计算综合评分
        if result.get("scores"):
            scores = result["scores"]
            valid_scores = [v for k, v in scores.items() if k != "avg" and isinstance(v, (int, float))]
            if valid_scores:
                scores["avg"] = round(sum(valid_scores) / len(valid_scores), 1)
        
        # 转换 JSON 字段
        if result.get("externalSource"):
            result["externalSource"] = json.dumps(result["externalSource"], ensure_ascii=False)
        if result.get("scores"):
            result["scores"] = json.dumps(result["scores"], ensure_ascii=False)
        if result.get("images"):
            result["images"] = json.dumps(result["images"], ensure_ascii=False)
        if result.get("related"):
            result["related"] = json.dumps(result["related"], ensure_ascii=False)
        if result.get("quotes"):
            result["quotes"] = json.dumps(result["quotes"], ensure_ascii=False)
        if result.get("otherTitles"):
            result["otherTitles"] = json.dumps(result["otherTitles"], ensure_ascii=False)
        if result.get("reviews") is not None:
            result["reviews"] = json.dumps(result["reviews"], ensure_ascii=False)
        
        Logger.success(f"数据合并完成: {book_id}")
        return result
    
    def _normalize_country(self, location: str) -> str:
        """
        标准化国家名称
        
        Args:
            location: 地点/出版地
            
        Returns:
            标准化的国家名称
        """
        if not location:
            return None
        
        location = str(location).strip()
        
        # 常见地点到国家的映射
        country_map = {
            "中华民国": "中国",
            "中国": "中国",
            "中国大陆": "中国",
            "台湾": "中国",
            "香港": "中国",
            "美国": "美国",
            "英国": "英国",
            "日本": "日本",
            "法国": "法国",
            "德国": "德国",
            "俄罗斯": "俄罗斯",
            "苏联": "俄罗斯",
        }
        
        return country_map.get(location, location)
    
    def save_raw_data(self, book_id: str, source: str, data: Dict):
        """保存原始数据到 data/raw/{book_id}/"""
        book_raw_dir = self.raw_dir / book_id
        book_raw_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = book_raw_dir / f"{source}.json"
        filepath.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        Logger.info(f"已保存原始数据: {filepath}")
    
    def save_merged_data(self, book_id: str, data: Dict):
        """保存合并数据到 data/staging/{book_id}.json"""
        filepath = self.staging_dir / f"{book_id}.json"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        filepath.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        Logger.success(f"已保存合并数据: {filepath}")
