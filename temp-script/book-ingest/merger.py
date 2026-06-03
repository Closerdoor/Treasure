# -*- coding: utf-8 -*-
"""
数据合并模块

核心原则：
1. staging 保持对象/数组结构，不在合并阶段序列化 JSON 字符串
2. 每个关键字段记录数据来源（_meta.fieldSources）
3. 多源冲突时记录到 _meta.conflicts，保留优先级最高的值
4. 临时字段（authors/translators/tags 等）放入 _meta，与正式字段分离
5. 作者去重与清洗：去除国籍前缀，合并同名不同格式
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils import Logger, generate_book_id


def _is_valid(value) -> bool:
    """判断值是否为有效非空值"""
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    if isinstance(value, (list, dict)) and len(value) == 0:
        return False
    return True


def _is_chinese(text: str) -> bool:
    """判断文本是否全为中文"""
    if not text:
        return False
    return bool(re.match(r'^[\u4e00-\u9fa5]+$', text))


def _has_cjk(text: str) -> bool:
    return bool(text and re.search(r"[\u4e00-\u9fff]", text))


def _is_chinese_category(value) -> bool:
    """书籍类型 / 标签入库只接受中文值；英文分类保留在 raw/staging 审视字段。"""
    return _has_cjk(str(value).strip()) if value is not None else False


def _parse_int(value) -> Optional[int]:
    """从来源文本中提取整数。"""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    match = re.search(r"\d+", str(value).replace(",", ""))
    return int(match.group(0)) if match else None


def _is_chinese_text(value, min_cjk_ratio: float = 0.15) -> bool:
    """判断正文是否有足够中文内容，避免英文简介进入中文展示字段。"""
    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    letters = len(re.findall(r"[A-Za-z]", text))
    return cjk > 0 and cjk / max(cjk + letters, 1) >= min_cjk_ratio


def _extract_labeled_int(text: str, labels: List[str]) -> Optional[int]:
    """从一段中文商品详情中提取“字数/页码”等标签后的整数。"""
    if not text:
        return None
    for label in labels:
        pattern = rf"{re.escape(label)}\s*[：:\n\r\t ]*\s*([0-9][0-9,]*)"
        match = re.search(pattern, str(text))
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def _clean_dangdang_summary(detail: dict) -> Optional[str]:
    """从当当混合文本中提取适合前台展示的中文简介。"""
    candidates = [
        detail.get("summary"),
        detail.get("description"),
        detail.get("editor_recommend"),
        detail.get("author_intro"),
        detail.get("catalog"),
    ]
    for raw in candidates:
        if not isinstance(raw, str) or not raw.strip():
            continue
        text = raw.replace("\r", "\n")
        markers = ["内容简介", "内容介绍", "编辑推荐"]
        for marker in markers:
            idx = text.find(marker)
            if idx >= 0:
                text = text[idx + len(marker):]
                break
        for stop in ["作者简介", "目　　录", "目录", "商品详情", "在线试读", "图书信息"]:
            idx = text.find(stop)
            if idx > 0:
                text = text[:idx]
        text = re.sub(r"^\s*重磅推荐\s*", "", text)
        text = re.sub(r"\s+", " ", text).strip(" 　：:")
        if _is_chinese_text(text):
            return text
    return None


def _build_baike_public_url(title: str, baike_id) -> Optional[str]:
    """用百度百科条目 ID 生成公开词条链接，避免把本地 HTML 辅助路径写入数据库。"""
    if not _is_valid(title) or not _is_valid(baike_id):
        return None
    from urllib.parse import quote
    return f"https://baike.baidu.com/item/{quote(str(title).strip())}/{quote(str(baike_id).strip())}"


def _strip_country_prefix(name: str) -> tuple:
    """
    去除作者名中的国籍前缀，返回 (清洗后名字, 国籍)

    示例：
    - "[哥伦比亚] 加西亚·马尔克斯" → ("加西亚·马尔克斯", "哥伦比亚")
    - "【哥伦比亚】加西亚·马尔克斯" → ("加西亚·马尔克斯", "哥伦比亚")
    - "（美）海明威" → ("海明威", "美")
    - "加西亚·马尔克斯" → ("加西亚·马尔克斯", None)
    """
    if not name:
        return name, None

    match = re.match(r'^[【\[（\(]([^】\]\)）]+)[】\]\)）]\s*(.+)$', name)
    if match:
        country = match.group(1)
        clean_name = match.group(2).strip()
        return clean_name, country

    match = re.match(r'^([^\]】)）]{1,8})[\]】)）]\s*(.+)$', name)
    if match:
        country = match.group(1)
        clean_name = match.group(2).strip()
        return clean_name, country

    return name.strip(), None


def _normalize_country(location: str) -> Optional[str]:
    """标准化国家名称"""
    if not location:
        return None

    location = str(location).strip()

    country_map = {
        "中": "中国",
        "中华民国": "中国",
        "中国": "中国",
        "中国大陆": "中国",
        "台湾": "中国",
        "香港": "中国",
        "美": "美国",
        "美国": "美国",
        "英": "英国",
        "英国": "英国",
        "日": "日本",
        "日本": "日本",
        "法国": "法国",
        "德国": "德国",
        "俄罗斯": "俄罗斯",
        "苏联": "俄罗斯",
        "哥伦比亚": "哥伦比亚",
        "阿根廷": "阿根廷",
        "印度": "印度",
        "韩国": "韩国",
        "意大利": "意大利",
        "西班牙": "西班牙",
        "葡萄牙": "葡萄牙",
        "巴西": "巴西",
        "墨西哥": "墨西哥",
        "加拿大": "加拿大",
        "澳大利亚": "澳大利亚",
        "挪威": "挪威",
        "瑞典": "瑞典",
        "丹麦": "丹麦",
        "芬兰": "芬兰",
        "荷兰": "荷兰",
        "比利时": "比利时",
        "瑞士": "瑞士",
        "奥地利": "奥地利",
        "波兰": "波兰",
        "捷克": "捷克",
        "匈牙利": "匈牙利",
        "土耳其": "土耳其",
        "以色列": "以色列",
        "伊朗": "伊朗",
        "埃及": "埃及",
        "南非": "南非",
        "尼日利亚": "尼日利亚",
    }

    return country_map.get(location, location)


def _dedupe_authors(author_lists: List[List[str]]) -> List[str]:
    """
    合并多来源作者列表，去重并清洗国籍前缀

    策略：
    1. 逐列表合并，保留首次出现的名字
    2. 去除国籍前缀后比较，避免同一人因前缀不同被重复
    3. 保留清洗后的名字（不含国籍前缀）
    """
    seen_clean = set()
    result = []

    for authors in author_lists:
        if not authors:
            continue
        for name in authors:
            if not name or not name.strip():
                continue
            clean_name, _ = _strip_country_prefix(name)
            key = (
                clean_name.lower()
                .replace(" ", "")
                .replace("·", "")
                .replace(",", "")
                .replace("-", "")
                .replace("锺", "钟")
                .replace("鐘", "钟")
            )
            if key not in seen_clean:
                seen_clean.add(key)
                result.append(clean_name)

    if any(_has_cjk(name) for name in result):
        result = [name for name in result if _has_cjk(name)]

    return result


def _dedupe_excerpts(excerpts: List[dict]) -> List[dict]:
    """Keep excerpt order while removing duplicate detail URLs and duplicate text."""
    result = []
    seen_urls = set()
    seen_text = set()
    for item in excerpts or []:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "").strip()
        text = str(item.get("content") or "").strip()
        if not text:
            continue
        text_key = re.sub(r"\s+", "", text)
        if url and url in seen_urls:
            continue
        if text_key in seen_text:
            continue
        result.append(item)
        if url:
            seen_urls.add(url)
        seen_text.add(text_key)
    return result


def _series_key(value: str) -> str:
    if not value:
        return ""
    return re.sub(r"[\s《》〈〉「」『』\"'()（）:：·・.\-_/]+", "", str(value)).lower()


def _is_valid_series_candidate(item: dict, title: str = None) -> bool:
    """Reject source noise before it can create or link book_series records."""
    if not isinstance(item, dict):
        return False
    name = str(item.get("name") or "").strip()
    if not name:
        return False
    name_key = _series_key(name)
    title_key = _series_key(title or "")
    if title_key and name_key == title_key:
        return False
    url = str(item.get("url") or "").lower()
    if "novelupdates.com" in url:
        return False
    noisy_names = {
        "novelupdatesenglishtranslationpage",
        "englishtranslationpage",
    }
    if name_key in noisy_names:
        return False
    return True


def _has_truncation_ellipsis(value: str) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    return text.endswith("...") or text.endswith("…") or "..." in text[-20:]


def _is_web_novel(raw_data: dict) -> bool:
    qidian = raw_data.get("qidian") or {}
    if qidian.get("url") or qidian.get("title"):
        return True
    baike = raw_data.get("baike") or {}
    info = baike.get("info") if isinstance(baike.get("info"), dict) else {}
    markers = [
        baike.get("serial_platform"),
        baike.get("platform"),
        info.get("首发平台"),
        info.get("连载平台"),
        info.get("状态"),
    ]
    return any(marker and ("起点" in str(marker) or "连载" in str(marker) or "完结" in str(marker)) for marker in markers)


def _extract_country_from_authors(author_lists: List[List[str]]) -> Optional[str]:
    """从作者名中提取国籍信息（取第一个非空国籍）"""
    for authors in author_lists:
        if not authors:
            continue
        for name in authors:
            _, country = _strip_country_prefix(name)
            if country:
                return _normalize_country(country)
    return None


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
            raw_data: 原始数据（各来源），格式 {"douban": {...}, "openlibrary": {...}, ...}

        Returns:
            合并后的 staging 数据（对象/数组结构，不序列化 JSON 字符串）
        """
        Logger.info(f"正在合并数据: {book_id}")

        result = {
            "id": book_id,
            "title": None,
            "titleOriginal": None,
            "otherTitles": None,
            "isbn": None,
            "year": None,
            "country": None,
            "language": None,
            "wordCount": None,
            "publisher": None,
            "publishDate": None,
            "pages": None,
            "price": None,
            "binding": None,
            "format": None,
            "edition": None,
            "summary": None,
            "story": None,
            "quotes": None,
            "excerpts": None,
            "seriesId": None,
            "seriesOrder": None,
            "scores": None,
            "externalSource": None,
            "images": None,
            "reviews": None,
            "related": None,
            "status": "draft",
            "_meta": {
                "fieldSources": {},
                "conflicts": [],
                "authors": [],
                "translators": [],
                "tags": [],
                "subjects": [],
                "genres": [],
                "awards": [],
                "series": None,
                "seriesCandidates": [],
                "coverUrls": {},
                "prices": {},
                "personDetails": [],
            },
        }

        fs = result["_meta"]["fieldSources"]
        conflicts = result["_meta"]["conflicts"]
        meta = result["_meta"]
        is_web_novel = _is_web_novel(raw_data)
        meta["isWebNovel"] = is_web_novel

        # ============================================================
        # 各数据源提取（按优先级顺序，后提取的不会覆盖先提取的有效值）
        # ============================================================

        self._apply_douban(raw_data.get("douban", {}), result, fs, conflicts, meta, book_id)
        self._apply_baike(raw_data.get("baike", {}), result, fs, conflicts, meta, book_id)
        self._apply_wikipedia(raw_data.get("wikipedia", {}), result, fs, conflicts, meta, book_id)
        self._apply_openlibrary(raw_data.get("openlibrary", {}), result, fs, conflicts, meta, book_id)
        self._apply_goodreads(raw_data.get("goodreads", {}), result, fs, conflicts, meta, book_id)
        self._apply_dangdang(raw_data.get("dangdang", {}), result, fs, conflicts, meta, book_id)
        self._apply_qidian(raw_data.get("qidian", {}), result, fs, conflicts, meta, book_id)
        if is_web_novel:
            self._apply_web_novel_text_rules(raw_data, result, fs, conflicts, meta)
        self._filter_series_candidates(meta, result.get("title"))

        # ============================================================
        # 后处理
        # ============================================================

        # 作者去重与清洗
        all_author_lists = []
        douban = raw_data.get("douban", {})
        if douban.get("authors"):
            all_author_lists.append(douban["authors"])
        baike = raw_data.get("baike", {})
        if baike.get("author"):
            all_author_lists.append([baike["author"]])
        wikipedia = raw_data.get("wikipedia", {})
        if wikipedia.get("author"):
            all_author_lists.append([wikipedia["author"]])
        goodreads = raw_data.get("goodreads", {})
        gr_detail = goodreads.get("detail", goodreads)
        if gr_detail.get("authors"):
            gr_names = [a["name"] if isinstance(a, dict) else a for a in gr_detail["authors"]]
            all_author_lists.append(gr_names)
        dangdang = raw_data.get("dangdang", {})
        dd_detail = dangdang.get("detail", dangdang)
        if dd_detail.get("authors"):
            dd_names = [a["name"] if isinstance(a, dict) else a for a in dd_detail["authors"]]
            all_author_lists.append(dd_names)
        qidian = raw_data.get("qidian", {})
        if qidian.get("authors"):
            qd_names = [a["name"] if isinstance(a, dict) else a for a in qidian["authors"]]
            all_author_lists.append(qd_names)
        elif qidian.get("author"):
            all_author_lists.append([qidian["author"]])

        meta["authors"] = _dedupe_authors(all_author_lists)

        # 从作者名推断国家（如果还没有）
        if not _is_valid(result["country"]):
            country_from_author = _extract_country_from_authors(all_author_lists)
            if country_from_author:
                result["country"] = country_from_author
                fs["country"] = "author_inference"

        # 译者去重
        all_translator_lists = []
        if douban.get("translators"):
            all_translator_lists.append(douban["translators"])
        if wikipedia.get("translators"):
            wiki_translators = [t["name"] if isinstance(t, dict) else t for t in wikipedia["translators"]]
            all_translator_lists.append(wiki_translators)
        if gr_detail.get("translators"):
            gr_translators = [t["name"] if isinstance(t, dict) else t for t in gr_detail["translators"]]
            all_translator_lists.append(gr_translators)
        if dd_detail.get("translators"):
            dd_translators = [t["name"] if isinstance(t, dict) else t for t in dd_detail["translators"]]
            all_translator_lists.append(dd_translators)
        meta["translators"] = _dedupe_authors(all_translator_lists)

        if not _is_valid(result["language"]) and _has_cjk(str(result.get("title") or "")):
            result["language"] = "中文"
            fs["language"] = "title_inference"

        # 计算综合评分
        if result.get("scores") and isinstance(result["scores"], dict):
            scores = result["scores"]
            valid_scores = [v for k, v in scores.items() if k != "avg" and isinstance(v, (int, float))]
            if valid_scores:
                scores["avg"] = round(sum(valid_scores) / len(valid_scores), 1)

        # 构建 externalSource（从各来源收集）
        external = self._build_external_sources(raw_data, book_id)
        if external:
            result["externalSource"] = external

        # 构建 images
        if not result.get("images"):
            has_cover = any(meta["coverUrls"].values())
            if has_cover:
                result["images"] = {"cover": "cover-main.jpg", "covers": {}, "assetDir": book_id}

        # 构建 related
        if not result.get("related"):
            recommendations = douban.get("recommendations", [])
            if recommendations:
                related = {"similar": [], "series": [], "sameAuthor": []}
                for rec in recommendations:
                    rating_val = None
                    if rec.get("rating"):
                        try:
                            rating_val = float(rec["rating"])
                        except (ValueError, TypeError):
                            pass
                    related["similar"].append({
                        "title": rec.get("title"),
                        "year": None,
                        "rating": rating_val,
                        "bookId": None,
                    })
                result["related"] = related

        Logger.success(f"数据合并完成: {book_id}")
        return result

    def _add_series_candidate(self, meta: dict, series, source: str):
        """记录系列候选，不直接伪造 book_series ID。"""
        if not _is_valid(series):
            return
        item = series if isinstance(series, dict) else {"name": str(series)}
        if not item.get("name"):
            return
        item = {**item, "source": source}
        key = (item.get("name"), item.get("url", ""))
        existing = {
            (candidate.get("name"), candidate.get("url", ""))
            for candidate in meta.get("seriesCandidates", [])
        }
        if key not in existing:
            meta.setdefault("seriesCandidates", []).append(item)
        if not _is_valid(meta.get("series")):
            meta["series"] = item

    def _filter_series_candidates(self, meta: dict, title: str = None):
        candidates = [
            item for item in meta.get("seriesCandidates", [])
            if _is_valid_series_candidate(item, title)
        ]
        meta["seriesCandidates"] = candidates
        meta["series"] = candidates[0] if candidates else None

    def _set_field(self, result, fs, field, value, source, conflicts=None):
        """设置字段值，仅在当前值为空时设置，否则记录冲突"""
        if not _is_valid(value):
            return

        current = result.get(field)
        if not _is_valid(current):
            result[field] = value
            fs[field] = source
            return

        # 已有值，检查是否冲突
        if conflicts is not None and current != value:
            if field == "year" and isinstance(current, int) and isinstance(value, int):
                if abs(current - value) > 1:
                    conflicts.append({
                        "field": field,
                        "existing": {"value": current, "source": fs.get(field, "unknown")},
                        "candidate": {"value": value, "source": source},
                        "reason": f"年份差异 {abs(current - value)} 年",
                    })
            elif field == "summary" and isinstance(current, str) and isinstance(value, str):
                len_ratio = min(len(current), len(value)) / max(len(current), len(value), 1)
                if len_ratio < 0.5:
                    conflicts.append({
                        "field": field,
                        "existing": {"value_len": len(current), "source": fs.get(field, "unknown")},
                        "candidate": {"value_len": len(value), "source": source},
                        "reason": f"简介长度差异过大 ({len_ratio:.0%})",
                    })
            elif field == "titleOriginal":
                conflicts.append({
                    "field": field,
                    "existing": {"value": current, "source": fs.get(field, "unknown")},
                    "candidate": {"value": value, "source": source},
                    "reason": "原名多源不一致",
                })

    def _apply_douban(self, data: dict, result: dict, fs: dict, conflicts: list, meta: dict, book_id: str):
        """豆瓣数据（主源，优先级最高）"""
        if not data:
            return

        self._set_field(result, fs, "title", data.get("title"), "douban", conflicts)

        title_original = data.get("title_original")
        if _is_valid(title_original) and not _is_chinese(title_original):
            self._set_field(result, fs, "titleOriginal", title_original, "douban", conflicts)

        self._set_field(result, fs, "isbn", data.get("isbn"), "douban", conflicts)
        self._set_field(result, fs, "year", data.get("year"), "douban", conflicts)
        self._set_field(result, fs, "publisher", data.get("publisher"), "douban", conflicts)
        self._set_field(result, fs, "publishDate", data.get("publish_date"), "douban", conflicts)
        self._set_field(result, fs, "pages", _parse_int(data.get("pages")), "douban", conflicts)
        self._set_field(result, fs, "price", data.get("price"), "douban", conflicts)
        self._set_field(result, fs, "binding", data.get("binding"), "douban", conflicts)
        self._set_field(result, fs, "format", data.get("format"), "douban", conflicts)
        self._set_field(result, fs, "edition", data.get("edition"), "douban", conflicts)
        if _is_valid(data.get("summary")):
            meta["doubanSummary"] = data.get("summary")

        rating = data.get("rating")
        if _is_valid(rating):
            try:
                result["scores"] = {"douban": float(rating)}
                fs["scores"] = "douban"
            except (ValueError, TypeError):
                pass

        cover_url = data.get("main_cover_url")
        if _is_valid(cover_url):
            result["images"] = {"cover": "cover-main.jpg", "covers": {}, "assetDir": book_id}
            meta["coverUrls"]["douban"] = cover_url

        tags = data.get("tags", [])
        if tags:
            meta["tags"] = [str(tag).strip() for tag in tags if _is_chinese_category(tag)]

        series = data.get("series")
        if _is_valid(series):
            self._add_series_candidate(meta, series, "douban")

        comments = data.get("comments", [])
        reviews = data.get("reviews", [])
        combined_reviews = []
        if comments:
            combined_reviews.extend(comments)
        if reviews:
            combined_reviews.extend(reviews)
        if combined_reviews:
            result["reviews"] = combined_reviews
            fs["reviews"] = "douban"

        excerpts = data.get("excerpts", [])
        if excerpts:
            result["excerpts"] = _dedupe_excerpts(excerpts)
            fs["excerpts"] = "douban"

        person_details = data.get("person_details", [])
        if person_details:
            meta["personDetails"] = person_details

    def _apply_baike(self, data: dict, result: dict, fs: dict, conflicts: list, meta: dict, book_id: str):
        """百度百科数据"""
        if not data:
            return

        if not _is_valid(result["title"]):
            title = data.get("baike_title") or data.get("title")
            self._set_field(result, fs, "title", title, "baike", conflicts)

        title_original = data.get("title_original")
        if _is_valid(title_original) and not _is_chinese(title_original):
            self._set_field(result, fs, "titleOriginal", title_original, "baike", conflicts)

        # year 表示作品首版年，百度百科的首版时间优先级最高，可覆盖豆瓣版本出版年。
        if _is_valid(data.get("year")):
            current_year = result.get("year")
            if _is_valid(current_year) and current_year != data["year"] and conflicts is not None:
                conflicts.append({
                    "field": "year",
                    "existing": {"value": current_year, "source": fs.get("year", "unknown")},
                    "candidate": {"value": data["year"], "source": "baike"},
                    "reason": "year 使用作品首版年，百度百科覆盖版本出版年",
                    "resolution": "use_candidate",
                })
            result["year"] = data["year"]
            fs["year"] = "baike"

        if _is_valid(data.get("word_count")):
            self._set_field(result, fs, "wordCount", data["word_count"], "baike", conflicts)

        # 国家：从作者字段提取的国籍前缀，无前缀默认中国
        if _is_valid(data.get("country")):
            self._set_field(result, fs, "country", _normalize_country(data["country"]), "baike", conflicts)
        elif _is_valid(data.get("authors")):
            self._set_field(result, fs, "country", "中国", "baike", conflicts)

        if _is_valid(data.get("language")):
            self._set_field(result, fs, "language", data["language"], "baike", conflicts)

        # 百度百科简介作为中文补充；summary 正式优先取 Wikipedia 的“故事大纲”。
        if _is_valid(data.get("summary")) and _is_chinese_text(data.get("summary")):
            meta["baikeSummary"] = data.get("summary")
            if not _is_valid(result["summary"]):
                self._set_field(result, fs, "summary", data["summary"], "baike", conflicts)

        # 完整剧情 / 内容情节：优先取百度百科“内容情节”等正文分节。
        story = data.get("story") or data.get("content_plot") or data.get("plot")
        if _is_valid(story) and _is_chinese_text(story):
            self._set_field(result, fs, "story", story, "baike", conflicts)

        # 出版社作为补充（不覆盖豆瓣）
        if not _is_valid(result["publisher"]) and _is_valid(data.get("publisher")):
            self._set_field(result, fs, "publisher", data["publisher"], "baike", conflicts)

        self._set_field(result, fs, "pages", _parse_int(data.get("pages")), "baike", conflicts)
        self._set_field(result, fs, "price", data.get("price"), "baike", conflicts)

        # 作者（补充，列表格式）
        if _is_valid(data.get("authors")) and not meta["authors"]:
            meta["authors"] = data["authors"]

        info = data.get("info", {})
        if isinstance(info, dict):
            if info.get("作品别名"):
                other_titles = [str(info["作品别名"])]
                if not _is_valid(result["otherTitles"]):
                    result["otherTitles"] = other_titles
                    fs["otherTitles"] = "baike"
                else:
                    for t in other_titles:
                        if t not in result["otherTitles"]:
                            result["otherTitles"].append(t)

            if info.get("出版时间") and not _is_valid(result["publishDate"]):
                self._set_field(result, fs, "publishDate", str(info["出版时间"]), "baike", conflicts)

            if info.get("页数") and not _is_valid(result["pages"]):
                self._set_field(result, fs, "pages", _parse_int(info["页数"]), "baike", conflicts)

            if info.get("定价") and not _is_valid(result["price"]):
                self._set_field(result, fs, "price", str(info["定价"]), "baike", conflicts)

            for info_key, field in [("装帧", "binding"), ("开本", "format"), ("版次", "edition")]:
                if info.get(info_key) and not _is_valid(result[field]):
                    self._set_field(result, fs, field, str(info[info_key]), "baike", conflicts)

            genre = data.get("genre") or data.get("type")
            for info_key in ("文学体裁", "作品类型", "类型", "体裁"):
                if not _is_valid(genre) and _is_valid(info.get(info_key)):
                    genre = info[info_key]
            if _is_valid(genre):
                values = genre if isinstance(genre, list) else [genre]
                for item in values:
                    item = str(item).strip()
                    if _is_chinese_category(item) and item not in meta["genres"]:
                        meta["genres"].append(item)

    def _apply_wikipedia(self, data: dict, result: dict, fs: dict, conflicts: list, meta: dict, book_id: str):
        """维基百科数据"""
        if not data:
            return

        if not _is_valid(result["title"]):
            self._set_field(result, fs, "title", data.get("title"), "wikipedia", conflicts)

        # 维基百科的 title_original 优先级最高（通常是原文标题）
        title_original = data.get("title_original")
        if _is_valid(title_original) and not _is_chinese(title_original):
            result["titleOriginal"] = title_original
            fs["titleOriginal"] = "wikipedia"

        # 内容简介：按当前规则优先取 Wikipedia 的“故事大纲”分节。
        if not _is_valid(result["summary"]) and _is_valid(data.get("summary")) and _is_chinese_text(data.get("summary")):
            self._set_field(result, fs, "summary", data["summary"], "wikipedia", conflicts)

        # 国家
        if not _is_valid(result["country"]) and _is_valid(data.get("country")):
            self._set_field(result, fs, "country", _normalize_country(data["country"]), "wikipedia", conflicts)

        # 语言
        if not _is_valid(result["language"]) and _is_valid(data.get("language")) and _is_chinese_text(str(data.get("language"))):
            self._set_field(result, fs, "language", str(data["language"]), "wikipedia", conflicts)

        # 类型 / 体裁：书籍也要像电影一样落到 category.group = type。
        genre = data.get("genre") or (data.get("info") or {}).get("类型") or (data.get("info") or {}).get("体裁")
        if _is_valid(genre):
            values = genre if isinstance(genre, list) else [genre]
            for item in values:
                item = str(item).strip()
                if _is_chinese_category(item) and item not in meta["genres"]:
                    meta["genres"].append(item)

        # 名句
        if _is_valid(data.get("quotes")):
            result["quotes"] = data["quotes"]
            fs["quotes"] = "wikipedia"

        # 作者（补充，列表格式）
        if _is_valid(data.get("authors")) and not meta["authors"]:
            meta["authors"] = data["authors"]

        # 译者（补充，列表格式）
        if _is_valid(data.get("translators")) and not meta["translators"]:
            meta["translators"] = data["translators"]

        # 别名（从翻译版本提取）
        if _is_valid(data.get("other_titles")) and not _is_valid(result["otherTitles"]):
            result["otherTitles"] = data["other_titles"]
            fs["otherTitles"] = "wikipedia"

        # 封面URL
        cover_url = data.get("cover_url")
        if _is_valid(cover_url) and not _is_valid(meta["coverUrls"].get("wikipedia")):
            meta["coverUrls"]["wikipedia"] = cover_url

        # 从 info 提取补充信息
        info = data.get("info", {})
        if isinstance(info, dict):
            if info.get("原名") and not _is_valid(result["titleOriginal"]):
                title_orig = info["原名"]
                if not _is_chinese(title_orig):
                    result["titleOriginal"] = title_orig
                    fs["titleOriginal"] = "wikipedia"

            if info.get("出版机构") and not _is_valid(result["publisher"]):
                self._set_field(result, fs, "publisher", info["出版机构"], "wikipedia", conflicts)

            if info.get("出版日期"):
                self._set_field(result, fs, "publishDate", str(info["出版日期"]), "wikipedia", conflicts)
            if info.get("出版日期") and not _is_valid(result["year"]):
                year_match = re.search(r"(\d{4})", str(info["出版日期"]))
                if year_match:
                    self._set_field(result, fs, "year", int(year_match.group(1)), "wikipedia", conflicts)

            if info.get("页数") and not _is_valid(result["pages"]):
                self._set_field(result, fs, "pages", _parse_int(info["页数"]), "wikipedia", conflicts)

            if info.get("系列"):
                self._add_series_candidate(meta, {"name": str(info["系列"])}, "wikipedia")

            if not _is_valid(result["country"]):
                for key in ["地点", "出版地", "国家", "Country"]:
                    if info.get(key):
                        country = _normalize_country(str(info[key]))
                        if country:
                            self._set_field(result, fs, "country", country, "wikipedia", conflicts)
                            break

    def _apply_openlibrary(self, data: dict, result: dict, fs: dict, conflicts: list, meta: dict, book_id: str):
        """OpenLibrary 数据"""
        if not data:
            return

        if not _is_valid(result["title"]):
            self._set_field(result, fs, "title", data.get("title"), "openlibrary", conflicts)

        # 原名作为补充（通常是罗马化标题，优先级低）
        if not _is_valid(result["titleOriginal"]):
            title_orig = data.get("title")
            if _is_valid(title_orig) and not _is_chinese(title_orig):
                self._set_field(result, fs, "titleOriginal", title_orig, "openlibrary", conflicts)

        if not _is_valid(result["isbn"]) and _is_valid(data.get("isbn")):
            self._set_field(result, fs, "isbn", data["isbn"], "openlibrary", conflicts)

        if not _is_valid(result["summary"]) and _is_valid(data.get("description")) and _is_chinese_text(data.get("description")):
            self._set_field(result, fs, "summary", data["description"], "openlibrary", conflicts)

        if not _is_valid(result["year"]) and _is_valid(data.get("first_publish_year")):
            self._set_field(result, fs, "year", data["first_publish_year"], "openlibrary", conflicts)

        if not _is_valid(result["publisher"]) and _is_valid(data.get("publisher")):
            self._set_field(result, fs, "publisher", data["publisher"], "openlibrary", conflicts)

        if not _is_valid(result["language"]) and _is_valid(data.get("language")) and _is_chinese_text(str(data.get("language"))):
            self._set_field(result, fs, "language", str(data["language"]), "openlibrary", conflicts)

        # 封面 URL
        cover_url = data.get("cover_url")
        if _is_valid(cover_url):
            meta["coverUrls"]["openlibrary"] = cover_url

        cover_urls = data.get("cover_urls", [])
        if cover_urls and _is_valid(result.get("images")):
            result["images"]["covers"] = result["images"].get("covers") or {}

        # 主题标签
        subjects = data.get("subjects", [])
        if subjects:
            chinese_subjects = [str(subject).strip() for subject in subjects if _is_chinese_category(subject)]
            if chinese_subjects:
                meta["subjects"] = chinese_subjects
            if len(chinese_subjects) != len(subjects):
                meta["rawOpenLibrarySubjects"] = subjects

        # 评分
        rating = data.get("rating")
        if _is_valid(rating):
            if not _is_valid(result.get("scores")):
                result["scores"] = {}
            if isinstance(result["scores"], dict):
                result["scores"]["openlibrary"] = rating

        # 作者（补充）
        if data.get("authors") and not meta["authors"]:
            meta["authors"] = data["authors"]

    def _apply_goodreads(self, data: dict, result: dict, fs: dict, conflicts: list, meta: dict, book_id: str):
        """Goodreads 数据"""
        if not data:
            return

        detail = data.get("detail", data)
        if not detail:
            return

        if not _is_valid(result["title"]):
            self._set_field(result, fs, "title", detail.get("title"), "goodreads", conflicts)

        # 原名（英文）
        if not _is_valid(result["titleOriginal"]) and _is_valid(detail.get("title")):
            title_orig = detail["title"]
            if not _is_chinese(title_orig):
                self._set_field(result, fs, "titleOriginal", title_orig, "goodreads", conflicts)

        # ISBN
        if not _is_valid(result["isbn"]) and _is_valid(detail.get("isbn")):
            self._set_field(result, fs, "isbn", detail["isbn"], "goodreads", conflicts)

        # 评分
        if _is_valid(detail.get("rating")):
            if not _is_valid(result.get("scores")):
                result["scores"] = {}
            if isinstance(result["scores"], dict):
                result["scores"]["goodreads"] = detail["rating"]

        # 封面
        cover_url = detail.get("cover_url")
        if _is_valid(cover_url):
            meta["coverUrls"]["goodreads"] = cover_url

        # 系列
        if _is_valid(detail.get("series")) and not _is_valid(meta["series"]):
            self._add_series_candidate(meta, detail["series"], "goodreads")

        # Goodreads 页面结构容易把站点导航分类误识别为书籍类型，先保留 raw，不入库。
        genres = detail.get("genres", [])
        if genres:
            meta["rawGoodreadsGenres"] = genres

        # 页数
        if _is_valid(detail.get("pages")) and not _is_valid(result["pages"]):
            self._set_field(result, fs, "pages", _parse_int(detail["pages"]), "goodreads", conflicts)

        # 出版年
        if not _is_valid(result["year"]) and _is_valid(detail.get("year")):
            self._set_field(result, fs, "year", detail["year"], "goodreads", conflicts)

        # 出版社
        if not _is_valid(result["publisher"]) and _is_valid(detail.get("publisher")):
            self._set_field(result, fs, "publisher", detail["publisher"], "goodreads", conflicts)

        # 简介
        if not _is_valid(result["summary"]) and _is_valid(detail.get("summary")) and _is_chinese_text(detail.get("summary")):
            self._set_field(result, fs, "summary", detail["summary"], "goodreads", conflicts)

        # 译者
        if _is_valid(detail.get("translators")) and not meta["translators"]:
            translator_names = [t["name"] if isinstance(t, dict) else t for t in detail["translators"]]
            meta["translators"] = translator_names

        # 书评
        gr_reviews = data.get("reviews", [])
        if gr_reviews:
            if not _is_valid(result.get("reviews")):
                result["reviews"] = []
            if isinstance(result["reviews"], list):
                result["reviews"].extend(gr_reviews)

        # 相似推荐
        similar_books = detail.get("similar_books", [])
        if similar_books and not _is_valid(result.get("related")):
            related = {"similar": [], "series": [], "sameAuthor": []}
            for book in similar_books:
                book_title = book.get("title") if isinstance(book, dict) else str(book)
                if book_title:
                    related["similar"].append({
                        "title": book_title,
                        "year": None,
                        "rating": None,
                        "bookId": None,
                    })
            if related["similar"]:
                result["related"] = related

    def _apply_dangdang(self, data: dict, result: dict, fs: dict, conflicts: list, meta: dict, book_id: str):
        """当当网数据"""
        if not data:
            return

        detail = data.get("detail", data)

        if not _is_valid(result["title"]):
            self._set_field(result, fs, "title", detail.get("title"), "dangdang", conflicts)

        # ISBN
        if not _is_valid(result["isbn"]) and _is_valid(detail.get("isbn")):
            self._set_field(result, fs, "isbn", detail["isbn"], "dangdang", conflicts)

        # 出版社作为补充
        if not _is_valid(result["publisher"]) and _is_valid(detail.get("publisher")):
            self._set_field(result, fs, "publisher", detail["publisher"], "dangdang", conflicts)

        # 字数
        word_count = detail.get("word_count")
        if not _is_valid(word_count):
            mixed_text = "\n".join(
                str(detail.get(key) or "")
                for key in ["author_intro", "editor_recommend", "catalog"]
            )
            word_count = _extract_labeled_int(mixed_text, ["字数"])
        if not _is_valid(result["wordCount"]) and _is_valid(word_count):
            self._set_field(result, fs, "wordCount", word_count, "dangdang", conflicts)

        # 页数（当当网优先）
        pages = detail.get("pages")
        if not _is_valid(pages):
            mixed_text = "\n".join(
                str(detail.get(key) or "")
                for key in ["author_intro", "editor_recommend", "catalog"]
            )
            pages = _extract_labeled_int(mixed_text, ["页码", "页数"])
        if _is_valid(pages):
            self._set_field(result, fs, "pages", _parse_int(pages), "dangdang", conflicts)

        # 价格
        if _is_valid(detail.get("price")):
            meta["prices"]["dangdang"] = detail["price"]
            self._set_field(result, fs, "price", str(detail["price"]), "dangdang", conflicts)

        for source_key, field in [("binding", "binding"), ("format", "format"), ("edition", "edition")]:
            if _is_valid(detail.get(source_key)):
                self._set_field(result, fs, field, str(detail[source_key]), "dangdang", conflicts)

        # 出版年
        if not _is_valid(result["year"]) and _is_valid(detail.get("publish_year")):
            self._set_field(result, fs, "year", detail["publish_year"], "dangdang", conflicts)
        if _is_valid(detail.get("publish_date")):
            self._set_field(result, fs, "publishDate", detail["publish_date"], "dangdang", conflicts)

        # 简介
        dangdang_summary = _clean_dangdang_summary(detail)
        if not _is_valid(result["summary"]) and _is_valid(dangdang_summary):
            self._set_field(result, fs, "summary", dangdang_summary, "dangdang", conflicts)

        # 译者
        if _is_valid(detail.get("translators")) and not meta["translators"]:
            dd_translators = [t["name"] if isinstance(t, dict) else t for t in detail["translators"]]
            meta["translators"] = dd_translators

        # 丛书
        if _is_valid(detail.get("series_name")) and not _is_valid(meta["series"]):
            self._add_series_candidate(meta, {"name": detail["series_name"]}, "dangdang")

        # 封面
        cover_url = detail.get("cover_url")
        if _is_valid(cover_url):
            meta["coverUrls"]["dangdang"] = cover_url

    def _apply_qidian(self, data: dict, result: dict, fs: dict, conflicts: list, meta: dict, book_id: str):
        """起点中文网数据（网络小说专用）"""
        if not data:
            return

        qidian_title = data.get("title")
        if _is_valid(qidian_title):
            current_title = result.get("title")
            if not _is_valid(current_title):
                self._set_field(result, fs, "title", qidian_title, "qidian", conflicts)
            elif str(qidian_title) in str(current_title) and str(qidian_title) != str(current_title):
                if not isinstance(result.get("otherTitles"), list):
                    result["otherTitles"] = []
                if current_title not in result["otherTitles"]:
                    result["otherTitles"].append(current_title)
                result["title"] = qidian_title
                fs["title"] = "qidian"

        # 字数（网络小说字数更准确）
        if _is_valid(data.get("word_count")):
            result["wordCount"] = data["word_count"]
            fs["wordCount"] = "qidian"

        if not _is_valid(result.get("country")):
            result["country"] = "中国"
            fs["country"] = "qidian"
        if not _is_valid(result.get("language")):
            result["language"] = "中文"
            fs["language"] = "qidian"

        # 连载状态
        if _is_valid(data.get("status")):
            meta["serialStatus"] = data["status"]

        # 分类
        if _is_valid(data.get("category")):
            category = str(data["category"]).strip()
            values = [item.strip() for item in re.split(r"[/、,，|]", category) if item.strip()]
            meta["genres"] = [item for item in values if _is_chinese_category(item)]

        # 标签
        tags = data.get("tags", [])
        if tags and not meta["tags"]:
            meta["tags"] = [str(tag).strip() for tag in tags if _is_chinese_category(tag)]

        # 简介
        if not _is_valid(result["summary"]) and _is_valid(data.get("summary")):
            self._set_field(result, fs, "summary", data["summary"], "qidian", conflicts)

        # 封面
        cover_url = data.get("cover_url")
        if _is_valid(cover_url):
            meta["coverUrls"]["qidian"] = cover_url

    def _apply_web_novel_text_rules(self, raw_data: dict, result: dict, fs: dict, conflicts: list, meta: dict):
        """
        网络小说专用文本规则：
        - summary 只取起点或豆瓣介绍，不使用 Wikipedia。
        - story 取百度百科词条顶部正文，用于对齐“完整剧情 / 内容情节”展示位。
        """
        qidian = raw_data.get("qidian") or {}
        douban = raw_data.get("douban") or {}
        baike = raw_data.get("baike") or {}

        summary_candidates = [
            ("qidian", qidian.get("summary")),
            ("douban", douban.get("summary")),
        ]
        for source, value in summary_candidates:
            if _is_valid(value) and _is_chinese_text(value) and not _has_truncation_ellipsis(value):
                result["summary"] = str(value).strip()
                fs["summary"] = source
                break
        else:
            if fs.get("summary") not in {"qidian", "douban"}:
                result["summary"] = None
                fs.pop("summary", None)

        story_candidates = [
            baike.get("top_content"),
            baike.get("topContent"),
            baike.get("summary"),
        ]
        for value in story_candidates:
            if _is_valid(value) and _is_chinese_text(value) and not _has_truncation_ellipsis(value):
                result["story"] = str(value).strip()
                fs["story"] = "baike_top"
                break
        else:
            if fs.get("story") != "baike_top":
                result["story"] = None
                fs.pop("story", None)

    def _build_external_sources(self, raw_data: dict, book_id: str) -> list:
        """从各来源构建 externalSource 列表"""
        external = []

        douban = raw_data.get("douban", {})
        if douban.get("douban_id"):
            external.append({
                "name": "豆瓣",
                "id": str(douban["douban_id"]),
                "link": f"https://book.douban.com/subject/{douban['douban_id']}/",
            })

        # ISBN 条目
        isbn = None
        for source_name in ["douban", "openlibrary", "goodreads", "dangdang"]:
            src = raw_data.get(source_name, {})
            detail = src.get("detail", src)
            isbn = detail.get("isbn") or src.get("isbn")
            if _is_valid(isbn):
                break
        if _is_valid(isbn):
            existing_ids = [e["id"] for e in external]
            if str(isbn) not in existing_ids:
                external.append({"name": "ISBN", "id": str(isbn), "link": None})

        openlibrary = raw_data.get("openlibrary", {})
        if openlibrary.get("openlibrary_id"):
            external.append({
                "name": "OpenLibrary",
                "id": openlibrary["openlibrary_id"],
                "link": f"https://openlibrary.org/works/{openlibrary['openlibrary_id']}",
            })

        baike = raw_data.get("baike", {})
        if baike.get("baike_id") or baike.get("url"):
            baike_id = baike.get("baike_id") or baike.get("title", "")
            public_link = _build_baike_public_url(baike.get("baike_title") or baike.get("title"), baike_id)
            if not public_link and str(baike.get("url", "")).startswith(("http://", "https://")):
                public_link = baike["url"]
            external.append({
                "name": "百度百科",
                "id": str(baike_id),
                "link": public_link,
            })

        wikipedia = raw_data.get("wikipedia", {})
        if wikipedia.get("url"):
            external.append({
                "name": "维基百科",
                "id": wikipedia.get("wikipedia_id") or wikipedia.get("title", ""),
                "link": wikipedia["url"],
            })

        goodreads = raw_data.get("goodreads", {})
        gr_detail = goodreads.get("detail", goodreads)
        if gr_detail.get("goodreads_id"):
            external.append({
                "name": "Goodreads",
                "id": str(gr_detail["goodreads_id"]),
                "link": gr_detail.get("url", ""),
            })

        dangdang = raw_data.get("dangdang", {})
        dd_detail = dangdang.get("detail", dangdang)
        if dd_detail.get("url"):
            external.append({
                "name": "当当网",
                "id": dd_detail.get("dangdang_id") or dd_detail.get("isbn") or "",
                "link": dd_detail["url"],
            })

        qidian = raw_data.get("qidian", {})
        if qidian.get("url"):
            external.append({
                "name": "起点中文网",
                "id": qidian.get("title") or "",
                "link": qidian["url"],
            })

        return external

    def save_raw_data(self, book_id: str, source: str, data: Dict):
        """保存原始数据到 data/raw/{book_id}/"""
        book_raw_dir = self.raw_dir / book_id
        book_raw_dir.mkdir(parents=True, exist_ok=True)

        filepath = book_raw_dir / f"{source}.json"
        filepath.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        Logger.info(f"已保存原始数据: {filepath}")

    def save_merged_data(self, book_id: str, data: Dict):
        """保存合并数据到 data/staging/{book_id}.json"""
        filepath = self.staging_dir / f"{book_id}.json"
        filepath.parent.mkdir(parents=True, exist_ok=True)

        filepath.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        Logger.success(f"已保存合并数据: {filepath}")

    def load_raw_data(self, book_id: str) -> Dict[str, Any]:
        """加载某本书的所有 raw 数据"""
        raw_dir = self.raw_dir / book_id
        if not raw_dir.exists():
            return {}

        result = {}
        for filepath in raw_dir.glob("*.json"):
            source_name = filepath.stem
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                result[source_name] = data
            except Exception as e:
                Logger.warning(f"加载 raw 数据失败: {filepath} - {e}")

        return result
