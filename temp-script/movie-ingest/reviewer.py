# -*- coding: utf-8 -*-
"""
审阅文件生成模块
"""
from pathlib import Path
from typing import Dict, List, Any

from utils import Logger


class Reviewer:
    """审阅文件生成器"""
    
    def __init__(self, output_dir: str = "data"):
        self.output_dir = Path(output_dir)
        
    def generate_review_file(self, work_id: str, title: str, conflicts: List[Dict]) -> str:
        """
        生成审阅文件
        
        Args:
            work_id: 作品 ID
            title: 电影标题
            conflicts: 冲突列表
            
        Returns:
            文件路径
        """
        Logger.info(f"正在生成审阅文件: {work_id}")
        
        filepath = self.output_dir / work_id / "review.md"
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        lines = [
            f"# 数据审阅：{title}",
            "",
            "## 基本信息",
            "",
            f"- 作品 ID：{work_id}",
            "",
            "---",
            "",
            "## 冲突字段",
            ""
        ]
        
        for i, conflict in enumerate(conflicts, 1):
            field = conflict.get("field", "")
            sources = conflict.get("sources", {})
            
            lines.append(f"### {i}. {self._get_field_label(field)}")
            lines.append("")
            lines.append("| 来源 | 值 |")
            lines.append("|------|-----|")
            
            for source, value in sources.items():
                lines.append(f"| {source} | {value} |")
            
            lines.append("")
            lines.append("**请选择**：")
            
            for source, value in sources.items():
                lines.append(f"- [ ] {source}：{value}")
            
            lines.append(f"- [ ] 自定义：______")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        lines.extend([
            "## 确认状态",
            "",
            "- [ ] 已审阅",
            "- [ ] 已确认",
            "",
            "审阅人：______",
            "审阅时间：______"
        ])
        
        content = "\n".join(lines)
        filepath.write_text(content, encoding="utf-8")
        
        Logger.success(f"审阅文件已生成: {filepath}")
        return str(filepath)
        
    def _get_field_label(self, field: str) -> str:
        """获取字段中文标签"""
        labels = {
            "runtime_minutes": "片长",
            "year": "年份",
            "title": "标题",
            "original_title": "原名",
            "synopsis_text": "简介",
            "story_text": "剧情详解"
        }
        return labels.get(field, field)
        
    def check_confirmation(self, work_id: str) -> bool:
        """
        检查是否已确认
        
        Args:
            work_id: 作品 ID
            
        Returns:
            是否已确认
        """
        filepath = self.output_dir / work_id / "review.md"
        
        if not filepath.exists():
            return True  # 没有审阅文件，视为已确认
            
        content = filepath.read_text(encoding="utf-8")
        
        # 检查是否有确认标记
        if "- [x] 已确认" in content or "- [X] 已确认" in content:
            return True
            
        return False
        
    def has_review_file(self, work_id: str) -> bool:
        """检查是否存在审阅文件"""
        filepath = self.output_dir / work_id / "review.md"
        return filepath.exists()