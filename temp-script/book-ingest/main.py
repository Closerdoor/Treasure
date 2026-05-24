# -*- coding: utf-8 -*-
"""
书籍数据多源爬取工具 - 主入口

命令结构：
  python main.py --crawl <source> --book <douban_id>   爬取指定数据源
  python main.py --crawl all --book <douban_id>         爬取所有数据源
  python main.py --merge --book <book_id>               合并数据
  python main.py --merge --all                          合并所有
  python main.py --download --book <book_id>            下载封面
  python main.py --download --all                       下载所有封面
  python main.py --import --book <book_id>              入库单本
  python main.py --import --all                         入库所有
  python main.py --full --book <douban_id>              一键全流程
"""
import asyncio
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict

import config
from utils import Logger, generate_book_id
from progress import ProgressManager
from merger import DataMerger
from import_staging import apply_import, load_staging, precheck


AVAILABLE_SOURCES = ["douban", "openlibrary", "baike", "wikipedia", "goodreads", "dangdang", "qidian"]


async def crawl_source(source: str, douban_id: str, title: str, book_id: str):
    """爬取单个数据源"""
    merger = DataMerger()

    if source == "douban":
        from sources.douban_crawl import DoubanCrawler
        crawler = DoubanCrawler()
        try:
            await crawler.init_browser()
            await crawler.ensure_login()
            data = await crawler.crawl(douban_id, title)
            if data:
                merger.save_raw_data(book_id, "douban", data)
                Logger.success(f"豆瓣爬取完成: {title}")
            else:
                Logger.error(f"豆瓣爬取失败: {title}")
        finally:
            await crawler.close()

    elif source == "openlibrary":
        from sources.openlibrary_crawl import OpenLibraryCrawler
        crawler = OpenLibraryCrawler()
        try:
            isbn = _get_isbn_from_raw(book_id)
            if isbn:
                data = await crawler.crawl(isbn)
                if data:
                    merger.save_raw_data(book_id, "openlibrary", data)
                    Logger.success(f"OpenLibrary 爬取完成: {title}")
                else:
                    Logger.warning(f"OpenLibrary 未找到: {title}")
            else:
                Logger.warning(f"无 ISBN，跳过 OpenLibrary: {title}")
        finally:
            await crawler.close()

    elif source == "baike":
        from sources.baike_crawl import BaikeCrawler
        crawler = BaikeCrawler()
        try:
            data = await crawler.crawl(title)
            if data:
                merger.save_raw_data(book_id, "baike", data)
                Logger.success(f"百度百科爬取完成: {title}")
            else:
                Logger.warning(f"百度百科未找到: {title}")
        finally:
            await crawler.close()

    elif source == "wikipedia":
        from sources.wikipedia_crawl import WikipediaCrawler
        crawler = WikipediaCrawler()
        try:
            await crawler.init_browser()
            original_title = _get_original_title_from_raw(book_id)
            data = await crawler.crawl(title, original_title)
            if data:
                merger.save_raw_data(book_id, "wikipedia", data)
                Logger.success(f"维基百科爬取完成: {title}")
            else:
                Logger.warning(f"维基百科未找到: {title}")
        finally:
            await crawler.close()

    elif source == "goodreads":
        from sources.goodreads_crawl import GoodreadsCrawler
        crawler = GoodreadsCrawler()
        try:
            await crawler.init_browser()
            isbn = _get_isbn_from_raw(book_id)
            data = await crawler.crawl(isbn=isbn, title=title)
            if data:
                merger.save_raw_data(book_id, "goodreads", data)
                Logger.success(f"Goodreads 爬取完成: {title}")
            else:
                Logger.warning(f"Goodreads 未找到: {title}")
        finally:
            await crawler.close()

    elif source == "dangdang":
        from sources.dangdang_crawl import DangdangCrawler
        crawler = DangdangCrawler()
        try:
            await crawler.init_browser()
            isbn = _get_isbn_from_raw(book_id)
            data = await crawler.crawl(isbn=isbn, title=title)
            if data:
                merger.save_raw_data(book_id, "dangdang", data)
                Logger.success(f"当当网爬取完成: {title}")
            else:
                Logger.warning(f"当当网未找到: {title}")
        finally:
            await crawler.close()

    elif source == "qidian":
        from sources.qidian_crawl import QidianCrawler
        crawler = QidianCrawler()
        try:
            await crawler.init_browser()
            data = await crawler.crawl(title)
            if data:
                merger.save_raw_data(book_id, "qidian", data)
                Logger.success(f"起点中文网爬取完成: {title}")
            else:
                Logger.warning(f"起点中文网未找到: {title}")
        finally:
            await crawler.close()

    else:
        Logger.error(f"未知数据源: {source}")


