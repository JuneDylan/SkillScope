"""
安全修复器
处理：Secrets 替换、危险函数替换、.gitignore 生成
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Optional

from skillscope.fixers.base import BaseFixer
from skillscope.core.models import SkillManifest, Issue, FixPatch, FixSafety


GITIGNORE_TEMPLATE = """# SkillScope auto-generated .gitignore
__pycache__/
*.pyc
*.pyo
.env
.venv/
*.egg-info/
dist/
build/
.DS_Store
.idea/
.vscode/
*.log
"""


class SecurityFixer(BaseFixer):
    name = "security"
    supported_rules = [
        "sec_secrets",
        "sec_dangerous_functions",
        "sec_hardcoded_config",
        "maint_versioning",  # .gitignore
    ]

    def generate_patch(self, manifest: SkillManifest, issue: Issue) -> Optional[FixPatch]:
        if issue.rule_id == "sec_secrets":
            return self._fix_secret(manifest, issue)
        if issue.rule_id == "sec_dangerous_functions":
            return self._fix_dangerous_function(manifest, issue)
        if issue.rule_id == "sec_hardcoded_config":
            return self._fix_hardcoded_config(manifest, issue)
        if issue.category == "缺少 .gitignore":
            return self._fix_gitignore(manifest, issue)
        return None

    def _fix_secret(self, manifest: SkillManifest, issue: Issue) -> Optional[FixPatch]:
        loc = issue.location
        if ":" not in loc:
            return None
        file_path, line_str = loc.rsplit(":", 1)
        full_path = Path(manifest.source_path) / file_path
        if not full_path.exists():
            return None
        try:
            lines = full_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            line_idx = int(line_str) - 1
            if line_idx < 0 or line_idx >= len(lines):
                return None
            original = lines[line_idx]
            # 简单替换：将 api_key = "xxx" 替换为 api_key = os.environ.get("API_KEY", "")
            def _replace_secret(m: re.Match) -> str:
                var_name = m.group(1)
                if var_name.upper().endswith(("_API_KEY", "_KEY", "_SECRET", "_TOKEN")):
                    return f'{var_name} = os.environ.get("{var_name.upper()}", "")'
                return m.group(0)

            replacement = re.sub(
                r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*["\'][^"\']+["\']',
                _replace_secret,
                original,
            )
            if replacement == original:
                return None
            return FixPatch(
                file_path=file_path,
                original=original,
                replacement=replacement,
                description="将硬编码密钥替换为环境变量读取",
                safety=FixSafety.SAFE,
                issue_rule_id=issue.rule_id,
            )
        except Exception:
            return None

    def _fix_dangerous_function(self, manifest: SkillManifest, issue: Issue) -> Optional[FixPatch]:
        loc = issue.location
        if ":" not in loc:
            return None
        file_path, line_str = loc.rsplit(":", 1)
        full_path = Path(manifest.source_path) / file_path
        if not full_path.exists():
            return None
        try:
            lines = full_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            line_idx = int(line_str) - 1
            if line_idx < 0 or line_idx >= len(lines):
                return None
            original = lines[line_idx]
            replacement = original
            if "eval(" in original and "ast.literal_eval" not in original:
                replacement = replacement.replace("eval(", "ast.literal_eval(")
            elif "os.system(" in original:
                m = re.search(r"os\.system\((.+)\)", original)
                if m:
                    arg = m.group(1)
                    replacement = original.replace(
                        f"os.system({arg})",
                        f"subprocess.run({arg}, shell=True, check=True)",
                    )
            if replacement == original:
                return None
            return FixPatch(
                file_path=file_path,
                original=original,
                replacement=replacement,
                description="替换危险函数为安全替代方案",
                safety=FixSafety.SUGGESTED,
                issue_rule_id=issue.rule_id,
            )
        except Exception:
            return None

    def _fix_hardcoded_config(self, manifest: SkillManifest, issue: Issue) -> Optional[FixPatch]:
        # 与 secrets 修复类似，生成配置提取建议
        return None  # 暂不实现精确替换，避免破坏设计

    def _fix_gitignore(self, manifest: SkillManifest, issue: Issue) -> FixPatch:
        return FixPatch(
            file_path=".gitignore",
            original="",
            replacement=GITIGNORE_TEMPLATE,
            description="生成标准 .gitignore 文件",
            safety=FixSafety.SAFE,
            issue_rule_id=issue.rule_id,
        )
