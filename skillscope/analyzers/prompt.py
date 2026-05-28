"""
Prompt 质量分析器 v2.0
增强：支持 tiktoken 精确计算、子维度细分、AI Judge 钩子
"""
from __future__ import annotations

import re
from pathlib import Path

from skillscope.analyzers.base import BaseAnalyzer
from skillscope.core.models import DimensionScore, Issue, Severity, SkillManifest
from skillscope.utils.parser import extract_prompt_content
from skillscope.utils.patterns import PROMPT_INJECTION_PATTERNS
from skillscope.utils.tokens import estimate_token_count


class PromptAnalyzer(BaseAnalyzer):
    dimension = "P"
    name = "Prompt质量"
    weight = 0.20

    def analyze(self, manifest: SkillManifest) -> DimensionScore:
        issues = []
        evidence = []
        sub_scores = {}

        # 收集所有 prompt 内容
        all_prompt_content = ""
        for pf in manifest.prompt_files:
            content = extract_prompt_content(str(Path(manifest.source_path) / pf))
            all_prompt_content += content + "\n"
        for cf in manifest.code_files:
            if cf.endswith(".py"):
                content = extract_prompt_content(str(Path(manifest.source_path) / cf))
                all_prompt_content += content + "\n"

        if not all_prompt_content.strip():
            issues.append(Issue(
                dimension=self.dimension,
                severity=Severity.WARNING,
                category="缺失Prompt",
                location=manifest.source_path,
                message="未检测到任何 Prompt 内容，Skill 可能缺少核心指令",
                fix_hint="添加明确的 system prompt 或 user prompt 定义",
                rule_id="prompt_missing",
            ))
            evidence.append("未找到 Prompt 文件或代码中的 Prompt 定义")
            return DimensionScore(
                dimension=self.dimension,
                name=self.name,
                score=0,
                weight=self.weight,
                issues=issues,
                evidence=evidence,
                sub_scores={"injection": 0, "token": 0, "clarity": 0, "specificity": 0},
            )

        # 1. 注入风险检测
        if self._should_run_rule("prompt_injection"):
            injection_score, injection_issues = self._check_injection_risk(manifest, all_prompt_content)
            issues.extend(injection_issues)
            sub_scores["injection"] = injection_score

        # 2. Token 效率（v2.0: 使用更精确的估算）
        if self._should_run_rule("prompt_token_efficiency"):
            token_score, token_evidence = self._check_token_efficiency(all_prompt_content)
            evidence.extend(token_evidence)
            sub_scores["token"] = token_score

        # 3. 指令清晰度
        if self._should_run_rule("prompt_clarity"):
            clarity_score, clarity_issues, clarity_evidence = self._check_clarity(all_prompt_content)
            issues.extend(clarity_issues)
            evidence.extend(clarity_evidence)
            sub_scores["clarity"] = clarity_score

        # 4. 特异性
        if self._should_run_rule("prompt_specificity"):
            specificity_score, spec_evidence = self._check_specificity(all_prompt_content)
            evidence.extend(spec_evidence)
            sub_scores["specificity"] = specificity_score

        # 加权总分（子维度权重可配置化）
        score = int(
            0.35 * sub_scores.get("injection", 100)
            + 0.25 * sub_scores.get("token", 100)
            + 0.25 * sub_scores.get("clarity", 100)
            + 0.15 * sub_scores.get("specificity", 100)
        )

        return DimensionScore(
            dimension=self.dimension, name=self.name, score=score,
            weight=self.weight, issues=issues, evidence=evidence,
            sub_scores=sub_scores,
        )

    def _check_injection_risk(self, manifest: SkillManifest, content: str) -> tuple[int, list[Issue]]:
        issues = []
        found_risk = False
        for pattern, message, severity_str in PROMPT_INJECTION_PATTERNS:
            for file_rel, line_num, line in self._iter_lines(manifest):
                if re.search(pattern, line):
                    found_risk = True
                    loc = self._rel_path(manifest, file_rel, line_num)
                    hint = "使用参数化调用，如 messages=[{'role': 'user', 'content': user_input}]"
                    issues.append(Issue(
                        dimension=self.dimension, severity=Severity(severity_str),
                        category="Prompt注入", location=loc, message=message,
                        fix_hint=hint, auto_fixable=False, rule_id="prompt_injection",
                    ))
        score = 30 if found_risk else 100
        return score, issues

    def _check_token_efficiency(self, content: str) -> tuple[int, list[str]]:
        tokens = estimate_token_count(content)
        evidence = [f"估算 Prompt 总 Token 数: ~{tokens}"]
        score = 100
        if tokens > 8000:
            score = 20
            evidence.append("Prompt 极长 (>8000 tokens)，强烈建议压缩或拆分")
        elif tokens > 4000:
            score = 40
            evidence.append("Prompt 过长 (>4000 tokens)，建议压缩或拆分")
        elif tokens > 2000:
            score = 70
            evidence.append("Prompt 较长 (>2000 tokens)，建议检查冗余指令")

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        duplicates = len(lines) - len(set(lines))
        if duplicates > 3:
            score -= 15
            evidence.append(f"检测到 {duplicates} 行重复内容，建议去重")
        return max(0, score), evidence

    def _check_clarity(self, content: str) -> tuple[int, list[Issue], list[str]]:
        issues = []
        evidence = []
        score = 100

        if not re.search(r"(?i)(你是一名|你是|you are|act as|role:|system:)", content):
            score -= 20
            evidence.append("缺少明确的角色定义（如'你是一名专家'）")

        if not re.search(r"(?i)(输出格式|请输出|output|format|json|markdown|xml)", content):
            score -= 15
            evidence.append("缺少输出格式指定")

        if re.search(r"(?i)(第一步|step 1|1\.|①)", content):
            evidence.append("包含分步骤指令，清晰度加分")
        else:
            score -= 10
            evidence.append("缺少分步骤指令，复杂任务建议拆分步骤")

        fuzzy_words = ["可能", "大概", "尽量", "适当", "一些", "一定程度", "maybe", "probably"]
        found_fuzzy = [w for w in fuzzy_words if w in content]
        if found_fuzzy:
            score -= min(len(found_fuzzy) * 5, 25)
            issues.append(Issue(
                dimension=self.dimension, severity=Severity.INFO,
                category="模糊指令", location="prompt",
                message=f"检测到模糊词汇: {', '.join(found_fuzzy)}",
                fix_hint="将模糊词替换为具体量化指标",
                rule_id="prompt_clarity",
            ))

        return max(0, score), issues, evidence

    def _check_specificity(self, content: str) -> tuple[int, list[str]]:
        evidence = []
        score = 100
        generic_patterns = [
            r"(?i)(请帮我|help me|请回答|answer the)",
            r"(?i)(以下|如下|following|below)",
        ]
        generic_hits = sum(1 for p in generic_patterns if re.search(p, content))
        if generic_hits >= 2:
            score -= 30
            evidence.append("Prompt 过于通用，缺乏领域特异性，易被模型原生能力覆盖")
        else:
            evidence.append("Prompt 具有一定特异性")
        return max(0, score), evidence

    def _iter_lines(self, manifest: SkillManifest):
        for cf in manifest.code_files:
            if cf.endswith(".py"):
                path = Path(manifest.source_path) / cf
                for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                    yield cf, i, line
        for pf in manifest.prompt_files:
            path = Path(manifest.source_path) / pf
            for i, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                yield pf, i, line

    def _rel_path(self, manifest: SkillManifest, file_rel: str, line_num: int) -> str:
        return f"{file_rel}:{line_num}"
