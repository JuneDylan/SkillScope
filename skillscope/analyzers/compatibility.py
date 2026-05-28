"""
兼容性分析器 v2.0（新增维度）
评估：模型 API 锁定、协议版本、多平台适配
"""
from __future__ import annotations

import re
from pathlib import Path

from skillscope.analyzers.base import BaseAnalyzer
from skillscope.core.models import DimensionScore, Issue, Severity, SkillManifest
from skillscope.utils.patterns import VENDOR_SPECIFIC_APIS


class CompatibilityAnalyzer(BaseAnalyzer):
    dimension = "M"
    name = "兼容性"
    weight = 0.10

    def analyze(self, manifest: SkillManifest) -> DimensionScore:
        issues = []
        evidence = []
        sub_scores = {}

        if self._should_run_rule("compat_vendor_lock"):
            vl_score, vl_issues, vl_evidence = self._check_vendor_lock(manifest)
            issues.extend(vl_issues)
            evidence.extend(vl_evidence)
            sub_scores["vendor_lock"] = vl_score

        if self._should_run_rule("compat_protocol"):
            proto_score, proto_issues = self._check_protocol_version(manifest)
            issues.extend(proto_issues)
            sub_scores["protocol"] = proto_score

        if self._should_run_rule("compat_platform"):
            plat_score, plat_evidence = self._check_platform_compat(manifest)
            evidence.extend(plat_evidence)
            sub_scores["platform"] = plat_score

        if self._should_run_rule("compat_encoding"):
            enc_score, enc_issues = self._check_encoding_compat(manifest)
            issues.extend(enc_issues)
            sub_scores["encoding"] = enc_score

        score = int(
            0.35 * sub_scores.get("vendor_lock", 100)
            + 0.30 * sub_scores.get("protocol", 100)
            + 0.20 * sub_scores.get("platform", 100)
            + 0.15 * sub_scores.get("encoding", 100)
        )

        return DimensionScore(
            dimension=self.dimension, name=self.name, score=score,
            weight=self.weight, issues=issues, evidence=evidence,
            sub_scores=sub_scores,
        )

    def _check_vendor_lock(self, manifest: SkillManifest):
        issues = []
        evidence = []
        score = 100
        vendor_apis_found = []

        for cf in manifest.code_files:
            if not cf.endswith(".py"):
                continue
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for pattern, message in VENDOR_SPECIFIC_APIS:
                if re.search(pattern, content):
                    vendor_apis_found.append((cf, message))

        if vendor_apis_found:
            score -= min(len(vendor_apis_found) * 15, 60)
            for cf, msg in vendor_apis_found:
                issues.append(Issue(
                    dimension=self.dimension,
                    severity=Severity.INFO,
                    category="厂商锁定",
                    location=cf,
                    message=msg,
                    fix_hint="使用 LiteLLM 或抽象层封装模型调用，降低迁移成本",
                    auto_fixable=False,
                    rule_id="compat_vendor_lock",
                ))
            evidence.append(f"检测到 {len(vendor_apis_found)} 处厂商特有 API 使用")
        else:
            evidence.append("未检测到明显的厂商锁定 API")

        return max(0, score), issues, evidence

    def _check_protocol_version(self, manifest: SkillManifest):
        issues = []
        score = 100

        # 检测 MCP 协议版本声明
        if manifest.skill_type == "mcp":
            has_version_decl = False
            for cf in manifest.config_files:
                if cf.endswith(".json"):
                    path = Path(manifest.source_path) / cf
                    try:
                        content = path.read_text(encoding="utf-8", errors="ignore")
                    except Exception:
                        continue
                    if '"version"' in content or "'version'" in content:
                        has_version_decl = True
            if not has_version_decl:
                score -= 25
                issues.append(Issue(
                    dimension=self.dimension,
                    severity=Severity.INFO,
                    category="协议版本",
                    location=manifest.source_path,
                    message="MCP 配置缺少版本声明，可能导致客户端兼容性问题",
                    fix_hint="在配置中明确声明 protocolVersion 或 schemaVersion",
                    auto_fixable=False,
                    rule_id="compat_protocol",
                ))

        return max(0, score), issues

    def _check_platform_compat(self, manifest: SkillManifest):
        evidence = []
        score = 100

        # 检测平台特定代码
        for cf in manifest.code_files:
            if not cf.endswith(".py"):
                continue
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            if "win32" in content or "sys.platform" in content:
                score -= 10
                evidence.append(f"{cf}: 包含平台特定代码，建议验证跨平台兼容性")

        if score == 100:
            evidence.append("未检测到明显的平台锁定代码")

        return max(0, score), evidence

    def _check_encoding_compat(self, manifest: SkillManifest):
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
            if re.search(r"\.read\(\)", content) and "encoding=" not in content:
                found = True
                issues.append(Issue(
                    dimension=self.dimension,
                    severity=Severity.INFO,
                    category="编码兼容",
                    location=cf,
                    message="文件读取未显式指定编码，跨平台可能出现编码问题",
                    fix_hint="使用 open(f, encoding='utf-8') 或 Path.read_text(encoding='utf-8')",
                    auto_fixable=False,
                    rule_id="compat_encoding",
                ))
        if found:
            score = max(0, 100 - len(issues) * 10)
        return score, issues
