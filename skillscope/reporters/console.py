"""
终端报告生成器 v2.0（Lighthouse 风格）
增强：子维度展示、修复预览、配置摘要
"""
from __future__ import annotations
from skillscope.core.models import AuditResult, Severity, FixSafety


RISK_COLORS = {
    "critical": "\033[91m",
    "warning": "\033[93m",
    "info": "\033[94m",
    "reset": "\033[0m",
    "green": "\033[92m",
    "bold": "\033[1m",
}

SEVERITY_ICONS = {"critical": "🔴", "warning": "🟠", "info": "🔵"}
FIX_SAFETY_ICONS = {"safe": "🛡️", "suggested": "⚠️", "dangerous": "☠️"}


def score_bar(score: int, width: int = 20) -> str:
    filled = int(score / 100 * width)
    empty = width - filled
    return "█" * filled + "░" * empty


def score_color(score: int) -> str:
    if score >= 90:
        return "🟢"
    if score >= 70:
        return "🟡"
    if score >= 50:
        return "🟠"
    return "🔴"


def generate_console_report(result: AuditResult, use_color: bool = True) -> str:
    lines = []
    c = lambda code, text: f"{RISK_COLORS.get(code, '')}{text}{RISK_COLORS['reset']}" if use_color else text
    b = lambda text: c("bold", text)

    lines.append("=" * 72)
    lines.append(b("  SkillScope 体检报告 v2.0"))
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"  Skill: {result.skill_name}")
    lines.append(f"  类型: {result.skill_type.value}")
    lines.append(f"  来源: {result.skill_source}")
    lines.append(f"  扫描文件: {result.files_scanned}")
    if result.scan_duration_ms:
        lines.append(f"  耗时: {result.scan_duration_ms}ms")
    lines.append("")

    # 总体评分
    icon = score_color(result.overall_score)
    lines.append("─" * 72)
    lines.append(f"  总体评分: {icon} {b(str(result.overall_score))}/100")
    lines.append("─" * 72)
    lines.append(f"    {score_bar(result.overall_score)}")
    lines.append("")

    # 维度评分（含子维度）
    lines.append("─" * 72)
    lines.append(b("  维度评分"))
    lines.append("─" * 72)
    for dim, ds in result.dimension_scores.items():
        icon = score_color(ds.score)
        lines.append(f"  {icon} {dim} {ds.name:10s} {ds.score:3d}/100  {score_bar(ds.score)}")
        if ds.sub_scores:
            for sub_key, sub_val in ds.sub_scores.items():
                sub_icon = score_color(sub_val)
                lines.append(f"      {sub_icon} {sub_key:20s} {sub_val:3d}/100")
    lines.append("")

    # 修复预览
    if result.patches:
        lines.append("─" * 72)
        lines.append(b(f"  可自动修复 ({len(result.patches)} 项)"))
        lines.append("─" * 72)
        for idx, patch in enumerate(result.patches, 1):
            safe_icon = FIX_SAFETY_ICONS.get(patch.safety.value, "")
            lines.append(f"  {idx}. {safe_icon} [{patch.safety.value}] {patch.file_path}")
            lines.append(f"     {patch.description}")
        lines.append("")

    # 问题清单
    if result.issues:
        lines.append("─" * 72)
        lines.append(b(f"  发现问题 ({len(result.issues)} 项)"))
        lines.append("─" * 72)
        for sev in ["critical", "warning", "info"]:
            sev_issues = [i for i in result.issues if i.severity.value == sev]
            if not sev_issues:
                continue
            lines.append(f"  [{SEVERITY_ICONS[sev]} {sev.upper()}]")
            for idx, issue in enumerate(sev_issues, 1):
                fixable = " [可自动修复]" if issue.auto_fixable else ""
                lines.append(f"    {idx}. [{issue.category}] {issue.message}{fixable}")
                lines.append(f"       📍 {issue.location}")
                if issue.fix_hint:
                    lines.append(f"       💡 {issue.fix_hint}")
                lines.append("")

    # 配置快照
    if result.config_snapshot:
        lines.append("─" * 72)
        lines.append(b("  扫描配置"))
        lines.append("─" * 72)
        preset = result.config_snapshot.get("preset") or "default"
        lines.append(f"  预设: {preset}")
        lines.append("")

    # 摘要
    lines.append("─" * 72)
    lines.append(b("  摘要"))
    lines.append("─" * 72)
    lines.append(f"  {result.summary}")
    lines.append("")
    lines.append(f"  体检时间: {result.audit_timestamp}")
    lines.append("=" * 72)

    return "\n".join(lines)