def _get_isbn_from_raw(book_id: str) -> str:
    """从豆瓣 raw 数据中获取 ISBN"""
    raw_file = Path(config.OUTPUT_DIR) / "raw" / book_id / "douban.json"
    if raw_file.exists():
        try:
            data = json.loads(raw_file.read_text(encoding="utf-8"))
            return data.get("isbn", "")
        except Exception:
            pass
    return ""


def _get_original_title_from_raw(book_id: str) -> str:
    """从豆瓣 raw 数据中获取原名"""
    raw_file = Path(config.OUTPUT_DIR) / "raw" / book_id / "douban.json"
    if raw_file.exists():
        try:
            data = json.loads(raw_file.read_text(encoding="utf-8"))
            return data.get("title_original", "")
        except Exception:
            pass
    return ""


def _get_title_from_raw(book_id: str) -> str:
    """从豆瓣 raw 数据中获取书名"""
    raw_file = Path(config.OUTPUT_DIR) / "raw" / book_id / "douban.json"
    if raw_file.exists():
        try:
            data = json.loads(raw_file.read_text(encoding="utf-8"))
            return data.get("title", "")
        except Exception:
            pass
    return ""


def merge_book(book_id: str):
    """合并单本书的数据"""
    merger = DataMerger()
    raw_data = merger.load_raw_data(book_id)
    if not raw_data:
        Logger.warning(f"无 raw 数据: {book_id}")
        return

    merged = merger.merge(book_id, raw_data)
    merger.save_merged_data(book_id, merged)


def merge_all():
    """合并所有 staging 数据"""
    merger = DataMerger()
    staging_dir = merger.staging_dir
    raw_dir = merger.raw_dir

    book_ids = []
    if raw_dir.exists():
        for d in raw_dir.iterdir():
            if d.is_dir():
                book_ids.append(d.name)

    if not book_ids:
        Logger.warning("无 raw 数据可合并")
        return

    Logger.info(f"发现 {len(book_ids)} 本书待合并")

    for book_id in sorted(book_ids):
        merge_book(book_id)

    Logger.success(f"合并完成: {len(book_ids)} 本")


def sync_cover_assets_to_staging(book_id: str, downloaded: Dict[str, str]):
    """把实际下载成功的封面文件列表回写到 staging，避免合并阶段猜测文件名。"""
    if not downloaded:
        return

    staging_file = Path(config.OUTPUT_DIR) / "staging" / f"{book_id}.json"
    if not staging_file.exists():
        Logger.warning(f"staging 不存在，跳过封面回写: {staging_file}")
        return

    try:
        data = json.loads(staging_file.read_text(encoding="utf-8"))
    except Exception as e:
        Logger.warning(f"读取 staging 失败，跳过封面回写: {e}")
        return

    images = data.get("images") if isinstance(data.get("images"), dict) else {}
    filenames = sorted(downloaded.keys())
    main_cover = "cover-main.jpg" if "cover-main.jpg" in downloaded else filenames[0]

    images["cover"] = main_cover
    images["covers"] = {
        source: filename
        for filename, source in sorted(downloaded.items(), key=lambda item: item[0])
        if filename != main_cover
    }
    images["assetDir"] = book_id
    data["images"] = images

    staging_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    Logger.info(f"已同步封面资源到 staging: {staging_file}")


def _person_id_from_detail(detail: dict) -> str:
    douban_id = detail.get("douban_personage_id") or detail.get("douban_id")
    if douban_id:
        return f"p{douban_id}"
    raw_name = detail.get("name") or detail.get("name_en") or "unknown"
    safe_name = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fa5_-]+", "-", str(raw_name)).strip("-")
    return f"book-{safe_name or 'unknown'}"


async def download_author_avatars(book_id: str) -> Dict[str, str]:
    """下载 staging 中的作者头像，并把本地头像路径回写到 _meta.personDetails。"""
    from downloaders import AvatarDownloader

    staging_file = Path(config.OUTPUT_DIR) / "staging" / f"{book_id}.json"
    if not staging_file.exists():
        return {}

    data = json.loads(staging_file.read_text(encoding="utf-8"))
    meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
    person_details = meta.get("personDetails") or []
    if not person_details:
        return {}

    downloader = AvatarDownloader(Path(config.OUTPUT_DIR) / "assets" / book_id / "people")
    downloaded: Dict[str, str] = {}
    try:
        await downloader.init()
        for detail in person_details:
            if not isinstance(detail, dict) or not detail.get("avatar_url"):
                continue
            person_id = _person_id_from_detail(detail)
            filename = f"{person_id}-avatar.jpg"
            result = await downloader.download_avatar(
                person_id,
                detail["avatar_url"],
                source=detail.get("avatar_source", "douban"),
                filename=filename,
            )
            if result:
                local_path = f"people/{filename}"
                detail["personId"] = person_id
                detail["avatarPath"] = local_path
                downloaded[local_path] = detail.get("name", person_id)
    finally:
        await downloader.close()

    if downloaded:
        meta["personDetails"] = person_details
        data["_meta"] = meta
        staging_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        Logger.info(f"已同步作者头像资源到 staging: {staging_file}")

    return downloaded


