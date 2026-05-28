"""
CLI 单元测试
"""
from __future__ import annotations
import pytest
from pathlib import Path

from skillscope.cli import build_parser, cmd_scan, cmd_config


class TestCLIParser:
    def test_scan_command(self):
        parser = build_parser()
        args = parser.parse_args(["scan", "./my-skill"])
        assert args.command == "scan"
        assert args.path == "./my-skill"

    def test_scan_with_format(self):
        parser = build_parser()
        args = parser.parse_args(["scan", "./my-skill", "--format", "json"])
        assert args.format == "json"

    def test_scan_with_fix(self):
        parser = build_parser()
        args = parser.parse_args(["scan", "./my-skill", "--fix", "safe"])
        assert args.fix == "safe"

    def test_scan_with_apply_fixes(self):
        parser = build_parser()
        args = parser.parse_args(["scan", "./my-skill", "--fix", "safe", "--apply-fixes"])
        assert args.apply_fixes is True

    def test_scan_with_output(self):
        parser = build_parser()
        args = parser.parse_args(["scan", "./my-skill", "--format", "json", "--output", "report.json"])
        assert args.output == "report.json"

    def test_scan_no_parallel(self):
        parser = build_parser()
        args = parser.parse_args(["scan", "./my-skill", "--no-parallel"])
        assert args.parallel is False

    def test_config_init(self):
        parser = build_parser()
        args = parser.parse_args(["config", "--init"])
        assert args.command == "config"
        assert args.init is True

    def test_gui_command(self):
        parser = build_parser()
        args = parser.parse_args(["gui", "--port", "9000"])
        assert args.command == "gui"
        assert args.port == 9000

    def test_global_options(self):
        parser = build_parser()
        args = parser.parse_args(["--fail-threshold", "80", "scan", "./my-skill"])
        assert args.fail_threshold == 80


class TestCmdScan:
    def test_scan_returns_zero_on_pass(self, tmp_path: Path):
        skill_dir = tmp_path / "pass-skill"
        skill_dir.mkdir()
        (skill_dir / "README.md").write_text("# Pass\n" * 20)
        (skill_dir / "prompt.md").write_text("你是一个助手。\n")

        parser = build_parser()
        args = parser.parse_args(["--fail-threshold", "10", "scan", str(skill_dir)])
        exit_code = cmd_scan(args)
        assert exit_code == 0

    def test_scan_returns_nonzero_on_fail(self, tmp_path: Path):
        skill_dir = tmp_path / "fail-skill"
        skill_dir.mkdir()
        (skill_dir / "main.py").write_text("x = 1\n")

        parser = build_parser()
        args = parser.parse_args(["--fail-threshold", "100", "scan", str(skill_dir)])
        exit_code = cmd_scan(args)
        assert exit_code == 1


class TestCmdConfig:
    def test_config_init_creates_file(self, tmp_path: Path):
        import os
        original = os.getcwd()
        os.chdir(str(tmp_path))
        try:
            parser = build_parser()
            args = parser.parse_args(["config", "--init"])
            exit_code = cmd_config(args)
            assert exit_code == 0
            assert (tmp_path / "skillscope.yaml").exists()
        finally:
            os.chdir(original)

    def test_config_init_no_overwrite(self, tmp_path: Path):
        import os
        original = os.getcwd()
        os.chdir(str(tmp_path))
        try:
            (tmp_path / "skillscope.yaml").write_text("exists")
            parser = build_parser()
            args = parser.parse_args(["config", "--init"])
            exit_code = cmd_config(args)
            assert exit_code == 1
        finally:
            os.chdir(original)
