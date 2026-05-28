"""
SkillScope CLI v2.0 入口
新增：配置加载、修复控制、多格式输出、CI 门禁
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

from skillscope.core.config import load_config
from skillscope.core.engine import SkillScopeEngine
from skillscope.reporters.console import generate_console_report
from skillscope.reporters.html_reporter import generate_html_report
from skillscope.reporters.json_reporter import generate_json_report
from skillscope.reporters.sarif import generate_sarif_report


def _ensure_utf8_output():
    if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
        try:
            if sys.stdout.encoding != "utf-8":
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            if sys.stderr.encoding != "utf-8":
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass


def _safe_print(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "utf-8"
        safe = text.encode(enc, errors="replace").decode(enc, errors="replace")
        print(safe)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skillscope",
        description="SkillScope v2.0: 像 Lighthouse 一样检查你的 AI Skill",
    )
    parser.add_argument("--config", help="配置文件路径 (skillscope.yaml)")
    parser.add_argument("--preset", help="使用预设配置")
    parser.add_argument("--no-color", action="store_true", help="禁用终端颜色")
    parser.add_argument("--fail-threshold", type=int, help="CI 门禁阈值 (低于此分数退出码非零)")

    sub = parser.add_subparsers(dest="command", help="可用命令")

    scan = sub.add_parser("scan", help="扫描 Skill 并生成体检报告")
    scan.add_argument("path", help="Skill 路径（本地目录或文件）")
    scan.add_argument("--format", choices=["console", "json", "sarif", "html"], default="console", help="输出格式")
    scan.add_argument("--output", help="输出文件路径")
    scan.add_argument("--fix", choices=["none", "safe", "suggested", "all"], default="none",
                      help="自动修复级别")
    scan.add_argument("--apply-fixes", action="store_true", help="应用生成的修复补丁到文件")
    scan.add_argument("--parallel", action="store_true", default=True, help="并行分析（默认开启）")
    scan.add_argument("--no-parallel", action="store_false", dest="parallel", help="禁用并行分析")

    config_cmd = sub.add_parser("config", help="配置管理")
    config_cmd.add_argument("--init", action="store_true", help="生成默认配置文件")

    gui_cmd = sub.add_parser("gui", help="启动 Web GUI 可视化界面")
    gui_cmd.add_argument("--host", default="127.0.0.1", help="监听地址 (默认 127.0.0.1)")
    gui_cmd.add_argument("--port", type=int, default=8501, help="监听端口 (默认 8501)")

    return parser


def cmd_scan(args) -> int:
    config = load_config(args.config)
    if args.preset:
        config.preset = args.preset
    if args.fail_threshold is not None:
        config.fail_threshold = args.fail_threshold
    config.parallel = args.parallel

    engine = SkillScopeEngine(config=config)
    fix_level = args.fix
    if args.apply_fixes and fix_level == "none":
        fix_level = "safe"
    result = engine.audit(
        args.path,
        apply_fixes=args.apply_fixes,
        fix_safety_level=fix_level,
    )

    report = None
    if args.format == "console":
        report = generate_console_report(result, use_color=not args.no_color)
        _safe_print(report)
    elif args.format == "json":
        report = generate_json_report(result)
        _safe_print(report)
    elif args.format == "sarif":
        report = generate_sarif_report(result)
        _safe_print(report)
    elif args.format == "html":
        report = generate_html_report(result)
        out_path = args.output or f"skillscope_report_{result.skill_name}.html"
        Path(out_path).write_text(report, encoding="utf-8")
        _safe_print(f"HTML 报告已保存至: {out_path}")

    if args.output and args.format != "html":
        Path(args.output).write_text(report, encoding="utf-8")
        _safe_print(f"\n报告已保存至: {args.output}")

    # CI 门禁（显式处理 None 和 0）
    threshold = args.fail_threshold
    if threshold is None:
        threshold = config.fail_threshold
    if threshold is not None and result.overall_score < threshold:
        _safe_print(f"\n❌ CI 门禁失败: 评分 {result.overall_score} < 阈值 {threshold}")
        return 1

    return 0


def cmd_config(args) -> int:
    if args.init:
        default = Path("skillscope.yaml")
        if default.exists():
            print("skillscope.yaml 已存在")
            return 1
        default.write_text("""version: "1.0"
preset: general
dimensions:
  P:
    enabled: true
    weight: 0.20
    threshold: 70
  S:
    enabled: true
    weight: 0.25
    threshold: 80
output_format: console
fail_threshold: 70
parallel: true
max_workers: 4
""", encoding="utf-8")
        print("已生成 skillscope.yaml")
    return 0


def cmd_gui(args) -> int:
    try:
        from skillscope.gui import launch_gui
    except ImportError:
        print("Web GUI 需要 Flask，请运行: pip install flask")
        return 1
    launch_gui(host=args.host, port=args.port)
    return 0


def main():
    _ensure_utf8_output()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "scan":
        sys.exit(cmd_scan(args))
    elif args.command == "config":
        sys.exit(cmd_config(args))
    elif args.command == "gui":
        sys.exit(cmd_gui(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
