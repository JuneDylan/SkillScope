"""
安全扫描分析器 v2.0
增强：AST 语义分析 + 正则快速筛选、依赖实时检查框架、MCP 权限模型
"""
from __future__ import annotations

import re
from pathlib import Path

from skillscope.analyzers.base import BaseAnalyzer
from skillscope.core.models import DimensionScore, Issue, Severity, SkillManifest, SkillType
from skillscope.utils.patterns import (
    DANGEROUS_FUNCTIONS,
    INSECURE_NETWORK_PATTERNS,
    LOGGING_SENSITIVE_PATTERNS,
    SECRET_PATTERNS,
)


class SecurityScanner(BaseAnalyzer):
    dimension = "S"
    name = "安全性"
    weight = 0.25

    def analyze(self, manifest: SkillManifest) -> DimensionScore:
        issues = []
        evidence = []
        sub_scores = {}

        # 1. Secrets 泄露扫描
        if self._should_run_rule("sec_secrets"):
            secrets_score, secret_issues = self._scan_secrets(manifest)
            issues.extend(secret_issues)
            sub_scores["secrets"] = secrets_score

        # 2. 危险函数检测（v2.0: AST 增强）
        if self._should_run_rule("sec_dangerous_functions"):
            danger_score, danger_issues = self._scan_dangerous_functions(manifest)
            issues.extend(danger_issues)
            sub_scores["dangerous"] = danger_score

        # 3. 依赖检查（v2.0: 框架支持接入 OSV/Snyk）
        if self._should_run_rule("sec_dependencies"):
            dep_score, dep_issues, dep_evidence = self._scan_dependencies(manifest)
            issues.extend(dep_issues)
            evidence.extend(dep_evidence)
            sub_scores["dependencies"] = dep_score

        # 4. MCP 权限检查
        if self._should_run_rule("sec_mcp_permissions"):
            mcp_score, mcp_issues = self._scan_mcp_permissions(manifest)
            issues.extend(mcp_issues)
            sub_scores["mcp"] = mcp_score

        # 5. 硬编码配置检测
        if self._should_run_rule("sec_hardcoded_config"):
            config_score, config_issues = self._scan_hardcoded_configs(manifest)
            issues.extend(config_issues)
            sub_scores["hardcoded_config"] = config_score

        # 6. 不安全网络通信
        if self._should_run_rule("sec_insecure_network"):
            net_score, net_issues = self._scan_insecure_network(manifest)
            issues.extend(net_issues)
            sub_scores["insecure_network"] = net_score

        # 7. 敏感信息日志泄露
        if self._should_run_rule("sec_logging_sensitive"):
            log_score, log_issues = self._scan_logging_sensitive(manifest)
            issues.extend(log_issues)
            sub_scores["logging_sensitive"] = log_score

        score = int(
            0.25 * sub_scores.get("secrets", 100)
            + 0.20 * sub_scores.get("dangerous", 100)
            + 0.15 * sub_scores.get("dependencies", 100)
            + 0.10 * sub_scores.get("mcp", 100)
            + 0.10 * sub_scores.get("hardcoded_config", 100)
            + 0.10 * sub_scores.get("insecure_network", 100)
            + 0.10 * sub_scores.get("logging_sensitive", 100)
        )

        return DimensionScore(
            dimension=self.dimension, name=self.name, score=score,
            weight=self.weight, issues=issues, evidence=evidence,
            sub_scores=sub_scores,
        )

    def _scan_secrets(self, manifest: SkillManifest) -> tuple[int, list[Issue]]:
        issues = []
        found_any = False
        for cf in manifest.code_files + manifest.config_files:
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for secret_name, info in SECRET_PATTERNS.items():
                for match in re.finditer(info["pattern"], content):
                    found_any = True
                    line_num = content[:match.start()].count("\n") + 1
                    issues.append(Issue(
                        dimension=self.dimension,
                        severity=Severity(info["severity"]),
                        category="Secrets泄露",
                        location=f"{cf}:{line_num}",
                        message=f"检测到可能的 {secret_name}: {match.group(0)[:20]}...",
                        fix_hint="将敏感信息移至环境变量或密钥管理服务，使用 os.environ.get() 读取",
                        auto_fixable=True,
                        fix_safety="safe",
                        rule_id="sec_secrets",
                    ))
        if not found_any:
            return 100, []
        critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
        warning_count = sum(1 for i in issues if i.severity == Severity.WARNING)
        score = max(0, 100 - critical_count * 30 - warning_count * 15)
        return score, issues

    def _scan_dangerous_functions(self, manifest: SkillManifest) -> tuple[int, list[Issue]]:
        issues = []
        found_any = False
        for cf in manifest.code_files:
            if not cf.endswith(".py"):
                continue
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            # v2.0: 结合 AST 数据流简单追踪（此处保留正则入口，AST 增强在 parser 中）
            for pattern, message in DANGEROUS_FUNCTIONS:
                for match in re.finditer(pattern, content):
                    found_any = True
                    line_num = content[:match.start()].count("\n") + 1
                    issues.append(Issue(
                        dimension=self.dimension,
                        severity=Severity.WARNING,
                        category="危险函数",
                        location=f"{cf}:{line_num}",
                        message=message,
                        fix_hint="使用安全的替代方案，如 json.loads 替代 eval，shlex.quote 包裹系统命令",
                        auto_fixable=True,
                        fix_safety="suggested",
                        rule_id="sec_dangerous_functions",
                    ))
        if not found_any:
            return 100, []
        score = max(0, 100 - len(issues) * 20)
        return score, issues

    def _scan_dependencies(self, manifest: SkillManifest) -> tuple[int, list[Issue], list[str]]:
        issues = []
        evidence = []
        if not manifest.dependency_file:
            evidence.append("未检测到依赖管理文件 (requirements.txt / package.json / pyproject.toml)")
            return 70, [], evidence

        dep_path = Path(manifest.source_path) / manifest.dependency_file
        try:
            content = dep_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            evidence.append("依赖文件无法读取")
            return 70, [], evidence

        evidence.append(f"检测到依赖文件: {manifest.dependency_file}")

        # v2.0: 保留已知问题依赖作为快速筛选，同时提示可接入 OSV API
        risky_packages = {
            "requests": ("<2.32.0", "存在证书验证绕过漏洞 CVE-2018-18074"),
            "urllib3": ("<1.26.19", "存在 CRLF 注入漏洞 CVE-2019-11324"),
            "flask": ("<2.3.0", "存在多个已知安全问题，建议升级"),
            "django": ("<4.2.0", "存在多个高危漏洞，建议升级"),
            "jinja2": ("<3.1.4", "存在 SSTI 漏洞 CVE-2019-10906"),
        }

        found_risky = False
        for pkg, (_bad_version, reason) in risky_packages.items():
            if pkg in content.lower():
                found_risky = True
                issues.append(Issue(
                    dimension=self.dimension,
                    severity=Severity.WARNING,
                    category="依赖风险",
                    location=manifest.dependency_file,
                    message=f"检测到 {pkg}，{reason}",
                    fix_hint=f"运行 pip install {pkg} --upgrade 升级到最新版本，或使用 skillscope scan --check-osv 接入实时漏洞库",
                    auto_fixable=False,
                    rule_id="sec_dependencies",
                ))

        if not found_risky:
            evidence.append("未检测到已知的高风险依赖（建议接入 OSV 实时查询）")

        score = 100 if not found_risky else max(0, 100 - len(issues) * 15)
        return score, issues, evidence

    def _scan_mcp_permissions(self, manifest: SkillManifest) -> tuple[int, list[Issue]]:
        issues = []
        if manifest.skill_type != SkillType.MCP:
            return 100, issues

        for cf in manifest.config_files:
            if cf.endswith(".json"):
                path = Path(manifest.source_path) / cf
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore").lower()
                except Exception:
                    continue
                if "filesystem" in content and "read" in content and "write" in content:
                    issues.append(Issue(
                        dimension=self.dimension,
                        severity=Severity.WARNING,
                        category="权限过度",
                        location=cf,
                        message="MCP Server 申请了文件系统读写权限，可能存在过度授权",
                        fix_hint="遵循最小权限原则，仅申请必要的权限范围",
                        auto_fixable=False,
                        rule_id="sec_mcp_permissions",
                    ))
        score = 100 if not issues else max(0, 100 - len(issues) * 25)
        return score, issues

    def _scan_hardcoded_configs(self, manifest: SkillManifest) -> tuple[int, list[Issue]]:
        """v2.0 新增：检测硬编码的模型配置"""
        issues = []
        found = False
        patterns = [
            (r'(?:model|temperature|max_tokens|top_p)\s*=\s*[\'"]?[^\'"\s\)]+', "硬编码模型参数"),
            (r'(?:base_url|api_url|endpoint)\s*=\s*[\'"]https?://[^\'"]+[\'"]', "硬编码 API 端点"),
        ]
        for cf in manifest.code_files:
            if not cf.endswith(".py"):
                continue
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for pattern, msg in patterns:
                for match in re.finditer(pattern, content):
                    found = True
                    line_num = content[:match.start()].count("\n") + 1
                    issues.append(Issue(
                        dimension=self.dimension,
                        severity=Severity.INFO,
                        category="硬编码配置",
                        location=f"{cf}:{line_num}",
                        message=f"{msg}: {match.group(0)[:40]}",
                        fix_hint="将配置提取到配置文件或环境变量中",
                        auto_fixable=True,
                        fix_safety="safe",
                        rule_id="sec_hardcoded_config",
                    ))
        score = 100 if not found else max(0, 100 - len(issues) * 10)
        return score, issues

    def _scan_insecure_network(self, manifest: SkillManifest) -> tuple[int, list[Issue]]:
        issues = []
        found = False
        for cf in manifest.code_files:
            if not cf.endswith(".py"):
                continue
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for pattern, message in INSECURE_NETWORK_PATTERNS:
                for match in re.finditer(pattern, content):
                    found = True
                    line_num = content[:match.start()].count("\n") + 1
                    issues.append(Issue(
                        dimension=self.dimension,
                        severity=Severity.WARNING,
                        category="不安全网络通信",
                        location=f"{cf}:{line_num}",
                        message=message,
                        fix_hint="使用 HTTPS 替代 HTTP，启用 SSL 证书验证",
                        auto_fixable=False,
                        rule_id="sec_insecure_network",
                    ))
        score = 100 if not found else max(0, 100 - len(issues) * 20)
        return score, issues

    def _scan_logging_sensitive(self, manifest: SkillManifest) -> tuple[int, list[Issue]]:
        issues = []
        found = False
        for cf in manifest.code_files:
            if not cf.endswith(".py"):
                continue
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for pattern, message in LOGGING_SENSITIVE_PATTERNS:
                for match in re.finditer(pattern, content):
                    found = True
                    line_num = content[:match.start()].count("\n") + 1
                    issues.append(Issue(
                        dimension=self.dimension,
                        severity=Severity.WARNING,
                        category="敏感信息日志泄露",
                        location=f"{cf}:{line_num}",
                        message=message,
                        fix_hint="在日志和 print 中过滤敏感字段，使用 *** 遮蔽",
                        auto_fixable=False,
                        rule_id="sec_logging_sensitive",
                    ))
        score = 100 if not found else max(0, 100 - len(issues) * 20)
        return score, issues
