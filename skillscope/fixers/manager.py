"""
修复管理器
协调多个修复器，按安全级别过滤，生成修复补丁
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional

from skillscope.core.models import SkillManifest, Issue, FixPatch, FixSafety
from skillscope.fixers.base import BaseFixer
from skillscope.fixers.security_fixer import SecurityFixer
from skillscope.fixers.prompt_fixer import PromptFixer


class FixManager:
    def __init__(self):
        self.fixers: list[BaseFixer] = [
            SecurityFixer(),
            PromptFixer(),
        ]

    def register(self, fixer: BaseFixer) -> None:
        self.fixers.append(fixer)

    def generate_patches(
        self,
        manifest: SkillManifest,
        issues: list[Issue],
        safety: str = "safe",
    ) -> list[FixPatch]:
        """
        safety levels:
          - none: 不生成任何修复
          - safe: 只生成 SAFE 级别的修复
          - suggested: 生成 SAFE + SUGGESTED
          - all: 全部（含 DANGEROUS，需人工确认）
        """
        if safety == "none":
            return []

        allowed = {FixSafety.SAFE}
        if safety in ("suggested", "all"):
            allowed.add(FixSafety.SUGGESTED)
        if safety == "all":
            allowed.add(FixSafety.DANGEROUS)

        patches = []
        seen = set()
        for issue in issues:
            if not issue.auto_fixable:
                continue
            if issue.fix_safety not in allowed:
                continue
            for fixer in self.fixers:
                if fixer.can_fix(issue):
                    patch = fixer.generate_patch(manifest, issue)
                    if patch:
                        dedup_key = (patch.file_path, patch.original)
                        if dedup_key not in seen:
                            patches.append(patch)
                            seen.add(dedup_key)
                    break
        return patches

    def apply_patches(self, manifest: SkillManifest, patches: list[FixPatch]) -> dict[str, int]:
        """将补丁应用到文件系统，返回统计信息"""
        stats = {"applied": 0, "failed": 0}
        for patch in patches:
            path = Path(manifest.source_path) / patch.file_path
            try:
                if patch.original == "":
                    # 新建文件
                    path.write_text(patch.replacement, encoding="utf-8")
                else:
                    content = path.read_text(encoding="utf-8")
                    content = content.replace(patch.original, patch.replacement, 1)
                    path.write_text(content, encoding="utf-8")
                stats["applied"] += 1
            except Exception:
                stats["failed"] += 1
        return stats
