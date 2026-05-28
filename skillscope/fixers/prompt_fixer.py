"""
Prompt 修复器
处理：格式化规范化、重复内容去重、模糊词提示
"""
from __future__ import annotations

from pathlib import Path

from skillscope.core.models import FixPatch, FixSafety, Issue, SkillManifest
from skillscope.fixers.base import BaseFixer


class PromptFixer(BaseFixer):
    name = "prompt"
    supported_rules = ["prompt_clarity"]

    def generate_patch(self, manifest: SkillManifest, issue: Issue) -> FixPatch | None:
        if issue.rule_id == "prompt_clarity" and "模糊词汇" in issue.message:
            return self._fix_fuzzy_words(manifest, issue)
        return None

    def _fix_fuzzy_words(self, manifest: SkillManifest, issue: Issue) -> FixPatch | None:
        for pf in manifest.prompt_files:
            path = Path(manifest.source_path) / pf
            if not path.exists():
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if issue.message and any(w in content for w in ["可能", "大概", "尽量", "适当", "一些", "一定程度", "maybe", "probably"]):
                return FixPatch(
                    file_path=pf,
                    original=content,
                    replacement=content + "\n<!-- SkillScope 提示: 建议将模糊词汇替换为量化指标，如'适当' -> '控制在 100-200 字之间' -->\n",
                    description="Prompt 模糊词改进建议",
                    safety=FixSafety.SUGGESTED,
                    issue_rule_id=issue.rule_id,
                )
        return None
