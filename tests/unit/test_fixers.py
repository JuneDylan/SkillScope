"""
修复器单元测试
"""
from __future__ import annotations
import pytest
from pathlib import Path

from skillscope.core.models import SkillManifest, SkillType, Issue, Severity, FixSafety
from skillscope.fixers.manager import FixManager
from skillscope.fixers.security_fixer import SecurityFixer


class TestSecurityFixer:
    def test_fix_secret(self, tmp_path: Path):
        code_file = tmp_path / "main.py"
        code_file.write_text('openai_api_key = "sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567"\n')
        manifest = SkillManifest(
            name="test", source_path=str(tmp_path),
            skill_type=SkillType.TOOL, files=["main.py"], code_files=["main.py"]
        )
        issue = Issue(
            dimension="S", severity=Severity.CRITICAL,
            category="Secrets泄露", location="main.py:1",
            message="检测到 OpenAI API Key",
            auto_fixable=True, fix_safety=FixSafety.SAFE,
            rule_id="sec_secrets",
        )
        fixer = SecurityFixer()
        patch = fixer.generate_patch(manifest, issue)
        assert patch is not None
        assert "os.environ.get" in patch.replacement

    def test_fix_gitignore(self, tmp_path: Path):
        manifest = SkillManifest(
            name="test", source_path=str(tmp_path),
            skill_type=SkillType.TOOL, files=[]
        )
        issue = Issue(
            dimension="X", severity=Severity.WARNING,
            category="缺少 .gitignore", location=str(tmp_path),
            message="缺少 .gitignore",
            auto_fixable=True, fix_safety=FixSafety.SAFE,
            rule_id="maint_versioning",
        )
        fixer = SecurityFixer()
        patch = fixer.generate_patch(manifest, issue)
        assert patch is not None
        assert patch.file_path == ".gitignore"
        assert "__pycache__" in patch.replacement


class TestFixManager:
    def test_generate_safe_patches_only(self, tmp_path: Path):
        # 需要创建实际文件，因为 fixer 会检查文件存在性
        (tmp_path / "main.py").write_text('api_key = "secret123"\n')
        manifest = SkillManifest(
            name="test", source_path=str(tmp_path),
            skill_type=SkillType.TOOL, files=["main.py"], code_files=["main.py"]
        )
        issues = [
            Issue(
                dimension="S", severity=Severity.CRITICAL,
                category="Secrets泄露", location="main.py:1",
                message="Key", auto_fixable=True,
                fix_safety=FixSafety.SAFE, rule_id="sec_secrets",
            ),
            Issue(
                dimension="P", severity=Severity.INFO,
                category="模糊指令", location="prompt.md",
                message="模糊", auto_fixable=True,
                fix_safety=FixSafety.SUGGESTED, rule_id="prompt_clarity",
            ),
        ]
        manager = FixManager()
        patches = manager.generate_patches(manifest, issues, safety="safe")
        assert len(patches) == 1  # 只返回 safe 级别的

    def test_apply_patches(self, tmp_path: Path):
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "main.py").write_text("old_line\n")
        manifest = SkillManifest(
            name="test", source_path=str(skill_dir),
            skill_type=SkillType.TOOL, files=["main.py"], code_files=["main.py"]
        )
        from skillscope.core.models import FixPatch
        patches = [
            FixPatch(
                file_path="main.py",
                original="old_line",
                replacement="new_line",
                description="test",
            )
        ]
        manager = FixManager()
        stats = manager.apply_patches(manifest, patches)
        assert stats["applied"] == 1
        content = (skill_dir / "main.py").read_text()
        assert "new_line" in content