async def download_covers(book_id: str):
    """下载单本书的封面和作者头像"""
    from downloaders import CoverDownloader

    merger = DataMerger()
    raw_data = merger.load_raw_data(book_id)
    if not raw_data:
        Logger.warning(f"无 raw 数据: {book_id}")
        return

    downloader = CoverDownloader()
    try:
        await downloader.init()
        result = await downloader.download_from_raw_data(book_id, raw_data)
        if result:
            sync_cover_assets_to_staging(book_id, result)
            Logger.success(f"封面下载完成: {book_id} ({len(result)} 张)")
        else:
            Logger.warning(f"无封面可下载: {book_id}")

        avatar_result = await download_author_avatars(book_id)
        if avatar_result:
            Logger.success(f"作者头像下载完成: {book_id} ({len(avatar_result)} 张)")
    finally:
        await downloader.close()


async def download_all_covers():
    """下载所有封面"""
    merger = DataMerger()
    raw_dir = merger.raw_dir

    book_ids = []
    if raw_dir.exists():
        for d in raw_dir.iterdir():
            if d.is_dir():
                book_ids.append(d.name)

    if not book_ids:
        Logger.warning("无 raw 数据")
        return

    Logger.info(f"发现 {len(book_ids)} 本书待下载封面")

    for book_id in sorted(book_ids):
        await download_covers(book_id)


