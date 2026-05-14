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
import sys
from pathlib import Path

import config
from utils import Logger, generate_book_id
from progress import ProgressManager
from merger import DataMerger
from database import BookDB


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
            await crawler.init_browser()
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


async def download_covers(book_id: str):
    """下载单本书的封面"""
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
            Logger.success(f"封面下载完成: {book_id} ({len(result)} 张)")
        else:
            Logger.warning(f"无封面可下载: {book_id}")
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


def import_book(book_id: str, dry_run: bool = False):
    """入库单本书"""
    staging_dir = Path(config.OUTPUT_DIR) / "staging"
    staging_file = staging_dir / f"{book_id}.json"

    if not staging_file.exists():
        Logger.error(f"staging 文件不存在: {staging_file}")
        return

    try:
        book_data = json.loads(staging_file.read_text(encoding="utf-8"))
    except Exception as e:
        Logger.error(f"读取 staging 文件失败: {e}")
        return

    Logger.info(f"准备入库: {book_data.get('title', book_id)}")

    if dry_run:
        Logger.info("[DRY RUN] 预览模式，不实际入库")
        meta = book_data.get("_meta", {})
        Logger.info(f"  书籍 ID: {book_id}")
        Logger.info(f"  书名: {book_data.get('title')}")
        Logger.info(f"  作者: {meta.get('authors', [])}")
        Logger.info(f"  译者: {meta.get('translators', [])}")
        Logger.info(f"  标签: {meta.get('tags', [])}")
        return

    db = BookDB()
    result = db.import_book(book_data)
    db.close()

    if result.get("success"):
        Logger.success(f"入库成功: {book_data.get('title')} ({book_id})")
        Logger.info(f"  人物: {result.get('persons', 0)}")
        Logger.info(f"  标签: {result.get('categories', 0)}")
    else:
        Logger.error(f"入库失败: {result.get('error')}")


def import_all(dry_run: bool = False):
    """入库所有 staging 数据"""
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
        if dry_run:
            import_book(book_id, dry_run=True)
            stats["success"] += 1
        else:
            staging_file = staging_dir / f"{book_id}.json"
            try:
                book_data = json.loads(staging_file.read_text(encoding="utf-8"))
                db = BookDB()
                result = db.import_book(book_data)
                db.close()

                if result.get("success"):
                    stats["success"] += 1
                else:
                    stats["failed"] += 1
                    Logger.error(f"入库失败: {book_id} - {result.get('error')}")
            except Exception as e:
                stats["failed"] += 1
                Logger.error(f"处理失败: {book_id} - {e}")

    Logger.info("=" * 50)
    Logger.info(f"入库完成: 总数 {stats['total']}, 成功 {stats['success']}, 失败 {stats['failed']}")


async def full_pipeline(douban_id: str, title: str):
    """一键全流程：爬取 → 合并 → 下载封面 → 入库"""
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

    # 步骤4: 入库
    Logger.info("\n[4/4] 入库...")
    import_book(book_id)

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
    parser.add_argument("--batch", action="store_true", help="批量模式（使用 config.TEST_BOOKS）")

    args = parser.parse_args()

    # 确定书籍列表
    if args.batch:
        book_list = config.TEST_BOOKS
    elif args.book:
        book_list = [{"douban_id": args.book, "title": args.title or args.book}]
    else:
        book_list = []

    async def run():
        if args.full:
            # 一键全流程
            if not book_list:
                book_list.extend(config.TEST_BOOKS)
            for book in book_list:
                await full_pipeline(book["douban_id"], book.get("title", ""))

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
                import_all(dry_run=args.dry_run)
            elif args.book:
                import_book(args.book, dry_run=args.dry_run)
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