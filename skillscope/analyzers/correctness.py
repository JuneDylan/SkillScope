"""
正确性分析器 v2.0（新增维度）
评估：边界 Case 覆盖、输出一致性、幻觉风险、类型安全
"""
from __future__ import annotations

import re
from pathlib import Path

from skillscope.analyzers.base import BaseAnalyzer
from skillscope.core.models import DimensionScore, Issue, Severity, SkillManifest


class CorrectnessAnalyzer(BaseAnalyzer):
    dimension = "C"
    name = "正确性"
    weight = 0.15

    def analyze(self, manifest: SkillManifest) -> DimensionScore:
        issues = []
        evidence = []
        sub_scores = {}

        if self._should_run_rule("corr_error_handling"):
            eh_score, eh_issues, eh_evidence = self._check_error_handling(manifest)
            issues.extend(eh_issues)
            evidence.extend(eh_evidence)
            sub_scores["error_handling"] = eh_score

        if self._should_run_rule("corr_type_safety"):
            ts_score, ts_issues = self._check_type_safety(manifest)
            issues.extend(ts_issues)
            sub_scores["type_safety"] = ts_score

        if self._should_run_rule("corr_hallucination_risk"):
            hall_score, hall_evidence = self._check_hallucination_risk(manifest)
            evidence.extend(hall_evidence)
            sub_scores["hallucination_risk"] = hall_score

        if self._should_run_rule("corr_validation"):
            val_score, val_issues = self._check_output_validation(manifest)
            issues.extend(val_issues)
            sub_scores["validation"] = val_score

        if self._should_run_rule("corr_resource_cleanup"):
            rc_score, rc_issues = self._check_resource_cleanup(manifest)
            issues.extend(rc_issues)
            sub_scores["resource_cleanup"] = rc_score

        if self._should_run_rule("corr_input_sanitization"):
            is_score, is_issues = self._check_input_sanitization(manifest)
            issues.extend(is_issues)
            sub_scores["input_sanitization"] = is_score

        score = int(
            0.25 * sub_scores.get("error_handling", 100)
            + 0.20 * sub_scores.get("type_safety", 100)
            + 0.20 * sub_scores.get("hallucination_risk", 100)
            + 0.15 * sub_scores.get("validation", 100)
            + 0.10 * sub_scores.get("resource_cleanup", 100)
            + 0.10 * sub_scores.get("input_sanitization", 100)
        )

        return DimensionScore(
            dimension=self.dimension, name=self.name, score=score,
            weight=self.weight, issues=issues, evidence=evidence,
            sub_scores=sub_scores,
        )

    def _check_error_handling(self, manifest: SkillManifest):
        issues = []
        evidence = []
        score = 100
        total_files = 0
        files_with_try = 0

        for cf in manifest.code_files:
            if not cf.endswith(".py"):
                continue
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            total_files += 1
            if "try:" in content and "except" in content:
                files_with_try += 1
            # 检测裸 except
            if re.search(r"except\s*:", content):
                score -= 15
                issues.append(Issue(
                    dimension=self.dimension,
                    severity=Severity.WARNING,
                    category="异常处理",
                    location=cf,
                    message="检测到裸 except: 语句，可能捕获 KeyboardInterrupt 等系统异常",
                    fix_hint="使用 except Exception: 或更具体的异常类型",
                    auto_fixable=True,
                    fix_safety="safe",
                    rule_id="corr_error_handling",
                ))

        if total_files > 0:
            ratio = files_with_try / total_files
            evidence.append(f"含异常处理的文件比例: {ratio:.0%} ({files_with_try}/{total_files})")
            if ratio < 0.3:
                score -= 20
                evidence.append("异常处理覆盖率较低，建议为核心流程添加错误处理")

        return max(0, score), issues, evidence

    def _check_type_safety(self, manifest: SkillManifest):
        issues = []
        score = 100

        for cf in manifest.code_files:
            if not cf.endswith(".py"):
                continue
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            funcs = re.findall(r"^\s*def\s+\w+\s*\(([^)]*)\)", content, re.MULTILINE)
            # 检测函数定义后 200 字符内是否有 -> 返回类型注解
            typed_funcs = 0
            for match in re.finditer(r"^\s*def\s+\w+\s*\([^)]*\)(\s*->\s*[^:#]+)?", content, re.MULTILINE):
                if match.group(1):
                    typed_funcs += 1
                else:
                    # 检查参数中是否有类型注解
                    params = match.group(0).split("(", 1)[1].rsplit(")", 1)[0]
                    if ":" in params:
                        typed_funcs += 1
            if funcs and typed_funcs / len(funcs) < 0.3:
                score -= 15
                issues.append(Issue(
                    dimension=self.dimension,
                    severity=Severity.INFO,
                    category="类型安全",
                    location=cf,
                    message="函数缺少类型注解，降低代码可维护性和 IDE 支持",
                    fix_hint="添加 Python 类型注解（PEP 484），或使用 mypy 检查",
                    auto_fixable=False,
                    rule_id="corr_type_safety",
                ))

        return max(0, score), issues

    def _check_resource_cleanup(self, manifest: SkillManifest):
        issues = []
        score = 100
        found = False
        for cf in manifest.code_files:
            if not cf.endswith(".py"):
                continue
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if re.search(r"\bopen\s*\(", content) and "with open" not in content and "with " not in content:
                found = True
                issues.append(Issue(
                    dimension=self.dimension,
                    severity=Severity.INFO,
                    category="资源泄露",
                    location=cf,
                    message="检测到文件操作未使用 with 语句，可能导致资源泄露",
                    fix_hint="使用 with open(...) as f: 替代 f = open(...)",
                    auto_fixable=False,
                    rule_id="corr_resource_cleanup",
                ))
        if found:
            score = max(0, 100 - len(issues) * 15)
        return score, issues

    def _check_input_sanitization(self, manifest: SkillManifest):
        issues = []
        score = 100
        found = False
        for cf in manifest.code_files:
            if not cf.endswith(".py"):
                continue
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            has_user_input = bool(re.search(r"(?:input\(|sys\.argv|request\.|os\.environ|argparse)", content))
            has_sanitization = bool(re.search(r"(?:sanitize|escape|validate|strip|encode|quote|filter)", content))
            if has_user_input and not has_sanitization:
                found = True
                issues.append(Issue(
                    dimension=self.dimension,
                    severity=Severity.WARNING,
                    category="输入净化",
                    location=cf,
                    message="接收用户输入但未检测到输入净化逻辑",
                    fix_hint="对用户输入进行验证、转义或净化处理，防止注入攻击",
                    auto_fixable=False,
                    rule_id="corr_input_sanitization",
                ))
        if found:
            score = max(0, 100 - len(issues) * 15)
        return score, issues

    def _check_hallucination_risk(self, manifest: SkillManifest):
        evidence = []
        score = 100

        # 检测 Prompt 中是否要求模型"编造"或"猜测"
        for pf in manifest.prompt_files:
            path = Path(manifest.source_path) / pf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            risky_patterns = [
                r"(?i)(编造|捏造|make up|fabricate)",
                r"(?i)(猜测|推测|guess|speculate)",
                r"(?i)(如果没有.*就.*假设)",
            ]
            hits = sum(1 for p in risky_patterns if re.search(p, content))
            if hits > 0:
                score -= 25
                evidence.append(f"{pf}: Prompt 包含可能诱导幻觉的表述（编造/猜测）")
            else:
                evidence.append(f"{pf}: 未检测到明显的幻觉诱导表述")

        if not manifest.prompt_files:
            evidence.append("无 Prompt 文件可分析")

        return max(0, score), evidence

    def _check_output_validation(self, manifest: SkillManifest):
        issues = []
        score = 100

        for cf in manifest.code_files:
            if not cf.endswith(".py"):
                continue
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # 检测是否有输出验证逻辑
            has_validation = any(k in content for k in (
                "pydantic", "validate", "jsonschema", "schema", "validator"
            ))
            if not has_validation and "openai" in content:
                score -= 20
                issues.append(Issue(
                    dimension=self.dimension,
                    severity=Severity.WARNING,
                    category="输出验证",
                    location=cf,
                    message="未检测到 LLM 输出验证逻辑，存在结构化输出失败的风险",
                    fix_hint="使用 Pydantic 或 JSON Schema 验证 LLM 输出结构",
                    auto_fixable=False,
                    rule_id="corr_validation",
                ))

        return max(0, score), issues