def import_book(book_id: str, apply: bool = False, update_existing: bool = False):
    """预检并按需入库单本书。默认只预检，显式 apply 才写库。"""
    try:
        book_data = load_staging(book_id)
    except Exception as e:
        Logger.error(f"读取 staging 文件失败: {e}")
        return {"success": False, "error": str(e)}

    report = precheck(book_id, book_data, update_existing=update_existing)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if report["problems"]:
        Logger.error("预检未通过，已停止。")
        return {"success": False, "error": "precheck failed", "report": report}

    if not apply:
        Logger.info("预检通过。未传入 --apply，因此没有写入主数据库。")
        return {"success": True, "dry_run": True, "report": report}

    result = apply_import(book_data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result["result"]


def import_all(apply: bool = False, update_existing: bool = False):
    """预检并按需入库所有 staging 数据。默认只预检。"""
    staging_dir = Path(config.OUTPUT_DIR) / "staging"

    if not staging_dir.exists():
        Logger.warning("staging 目录不存在")
        return

    book_ids = sorted([f.stem for f in staging_dir.glob("*.json")])
    if not book_ids:
        Logger.warning("staging 目录下没有书籍数据")
        return

    Logger.info(f"发现 {len(book_ids)} 本书待入库")

    stats = {"total": len(book_ids), "success": 0, "failed": 0}

    for book_id in book_ids:
        if not apply:
            result = import_book(book_id, apply=False, update_existing=update_existing)
            if result.get("success"):
                stats["success"] += 1
            else:
                stats["failed"] += 1
        else:
            try:
                result = import_book(book_id, apply=True, update_existing=update_existing)
                if result.get("success"):
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
                    Logger.error(f"入库失败: {book_id} - {result.get('error')}")
            except Exception as e:
                stats["failed"] += 1
                Logger.error(f"处理失败: {book_id} - {e}")

    Logger.info("=" * 50)
    Logger.info(f"入库流程完成: 总数 {stats['total']}, 成功 {stats['success']}, 失败 {stats['failed']}")


async def full_pipeline(douban_id: str, title: str, apply: bool = False, update_existing: bool = False):
    """一键全流程：爬取 → 合并 → 下载封面 → 预检/按需入库"""
    progress = ProgressManager()
    progress.load()

    book_id = progress.get_book_id(douban_id)
    if not book_id:
        book_id = generate_book_id()
        progress.update_book_id(douban_id, book_id)

    Logger.info(f"{'='*60}")
    Logger.info(f"全流程: {title} ({douban_id}) → {book_id}")
    Logger.info(f"{'='*60}")

    # 步骤1: 爬取各数据源
    Logger.info("\n[1/4] 爬取各数据源...")
    for source in AVAILABLE_SOURCES:
        Logger.info(f"\n--- {source} ---")
        try:
            await crawl_source(source, douban_id, title, book_id)
        except Exception as e:
            Logger.error(f"{source} 爬取失败: {e}")

    # 步骤2: 合并数据
    Logger.info("\n[2/4] 合并数据...")
    merge_book(book_id)

    # 步骤3: 下载封面
    Logger.info("\n[3/4] 下载封面...")
    await download_covers(book_id)

    # 步骤4: 预检 / 按需入库
    Logger.info("\n[4/4] 入库预检...")
    import_book(book_id, apply=apply, update_existing=update_existing)

    progress.mark_basic_completed(douban_id)
    progress.mark_data_merged(douban_id)
    progress.update_status(douban_id, "completed")

    Logger.success(f"\n全流程完成: {title}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="书籍数据多源爬取工具")

    # 操作模式
    parser.add_argument("--crawl", nargs="?", const="all", default=None,
                        help="爬取指定数据源（douban/openlibrary/baike/wikipedia/goodreads/dangdang/qidian/all）")
    parser.add_argument("--merge", action="store_true", help="合并数据")
    parser.add_argument("--download", action="store_true", help="下载封面")
    parser.add_argument("--import", dest="import_db", action="store_true", help="入库数据库")
    parser.add_argument("--full", action="store_true", help="一键全流程")

    # 目标
    parser.add_argument("--book", help="豆瓣 ID 或书籍 ID")
    parser.add_argument("--title", help="书名（可选，用于搜索）")
    parser.add_argument("--all", action="store_true", help="处理所有")

    # 选项
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际入库")
    parser.add_argument("--apply", action="store_true", help="通过预检后正式写入 .local/treasure.db")
    parser.add_argument("--update-existing", action="store_true", help="刷新数据库中同 ID 的已有书籍")
    parser.add_argument("--batch", action="store_true", help="批量模式（使用 config.TEST_BOOKS）")

    args = parser.parse_args()

    # 确定书籍列表
    if args.batch:
        book_list = config.TEST_BOOKS
    elif args.book:
        book_list = [{"douban_id": args.book, "title": args.title or ""}]
    else:
        book_list = []

    async def run():
        if args.full:
            # 一键全流程
            if not book_list:
                book_list.extend(config.TEST_BOOKS)
            for book in book_list:
                await full_pipeline(
                    book["douban_id"],
                    book.get("title", ""),
                    apply=args.apply,
                    update_existing=args.update_existing,
                )

        elif args.crawl:
            # 爬取指定数据源
            source = args.crawl
            if source == "all":
                sources = AVAILABLE_SOURCES
            elif source in AVAILABLE_SOURCES:
                sources = [source]
            else:
                Logger.error(f"未知数据源: {source}")
                return

            if not book_list:
                Logger.error("请指定 --book <douban_id> 或 --batch")
                return

            progress = ProgressManager()
            progress.load()
            progress.init_books(book_list)

            for book in book_list:
                douban_id = book["douban_id"]
                title = book.get("title", "")
                book_id = progress.get_book_id(douban_id)
                if not book_id:
                    book_id = generate_book_id()
                    progress.update_book_id(douban_id, book_id)

                if not title and book_id:
                    title = _get_title_from_raw(book_id)
                if not title:
                    title = douban_id

                for src in sources:
                    try:
                        await crawl_source(src, douban_id, title, book_id)
                        progress.update_source_status(douban_id, src, "done")
                    except Exception as e:
                        Logger.error(f"{src} 爬取失败: {e}")
                        progress.update_source_status(douban_id, src, "error")

        elif args.merge:
            # 合并数据
            if args.all:
                merge_all()
            elif args.book:
                merge_book(args.book)
            else:
                Logger.error("请指定 --book <book_id> 或 --all")

        elif args.download:
            # 下载封面
            if args.all:
                await download_all_covers()
            elif args.book:
                await download_covers(args.book)
            else:
                Logger.error("请指定 --book <book_id> 或 --all")

        elif args.import_db:
            # 入库
            if args.all:
                import_all(apply=args.apply and not args.dry_run, update_existing=args.update_existing)
            elif args.book:
                import_book(args.book, apply=args.apply and not args.dry_run, update_existing=args.update_existing)
            else:
                Logger.error("请指定 --book <book_id> 或 --all")

        else:
            parser.print_help()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        Logger.warning("\n用户中断")
    except Exception as e:
        Logger.error(f"运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
