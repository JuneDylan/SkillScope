"""
性能分析器 v2.0（新增维度）
评估：Token 成本、API 调用效率、延迟热点
"""
from __future__ import annotations
import re
from pathlib import Path

from skillscope.analyzers.base import BaseAnalyzer
from skillscope.core.models import SkillManifest, DimensionScore, Issue, Severity


class PerformanceAnalyzer(BaseAnalyzer):
    dimension = "F"
    name = "性能"
    weight = 0.15

    def analyze(self, manifest: SkillManifest) -> DimensionScore:
        issues = []
        evidence = []
        sub_scores = {}

        if self._should_run_rule("perf_token_cost"):
            cost_score, cost_evidence = self._check_token_cost(manifest)
            evidence.extend(cost_evidence)
            sub_scores["token_cost"] = cost_score

        if self._should_run_rule("perf_api_efficiency"):
            api_score, api_issues, api_evidence = self._check_api_efficiency(manifest)
            issues.extend(api_issues)
            evidence.extend(api_evidence)
            sub_scores["api_efficiency"] = api_score

        if self._should_run_rule("perf_latency"):
            latency_score, latency_issues = self._check_latency(manifest)
            issues.extend(latency_issues)
            sub_scores["latency"] = latency_score

        if self._should_run_rule("perf_streaming"):
            stream_score, stream_issues = self._check_streaming(manifest)
            issues.extend(stream_issues)
            sub_scores["streaming"] = stream_score

        score = int(
            0.35 * sub_scores.get("token_cost", 100)
            + 0.30 * sub_scores.get("api_efficiency", 100)
            + 0.20 * sub_scores.get("latency", 100)
            + 0.15 * sub_scores.get("streaming", 100)
        )

        return DimensionScore(
            dimension=self.dimension, name=self.name, score=score,
            weight=self.weight, issues=issues, evidence=evidence,
            sub_scores=sub_scores,
        )

    def _check_token_cost(self, manifest: SkillManifest) -> tuple[int, list[str]]:
        evidence = []
        score = 100
        total_tokens = manifest.estimated_total_tokens

        if total_tokens == 0:
            evidence.append("无法估算 Token 成本（未找到可分析内容）")
            return 70, evidence

        evidence.append(f"项目估算总 Token 数: ~{total_tokens}")

        # 粗略成本估算（以 GPT-4 价格为例）
        estimated_cost_usd = (total_tokens / 1000) * 0.03
        evidence.append(f"单次调用估算成本: ~${estimated_cost_usd:.4f} USD (GPT-4 标准)")

        if total_tokens > 16000:
            score = 30
            evidence.append("Token 消耗极高，单次调用可能超出常见模型上下文限制")
        elif total_tokens > 8000:
            score = 50
            evidence.append("Token 消耗高，建议优化 Prompt 长度或拆分任务")
        elif total_tokens > 4000:
            score = 75
            evidence.append("Token 消耗中等，仍有优化空间")
        else:
            evidence.append("Token 消耗在合理范围内")

        return score, evidence

    def _check_api_efficiency(self, manifest: SkillManifest) -> tuple[int, list[Issue], list[str]]:
        issues = []
        evidence = []
        score = 100

        # 检测重复 API 调用模式
        for cf in manifest.code_files:
            if not cf.endswith(".py"):
                continue
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            # 检测循环内的 API 调用（逐行分析，避免灾难性回溯）
            lines = content.splitlines()
            in_loop = False
            loop_indent = -1
            found_loop_api = False
            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                current_indent = len(line) - len(line.lstrip())
                if re.match(r"^(for|while)\s+.+:", stripped):
                    in_loop = True
                    loop_indent = current_indent
                    continue
                if in_loop:
                    if current_indent <= loop_indent and stripped:
                        in_loop = False
                    elif any(k in line for k in ("openai", "anthropic", "chat.completions", ".invoke(")):
                        found_loop_api = True
                        break
            if found_loop_api:
                score -= 30
                issues.append(Issue(
                    dimension=self.dimension,
                    severity=Severity.WARNING,
                    category="低效API调用",
                    location=cf,
                    message="检测到循环内调用 LLM API，可能导致成本急剧上升",
                    fix_hint="考虑批量处理或使用缓存减少 API 调用次数",
                    auto_fixable=False,
                    rule_id="perf_api_efficiency",
                ))

            # 检测缺乏缓存
            if "cache" not in content.lower() and "@lru_cache" not in content:
                # 宽松判断：如果文件有 API 调用但没有缓存相关代码
                if any(k in content for k in ("openai", "anthropic", "completions")):
                    score -= 10
                    evidence.append(f"{cf} 中未检测到缓存机制，建议为重复查询添加缓存")

        return max(0, score), issues, evidence

    def _check_streaming(self, manifest: SkillManifest):
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
            has_api_call = bool(re.search(r"(?:chat\.completions|messages\.create|\.invoke\()", content))
            has_streaming = bool(re.search(r"stream\s*=\s*True", content))
            if has_api_call and not has_streaming:
                found = True
                issues.append(Issue(
                    dimension=self.dimension,
                    severity=Severity.INFO,
                    category="流式输出",
                    location=cf,
                    message="LLM API 调用未启用流式输出，长回复场景下用户体验较差",
                    fix_hint="设置 stream=True 并逐块处理响应，提升首字延迟体验",
                    auto_fixable=False,
                    rule_id="perf_streaming",
                ))
        if found:
            score = max(0, 100 - len(issues) * 10)
        return score, issues

    def _check_latency(self, manifest: SkillManifest) -> tuple[int, list[Issue]]:
        issues = []
        score = 100

        # 检测同步阻塞调用
        for cf in manifest.code_files:
            if not cf.endswith(".py"):
                continue
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            if "asyncio" not in content and "async def" not in content:
                if any(k in content for k in ("openai", "anthropic", "requests.post")):
                    score -= 15
                    issues.append(Issue(
                        dimension=self.dimension,
                        severity=Severity.INFO,
                        category="同步阻塞",
                        location=cf,
                        message="检测到同步 API 调用，建议使用异步模式提升并发性能",
                        fix_hint="使用 asyncio 和异步客户端（如 openai.AsyncOpenAI）",
                        auto_fixable=False,
                        rule_id="perf_latency",
                    ))

        return max(0, score), issues
