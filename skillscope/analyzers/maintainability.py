"""
可维护性分析器 v2.0
增强：支持多语言、测试覆盖率估算、代码复杂度检测
"""
from __future__ import annotations
import re
from pathlib import Path

from skillscope.analyzers.base import BaseAnalyzer
from skillscope.core.models import SkillManifest, DimensionScore, Issue, Severity


class MaintainabilityAnalyzer(BaseAnalyzer):
    dimension = "X"
    name = "可维护性"
    weight = 0.15

    def analyze(self, manifest: SkillManifest) -> DimensionScore:
        issues = []
        evidence = []
        sub_scores = {}

        if self._should_run_rule("maint_documentation"):
            doc_score, doc_issues, doc_evidence = self._check_documentation(manifest)
            issues.extend(doc_issues)
            evidence.extend(doc_evidence)
            sub_scores["documentation"] = doc_score

        if self._should_run_rule("maint_tests"):
            test_score, test_issues, test_evidence = self._check_tests(manifest)
            issues.extend(test_issues)
            evidence.extend(test_evidence)
            sub_scores["tests"] = test_score

        if self._should_run_rule("maint_versioning"):
            version_score, version_issues, version_evidence = self._check_versioning(manifest)
            issues.extend(version_issues)
            evidence.extend(version_evidence)
            sub_scores["versioning"] = version_score

        if self._should_run_rule("maint_comments"):
            comment_score, comment_evidence = self._check_comments(manifest)
            evidence.extend(comment_evidence)
            sub_scores["comments"] = comment_score

        if self._should_run_rule("maint_complexity"):
            complexity_score, complexity_issues = self._check_complexity(manifest)
            issues.extend(complexity_issues)
            sub_scores["complexity"] = complexity_score

        score = int(
            0.25 * sub_scores.get("documentation", 100)
            + 0.25 * sub_scores.get("tests", 100)
            + 0.20 * sub_scores.get("versioning", 100)
            + 0.15 * sub_scores.get("comments", 100)
            + 0.15 * sub_scores.get("complexity", 100)
        )

        return DimensionScore(
            dimension=self.dimension, name=self.name, score=score,
            weight=self.weight, issues=issues, evidence=evidence,
            sub_scores=sub_scores,
        )

    def _check_documentation(self, manifest: SkillManifest):
        issues = []
        evidence = []
        score = 100

        if not manifest.readme_exists:
            score -= 40
            issues.append(Issue(
                dimension=self.dimension, severity=Severity.WARNING,
                category="缺少文档", location=manifest.source_path,
                message="未检测到 README.md，用户无法了解 Skill 的用途和使用方法",
                fix_hint="添加 README.md，包含：功能描述、安装方法、使用示例、配置说明",
                auto_fixable=False, rule_id="maint_documentation",
            ))
        else:
            evidence.append("检测到 README.md")
            readme_path = Path(manifest.source_path) / "README.md"
            if readme_path.exists():
                content = readme_path.read_text(encoding="utf-8", errors="ignore")
                if len(content) < 200:
                    score -= 15
                    evidence.append("README.md 内容过短，建议补充更多说明")
                if "install" not in content.lower() and "安装" not in content:
                    score -= 10
                    evidence.append("README 缺少安装说明")
                if "example" not in content.lower() and "示例" not in content:
                    score -= 10
                    evidence.append("README 缺少使用示例")
                if "license" not in content.lower() and "许可" not in content:
                    score -= 5
                    evidence.append("README 缺少许可证信息")

        return max(0, score), issues, evidence

    def _check_tests(self, manifest: SkillManifest):
        issues = []
        evidence = []
        score = 100

        has_test_dir = any("test" in f.lower() for f in manifest.files)
        has_test_file = any(re.search(r"test_.*\.py$|.*_test\.py$", f) for f in manifest.code_files)

        if not has_test_dir and not has_test_file:
            score -= 50
            issues.append(Issue(
                dimension=self.dimension, severity=Severity.WARNING,
                category="缺少测试", location=manifest.source_path,
                message="未检测到测试文件或测试目录",
                fix_hint="添加 tests/ 目录，为核心功能编写单元测试（推荐 pytest）",
                auto_fixable=False, rule_id="maint_tests",
            ))
        else:
            evidence.append("检测到测试相关文件")
            test_lines = 0
            code_lines = 0
            for f in manifest.files:
                path = Path(manifest.source_path) / f
                if not f.endswith(".py"):
                    continue
                try:
                    lines = len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
                except Exception:
                    continue
                if "test" in f.lower():
                    test_lines += lines
                else:
                    code_lines += lines
            if code_lines > 0:
                ratio = test_lines / code_lines
                evidence.append(f"测试代码 / 业务代码 行数比: {ratio:.2%}")
                if ratio < 0.1:
                    score -= 20
                    evidence.append("测试覆盖率可能不足（行数比 < 10%）")
                elif ratio >= 0.5:
                    evidence.append("测试覆盖良好")

        return max(0, score), issues, evidence

    def _check_versioning(self, manifest: SkillManifest):
        issues = []
        evidence = []
        score = 100

        has_changelog = any("change" in f.lower() for f in manifest.files)
        if not has_changelog:
            score -= 20
            evidence.append("未检测到 CHANGELOG，建议记录版本变更历史")
        else:
            evidence.append("检测到 CHANGELOG")

        if not manifest.gitignore_exists:
            score -= 15
            evidence.append("缺少 .gitignore，可能将敏感文件或临时文件提交到版本控制")
            issues.append(Issue(
                dimension=self.dimension, severity=Severity.WARNING,
                category="缺少 .gitignore", location=manifest.source_path,
                message="缺少 .gitignore，可能将敏感文件或临时文件提交到版本控制",
                fix_hint="添加标准 .gitignore 文件",
                auto_fixable=True, fix_safety="safe",
                rule_id="maint_versioning",
            ))
        else:
            evidence.append("检测到 .gitignore")

        has_version_file = any(f in manifest.files for f in ("__init__.py", "version.py", "VERSION"))
        if not has_version_file:
            score -= 10
            evidence.append("缺少版本号定义文件")

        return max(0, score), issues, evidence

    def _check_comments(self, manifest: SkillManifest):
        evidence = []
        score = 100
        total_docstrings = 0
        total_functions = 0

        for cf in manifest.code_files:
            if not cf.endswith(".py"):
                continue
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            funcs = re.findall(r"^\s*def\s+\w+\s*\(", content, re.MULTILINE)
            total_functions += len(funcs)
            docstrings = len(re.findall(r'\n\s*"""', content))
            total_docstrings += docstrings

        if total_functions > 0:
            ratio = total_docstrings / total_functions
            evidence.append(f"函数数量: {total_functions}, 含 docstring: {total_docstrings} ({ratio:.0%})")
            if ratio < 0.3:
                score -= 25
                evidence.append("函数 docstring 覆盖率较低，建议为核心函数添加文档字符串")
        else:
            evidence.append("未检测到 Python 函数定义")

        return max(0, score), evidence

    def _check_complexity(self, manifest: SkillManifest):
        """v2.0 新增：简单圈复杂度估算"""
        issues = []
        score = 100
        max_complexity = 0

        for cf in manifest.code_files:
            if not cf.endswith(".py"):
                continue
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            # 简单估算：if/for/while/except/and/or 数量
            branches = len(re.findall(r"\b(if|for|while|except|and|or)\b", content))
            if branches > 30:
                max_complexity = max(max_complexity, branches)
                issues.append(Issue(
                    dimension=self.dimension,
                    severity=Severity.INFO,
                    category="代码复杂度",
                    location=cf,
                    message=f"文件分支逻辑较多（约 {branches} 个），建议拆分函数",
                    fix_hint="提取子函数，降低单个函数的圈复杂度",
                    auto_fixable=False,
                    rule_id="maint_complexity",
                ))

        if max_complexity > 30:
            score -= min(len(issues) * 10, 40)

        return max(0, score), issues
