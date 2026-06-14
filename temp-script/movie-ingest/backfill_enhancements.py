# -*- coding: utf-8 -*-
"""
回填剧集 / 番剧增强字段。

只处理 episodesStory / characters，不重跑完整媒体采集，不下载图片，不刷新评论。
分集剧情不设置采样上限；如果无法覆盖 episodeCount 的每一集，预检会失败。
"""
import argparse
import asyncio
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import config
from import_staging import apply_import, precheck
from merger import DataMerger
from sources.baike import BaikeCrawler
from sources.douban import DoubanCrawler
from sources.tmdb import TMDBClient
from utils import Logger


DEFAULT_QUEUE = (
    config.DATA_DIR
    / "batch-runs"
    / "2026-06-13-media-validation"
    / "enhancement-queue.json"
)


def read_json(path: Path, fallback: Any = None) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_json_text(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def load_db_work(work_id: str) -> Dict[str, Any]:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM works WHERE id = ?", (work_id,)).fetchone()
    conn.close()
    if not row:
        raise ValueError(f"数据库中不存在作品: {work_id}")
    return dict(row)


def source_map_from_work(work: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    sources = parse_json_text(work.get("external_source"), [])
    result: Dict[str, Dict[str, str]] = {}
    if not isinstance(sources, list):
        return result
    for source in sources:
        if not isinstance(source, dict):
            continue
        name = str(source.get("name") or "").lower()
        item = {
            "id": str(source.get("id") or ""),
            "link": str(source.get("link") or ""),
            "name": str(source.get("name") or ""),
        }
        if "豆瓣" in name or "douban" in name:
            result["douban"] = item
        elif "百度" in name or "baike" in name:
            result["baike"] = item
        elif "tmdb" in name:
            result["tmdb"] = item
        elif "imdb" in name:
            result["imdb"] = item
    return result


def load_staging(work_id: str) -> Dict[str, Any]:
    staging_path = config.STAGING_DIR / f"{work_id}.json"
    if staging_path.exists():
        return read_json(staging_path, {})

    work = load_db_work(work_id)
    return {
        "id": work_id,
        "module": work.get("module"),
        "submodule": work.get("submodule"),
        "schemaType": work.get("schema_type"),
        "title": work.get("title"),
        "originalTitle": work.get("title_original"),
        "year": work.get("year"),
        "episodeCount": work.get("episode_count"),
        "episodeTime": work.get("episode_time"),
        "episodesStory": parse_json_text(work.get("episodes_story"), []),
        "characters": parse_json_text(work.get("characters"), []),
    }


def episode_number(item: Dict[str, Any], fallback: int = 0) -> Optional[int]:
    value = item.get("episode") or item.get("episodeNumber") or item.get("number") or fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def story_text(item: Dict[str, Any]) -> str:
    return str(item.get("story") or item.get("summary") or item.get("content") or "").strip()


def merge_episodes(*groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """不截断分集；同集多来源时保留剧情正文更完整的一条。"""
    by_number: Dict[int, Dict[str, Any]] = {}
    extra: List[Dict[str, Any]] = []

    for group in groups:
        for index, item in enumerate(group or [], start=1):
            if not isinstance(item, dict):
                continue
            if not story_text(item):
                continue
            number = episode_number(item, index)
            normalized = {
                key: value
                for key, value in {
                    "episode": number,
                    "title": item.get("title") or (f"第 {number} 集" if number else ""),
                    "story": story_text(item),
                    "source": item.get("source"),
                    "sourceUrl": item.get("sourceUrl") or item.get("source_url") or item.get("url"),
                }.items()
                if value not in (None, "")
            }
            if not number:
                extra.append(normalized)
                continue

            previous = by_number.get(number)
            if not previous or len(story_text(normalized)) > len(story_text(previous)):
                by_number[number] = normalized

    return [by_number[key] for key in sorted(by_number)] + extra


def split_out_of_scope_episodes(
    episodes: List[Dict[str, Any]],
    expected_count: int
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """按作品 episodeCount 过滤入库范围；原始越界数据仍保留在 raw 快照。"""
    if not expected_count:
        return episodes, []
    in_scope: List[Dict[str, Any]] = []
    out_of_scope: List[Dict[str, Any]] = []
    for item in episodes or []:
        number = episode_number(item)
        if number and number > expected_count:
            out_of_scope.append(item)
            continue
        in_scope.append(item)
    return in_scope, out_of_scope


def merge_characters(*groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """角色不截断，仅按角色名 + 演员名去重。"""
    merged: List[Dict[str, Any]] = []
    seen = set()
    for group in groups:
        for item in group or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("character") or "").strip()
            name_en = str(item.get("nameEn") or item.get("characterEn") or "").strip()
            actor = str(item.get("actorName") or item.get("actor") or item.get("nameActor") or "").strip()
            if not name and not name_en:
                continue
            key = (name, name_en, actor)
            if key in seen:
                continue
            seen.add(key)
            merged.append({
                key_name: value
                for key_name, value in {
                    "name": name,
                    "nameEn": name_en,
                    "actorName": actor,
                    "actorNameEn": item.get("actorNameEn"),
                    "actorDoubanId": item.get("actorDoubanId") or item.get("doubanId"),
                    "actorTmdbId": item.get("actorTmdbId") or item.get("tmdbId"),
                    "actorAvatar": item.get("actorAvatar") or item.get("avatar"),
                    "source": item.get("source"),
                    "sourceUrl": item.get("sourceUrl") or item.get("source_url") or item.get("link") or item.get("url"),
                    "description": item.get("description") or item.get("intro") or item.get("note") or "",
                }.items()
                if value not in (None, "")
            })
    return merged


def missing_episode_numbers(episodes: List[Dict[str, Any]], expected_count: int) -> List[int]:
    if not expected_count:
        return []
    present = {
        number
        for number in (episode_number(item) for item in episodes or [])
        if number and story_text(item_by_number(episodes, number) or {})
    }
    return [number for number in range(1, expected_count + 1) if number not in present]


def item_by_number(episodes: List[Dict[str, Any]], number: int) -> Optional[Dict[str, Any]]:
    for item in episodes or []:
        if episode_number(item) == number:
            return item
    return None


async def fetch_baike(
    crawler: BaikeCrawler,
    title: str,
    source: Dict[str, str],
) -> Dict[str, Any]:
    url = source.get("link") or ""
    if url:
        try:
            await crawler.page.goto(url, timeout=60000, wait_until="domcontentloaded")
            return await crawler.get_detail(url)
        except Exception as exc:
            if source.get("id") or re.search(r"/\d+(?:[?#].*)?$", url):
                raise
            Logger.warning(f"百度百科指定链接采集失败，将尝试标题搜索: {exc}")
    return await crawler.crawl(title)


def override_baike_source(
    sources: Dict[str, Dict[str, str]],
    item: Dict[str, Any],
) -> Dict[str, Dict[str, str]]:
    source_url = item.get("baikeUrl") or item.get("baike_url")
    source_id = item.get("baikeId") or item.get("baike_id")
    if not source_url and not source_id:
        return sources
    updated = dict(sources)
    current = dict(updated.get("baike", {}))
    if source_url:
        current["link"] = str(source_url)
    if source_id:
        current["id"] = str(source_id)
    current["name"] = current.get("name") or "百度百科"
    updated["baike"] = current
    return updated


async def fetch_tmdb_tv(
    tmdb: TMDBClient,
    imdb_id: str,
    expected_episode_count: int,
    merger: DataMerger,
) -> Dict[str, Any]:
    if not imdb_id:
        return {"episodes": [], "characters": [], "raw": {}}

    tv = await tmdb.search_tv_by_imdb(imdb_id)
    if not tv:
        return {"episodes": [], "characters": [], "raw": {"imdb_id": imdb_id, "source": "tmdb"}}

    tv_id = int(tv.get("id") or 0)
    if not tv_id:
        return {"episodes": [], "characters": [], "raw": {"imdb_id": imdb_id, "search": tv, "source": "tmdb"}}

    episodes_payload, credits = await asyncio.gather(
        tmdb.get_tv_episode_stories(tv_id, expected_count=expected_episode_count),
        tmdb.get_tv_credits(tv_id),
    )
    characters = merger._build_characters_from_tmdb_cast(credits.get("cast", []))
    raw = {
        "imdb_id": imdb_id,
        "search": tv,
        "episodes": episodes_payload,
        "credits": credits,
        "source": "tmdb",
    }
    return {
        "episodes": episodes_payload.get("episodes") or [],
        "characters": characters,
        "raw": raw,
    }


async def backfill_item(
    item: Dict[str, Any],
    douban: DoubanCrawler,
    baike: BaikeCrawler,
    merger: DataMerger,
    tmdb: TMDBClient,
    apply: bool = False,
) -> Dict[str, Any]:
    work_id = item["workId"]
    title = item["title"]
    schema_type = item["schemaType"]
    work = load_db_work(work_id)
    sources = source_map_from_work(work)
    sources = override_baike_source(sources, item)
    staging = load_staging(work_id)
    staging["schemaType"] = schema_type

    episode_count = staging.get("episodeCount") or staging.get("episode_count") or work.get("episode_count") or 0
    try:
        episode_count = int(episode_count or 0)
    except (TypeError, ValueError):
        episode_count = 0

    raw_dir = config.RAW_DIR / work_id
    raw_dir.mkdir(parents=True, exist_ok=True)

    douban_episodes: List[Dict[str, Any]] = []
    douban_characters: List[Dict[str, Any]] = []
    douban_id = sources.get("douban", {}).get("id", "")
    if douban_id:
        try:
            douban_episodes = await douban.crawl_episodes(douban_id, episode_count)
        except Exception as exc:
            Logger.warning(f"{title} 豆瓣分集剧情采集失败: {exc}")
        try:
            celebrities = await douban.crawl_celebrities(douban_id)
            douban_characters = merger._build_characters_from_cast(
                celebrities.get("cast", []),
                source="douban_celebrities",
            )
            write_json(raw_dir / "douban_enhancement.json", {
                "episodes": douban_episodes,
                "celebrities": celebrities,
            })
        except Exception as exc:
            Logger.warning(f"{title} 豆瓣角色采集失败: {exc}")

    baike_data: Dict[str, Any] = {}
    baike_episodes: List[Dict[str, Any]] = []
    baike_characters: List[Dict[str, Any]] = []
    try:
        baike_data = await fetch_baike(baike, title, sources.get("baike", {}))
        write_json(raw_dir / "baike_enhancement.json", baike_data)
        baike_episodes = baike_data.get("episodes_story") or []
        baike_characters = baike_data.get("characters") or []
        if not baike_characters:
            baike_characters = merger._build_characters_from_cast(
                baike_data.get("credits", {}).get("cast", []),
                source="baike_credits",
            )
    except Exception as exc:
        Logger.warning(f"{title} 百度百科增强采集失败: {exc}")

    tmdb_data: Dict[str, Any] = {"episodes": [], "characters": [], "raw": {}}
    imdb_id = sources.get("imdb", {}).get("id", "")
    if schema_type in (
        "documentary_series",
        "live_action_series",
        "animated_series",
        "tv_series",
        "anime_series",
        "documentary",
    ):
        try:
            tmdb_data = await fetch_tmdb_tv(tmdb, imdb_id, episode_count, merger)
            if tmdb_data.get("raw"):
                write_json(raw_dir / "tmdb_enhancement.json", tmdb_data["raw"])
        except Exception as exc:
            Logger.warning(f"{title} TMDB TV 增强采集失败: {exc}")

    existing_episodes = staging.get("episodesStory") or staging.get("episodes_story") or []
    existing_characters = staging.get("characters") or []
    tmdb_episodes = tmdb_data.get("episodes") or []
    tmdb_characters = tmdb_data.get("characters") or []
    merged_episodes = merge_episodes(existing_episodes, baike_episodes, douban_episodes, tmdb_episodes)
    merged_episodes, out_of_scope_episodes = split_out_of_scope_episodes(merged_episodes, episode_count)
    merged_characters = merge_characters(existing_characters, baike_characters, douban_characters, tmdb_characters)

    if merged_episodes:
        staging["episodesStory"] = merged_episodes
        staging.pop("episodes_story", None)
    if merged_characters:
        staging["characters"] = merged_characters

    write_json(config.STAGING_DIR / f"{work_id}.json", staging)

    check = precheck(work_id, staging, update_existing=True)
    apply_result = None
    if apply and not check["problems"]:
        apply_result = apply_import(staging)

    missing_episodes = missing_episode_numbers(merged_episodes, episode_count)
    return {
        "workId": work_id,
        "title": title,
        "schemaType": schema_type,
        "episodeCount": episode_count,
        "episodesStoryCount": len(merged_episodes),
        "missingEpisodes": missing_episodes,
        "outOfScopeEpisodes": [
            {
                "episode": episode_number(item),
                "title": item.get("title"),
                "source": item.get("source"),
            }
            for item in out_of_scope_episodes
        ],
        "charactersCount": len(merged_characters),
        "sources": {
            "doubanEpisodes": len(douban_episodes),
            "doubanCharacters": len(douban_characters),
            "baikeEpisodes": len(baike_episodes),
            "baikeCharacters": len(baike_characters),
            "tmdbEpisodes": len(tmdb_episodes),
            "tmdbCharacters": len(tmdb_characters),
        },
        "precheckProblems": check["problems"],
        "enhancementProblems": check["enhancement_problems"],
        "applied": bool(apply_result and apply_result.get("result", {}).get("success")),
        "applyResult": apply_result,
    }


async def run(
    queue_path: Path,
    apply: bool = False,
    work_id: Optional[str] = None,
    visible: bool = False,
) -> Dict[str, Any]:
    queue = read_json(queue_path, {})
    items = queue.get("items") or []
    if work_id:
        items = [item for item in items if item.get("workId") == work_id]

    config.HEADLESS = not visible
    config.SLOW_MO = 100 if visible else 0
    config.NONINTERACTIVE_BATCH = True

    douban = DoubanCrawler()
    await douban.init_browser()
    try:
        await douban.load_cookies()
        baike = BaikeCrawler(douban.page)
        merger = DataMerger()
        tmdb = TMDBClient()
        results = []
        for index, item in enumerate(items, start=1):
            Logger.info("=" * 80)
            Logger.info(f"[{index}/{len(items)}] 回填增强字段: {item.get('title')} ({item.get('workId')})")
            Logger.info("=" * 80)
            results.append(await backfill_item(item, douban, baike, merger, tmdb, apply=apply))

        report = {
            "queue": str(queue_path),
            "startedAt": datetime.now().isoformat(),
            "apply": apply,
            "total": len(items),
            "completed": sum(1 for item in results if not item["precheckProblems"]),
            "applied": sum(1 for item in results if item["applied"]),
            "items": results,
        }
        report_path = queue_path.parent / "enhancement-backfill-report.json"
        write_json(report_path, report)
        report["reportPath"] = str(report_path)
        return report
    finally:
        await douban.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="回填剧集 / 番剧增强字段")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE, help="增强队列 JSON")
    parser.add_argument("--apply", action="store_true", help="预检通过后正式更新主库")
    parser.add_argument("--work-id", help="只回填指定作品 ID")
    parser.add_argument("--visible", action="store_true", help="使用可见浏览器，便于人工处理验证页")
    args = parser.parse_args()

    report = asyncio.run(run(args.queue, apply=args.apply, work_id=args.work_id, visible=args.visible))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["completed"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
