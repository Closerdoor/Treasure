# -*- coding: utf-8 -*-
"""
Apply approved book-ingest staging records safely.

This script never discovers records by itself. It only imports IDs explicitly
listed in an approval JSON, one by one, through import_staging.py --apply.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import config
from utils import Logger


ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parents[1]


def load_approval(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    approved = data.get("approved")
    if not isinstance(approved, list) or not approved:
        raise ValueError("approval.approved 必须是非空数组")
    return data


def normalize_approved_ids(approved: List[Any]) -> List[str]:
    ids = []
    for item in approved:
        if isinstance(item, str):
            book_id = item.strip()
        elif isinstance(item, dict):
            book_id = str(item.get("bookId") or item.get("id") or "").strip()
        else:
            book_id = ""
        if not book_id:
            raise ValueError(f"approval.approved 包含无效项: {item!r}")
        ids.append(book_id)
    return sorted(dict.fromkeys(ids))


def run_command(args: List[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )


def import_one(book_id: str) -> Dict[str, Any]:
    precheck = run_command([sys.executable, "import_staging.py", "--book-id", book_id], ROOT)
    if precheck.returncode != 0:
        return {
            "bookId": book_id,
            "success": False,
            "stage": "precheck",
            "stdout": precheck.stdout,
            "stderr": precheck.stderr,
        }

    applied = run_command([sys.executable, "import_staging.py", "--book-id", book_id, "--apply"], ROOT)
    return {
        "bookId": book_id,
        "success": applied.returncode == 0,
        "stage": "apply",
        "stdout": applied.stdout,
        "stderr": applied.stderr,
    }


def export_generated() -> Dict[str, Any]:
    result = run_command(["node", "tools/db/export-generated.mjs"], REPO_ROOT)
    return {
        "success": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def build_site() -> Dict[str, Any]:
    result = run_command(["npm.cmd", "run", "build"], REPO_ROOT / "site")
    return {
        "success": result.returncode == 0,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="按 approval JSON 安全批量写入书籍 staging")
    parser.add_argument("--approval", required=True, help="approval JSON 路径，必须显式列出 approved bookId")
    parser.add_argument("--skip-export", action="store_true", help="写库后不导出 generated/assets")
    parser.add_argument("--build", action="store_true", help="导出后构建 Astro 站点")
    args = parser.parse_args()

    approval_path = Path(args.approval)
    if not approval_path.is_absolute():
        approval_path = (ROOT / approval_path).resolve()

    approval = load_approval(approval_path)
    approved_ids = normalize_approved_ids(approval["approved"])
    Logger.info(f"准备写入 {len(approved_ids)} 本: {', '.join(approved_ids)}")

    results = []
    for book_id in approved_ids:
        Logger.info(f"预检并写入: {book_id}")
        result = import_one(book_id)
        results.append(result)
        if not result["success"]:
            Logger.error(f"写入停止: {book_id} 在 {result['stage']} 阶段失败")
            break
        Logger.success(f"写入成功: {book_id}")

    success_count = sum(1 for item in results if item["success"])
    payload: Dict[str, Any] = {
        "approval": str(approval_path),
        "requested": len(approved_ids),
        "applied": success_count,
        "results": results,
    }

    if success_count == len(approved_ids) and not args.skip_export:
        Logger.info("导出 generated 与静态资源")
        payload["exportGenerated"] = export_generated()
        if not payload["exportGenerated"]["success"]:
            Logger.error("导出 generated 失败")
        elif args.build:
            Logger.info("构建 Astro 站点")
            payload["build"] = build_site()
            if not payload["build"]["success"]:
                Logger.error("Astro 构建失败")

    report_path = approval_path.with_name(f"{approval_path.stem}-apply-result.json")
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "requested": payload["requested"],
        "applied": payload["applied"],
        "report": str(report_path),
        "success": payload["applied"] == payload["requested"],
    }, ensure_ascii=False, indent=2))
    return 0 if payload["applied"] == payload["requested"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
