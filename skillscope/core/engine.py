"""
SkillScope 混合分析引擎 v2.0
支持：确定性分析 + AI Judge、并行执行、缓存、修复编排
"""
from __future__ import annotations

import contextlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from skillscope.core.config import load_config
from skillscope.core.loader import load_skill
from skillscope.core.models import (
    AuditResult,
    DimensionScore,
    FixPatch,
    Issue,
    Severity,
    SkillManifest,
    SkillScopeConfig,
)
from skillscope.core.registry import registry
from skillscope.fixers.manager import FixManager
from skillscope.utils.cache import FileCache


class SkillScopeEngine:
    def __init__(self, config: SkillScopeConfig | None = None):
        self.config = config or load_config()
        self.fix_manager = FixManager()
        self.cache = FileCache() if self.config.cache_enabled else None
        registry.auto_discover("skillscope.analyzers")
        self._analyzers: list = []
        self._ai_judge_metas: list = []

    def audit(
        self,
        path: str,
        apply_fixes: bool = False,
        fix_safety_level: str = "safe",
    ) -> AuditResult:
        start_ts = time.perf_counter()

        manifest = load_skill(path, max_workers=self.config.max_workers)

        enabled_dims = [
            d for d, cfg in self.config.dimensions.items() if cfg.enabled
        ] if self.config.dimensions else None
        dim_configs = {
            d: cfg.model_dump() for d, cfg in (self.config.dimensions or {}).items()
        }
        self._analyzers = registry.build_analyzers(
            enabled_dimensions=enabled_dims,
            config=dim_configs,
        )

        dimension_scores = {}
        all_issues = []

        if self.config.parallel and len(self._analyzers) > 1:
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as pool:
                futures = {
                    pool.submit(self._run_analyzer, a, manifest): a.dimension
                    for a in self._analyzers
                }
                for future in as_completed(futures):
                    dim = futures[future]
                    try:
                        score = future.result()
                        dimension_scores[dim] = score
                        all_issues.extend(score.issues)
                    except Exception as e:
                        dimension_scores[dim] = self._error_score(dim, str(e))
        else:
            for analyzer in self._analyzers:
                try:
                    score = self._run_analyzer(analyzer, manifest)
                    dimension_scores[analyzer.dimension] = score
                    all_issues.extend(score.issues)
                except Exception as e:
                    dimension_scores[analyzer.dimension] = self._error_score(
                        analyzer.dimension, str(e)
                    )

        if self.config.ai_enabled:
            self._run_ai_judges(manifest, dimension_scores, all_issues)

        overall = self._compute_overall(dimension_scores)

        patches: list[FixPatch] = []
        if apply_fixes or fix_safety_level != "none":
            effective_safety = fix_safety_level if fix_safety_level != "none" else "safe"
            patches = self.fix_manager.generate_patches(
                manifest, all_issues, safety=effective_safety
            )
            if apply_fixes and patches:
                self.fix_manager.apply_patches(manifest, patches)

        summary = self._generate_summary(manifest, overall, dimension_scores, all_issues)

        duration_ms = int((time.perf_counter() - start_ts) * 1000)

        return AuditResult(
            skill_name=manifest.name,
            skill_source=manifest.source_path,
            skill_type=manifest.skill_type,
            overall_score=overall,
            dimension_scores=dimension_scores,
            issues=all_issues,
            patches=patches,
            summary=summary,
            audit_timestamp=datetime.now(timezone.utc).isoformat(),
            config_snapshot=self.config.model_dump(),
            scan_duration_ms=duration_ms,
            files_scanned=len(manifest.files),
        )

    def _run_analyzer(self, analyzer, manifest: SkillManifest) -> DimensionScore:
        if self.cache:
            cached = self.cache.get(manifest.source_path, analyzer.dimension)
            if cached:
                return DimensionScore(**cached)
        score = analyzer.analyze(manifest)
        if self.cache:
            self.cache.set(manifest.source_path, analyzer.dimension, score.model_dump())
        return score

    def _run_ai_judges(
        self,
        manifest: SkillManifest,
        dimension_scores: dict[str, DimensionScore],
        all_issues: list[Issue],
    ) -> None:
        from skillscope.ai_judges import HallucinationJudge, PromptQualityJudge

        prompt_content = self._collect_prompt_content(manifest)
        code_content = self._collect_code_content(manifest)
        context = {
            "prompt_content": prompt_content,
            "code_content": code_content,
        }

        judges = []
        if "P" in dimension_scores:
            judges.append(PromptQualityJudge(model=self.config.ai_model))
        if "C" in dimension_scores:
            judges.append(HallucinationJudge(model=self.config.ai_model))

        for judge in judges:
            result, meta = judge.evaluate(context)
            self._ai_judge_metas.append(meta)
            if not result:
                continue

            dim = judge.dimension
            if dim not in dimension_scores:
                continue

            existing = dimension_scores[dim]
            merged_sub = dict(existing.sub_scores)

            if dim == "P":
                for sub_key in ("clarity", "specificity", "injection_risk"):
                    if sub_key in result and isinstance(result[sub_key], dict):
                        ai_score = result[sub_key].get("score")
                        if isinstance(ai_score, (int, float)):
                            det_score = existing.sub_scores.get(sub_key, 100)
                            merged_sub[f"{sub_key}_ai"] = int(ai_score)
                            merged_sub[sub_key] = int(0.6 * det_score + 0.4 * ai_score)

                        reason = result[sub_key].get("reason", "")
                        if reason:
                            all_issues.append(Issue(
                                dimension=dim,
                                severity=Severity.INFO,
                                category=f"AI评估-{sub_key}",
                                location="prompt",
                                message=f"AI Judge: {reason}",
                                fix_hint="",
                                auto_fixable=False,
                                source="ai_judge",
                            ))

                vuln_lines = result.get("injection_risk", {}).get("vulnerable_lines", [])
                if vuln_lines:
                    for line in vuln_lines[:3]:
                        all_issues.append(Issue(
                            dimension=dim,
                            severity=Severity.WARNING,
                            category="AI评估-注入风险",
                            location="prompt",
                            message=f"AI Judge 发现潜在注入风险: {line[:100]}",
                            fix_hint="使用参数化调用，避免用户输入直接拼接到 Prompt",
                            auto_fixable=False,
                            source="ai_judge",
                        ))

            elif dim == "C":
                hall = result.get("hallucination_risk", {})
                if isinstance(hall, dict):
                    ai_score = hall.get("score")
                    if isinstance(ai_score, (int, float)):
                        det_score = existing.sub_scores.get("hallucination_risk", 100)
                        merged_sub["hallucination_risk_ai"] = int(ai_score)
                        merged_sub["hallucination_risk"] = int(0.6 * det_score + 0.4 * ai_score)

                    reason = hall.get("reason", "")
                    if reason:
                        all_issues.append(Issue(
                            dimension=dim,
                            severity=Severity.INFO,
                            category="AI评估-幻觉风险",
                            location="prompt",
                            message=f"AI Judge: {reason}",
                            fix_hint="",
                            auto_fixable=False,
                            source="ai_judge",
                        ))

                for pattern in result.get("risk_patterns", [])[:3]:
                    all_issues.append(Issue(
                        dimension=dim,
                        severity=Severity.WARNING,
                        category="AI评估-幻觉模式",
                        location="prompt",
                        message=f"AI Judge 发现幻觉诱导模式: {pattern[:100]}",
                        fix_hint="添加事实性约束或不确定声明",
                        auto_fixable=False,
                        source="ai_judge",
                    ))

            new_score = int(
                sum(merged_sub.values()) / len(merged_sub)
            ) if merged_sub else existing.score

            dimension_scores[dim] = DimensionScore(
                dimension=existing.dimension,
                name=existing.name,
                score=new_score,
                weight=existing.weight,
                issues=existing.issues,
                evidence=existing.evidence,
                sub_scores=merged_sub,
            )

    @staticmethod
    def _collect_prompt_content(manifest: SkillManifest) -> str:
        parts = []
        for pf in manifest.prompt_files:
            path = Path(manifest.source_path) / pf
            with contextlib.suppress(Exception):
                parts.append(path.read_text(encoding="utf-8", errors="ignore"))
        return "\n".join(parts)

    @staticmethod
    def _collect_code_content(manifest: SkillManifest) -> str:
        parts = []
        for cf in manifest.code_files[:5]:
            path = Path(manifest.source_path) / cf
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                parts.append(content[:3000])
            except Exception:
                pass
        return "\n".join(parts)

    def _compute_overall(self, dimension_scores: dict[str, DimensionScore]) -> int:
        weighted_sum = 0.0
        weight_sum = 0.0
        for _dim, ds in dimension_scores.items():
            weighted_sum += ds.score * ds.weight
            weight_sum += ds.weight
        if weight_sum == 0:
            return 0
        return int(weighted_sum / weight_sum)

    @staticmethod
    def _generate_summary(
        manifest,
        overall: int,
        dimension_scores: dict[str, DimensionScore],
        issues: list,
    ) -> str:
        critical = sum(1 for i in issues if i.severity.value == "critical")
        warnings = sum(1 for i in issues if i.severity.value == "warning")
        infos = sum(1 for i in issues if i.severity.value == "info")
        level = (
            "优秀" if overall >= 90
            else "良好" if overall >= 70
            else "需改进" if overall >= 50
            else "差"
        )
        return (
            f"Skill '{manifest.name}' ({manifest.skill_type.value}) 体检完成: "
            f"总体评分 {overall}/100 ({level}). "
            f"发现问题: {critical} 严重 / {warnings} 警告 / {infos} 提示. "
            f"维度得分: " + ", ".join(
                f"{d}={ds.score}" for d, ds in dimension_scores.items()
            )
        )

    @staticmethod
    def _error_score(dimension: str, message: str) -> DimensionScore:
        return DimensionScore(
            dimension=dimension,
            name="Error",
            score=0,
            weight=1.0,
            issues=[
                Issue(
                    dimension=dimension,
                    severity=Severity.CRITICAL,
                    category="引擎错误",
                    location="engine",
                    message=f"分析器执行失败: {message}",
                )
            ],
        )
