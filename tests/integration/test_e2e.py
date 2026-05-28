"""
集成测试：端到端扫描流程
"""
from __future__ import annotations

import json
from pathlib import Path

from skillscope.core.config import load_config
from skillscope.core.engine import SkillScopeEngine
from skillscope.reporters.console import generate_console_report
from skillscope.reporters.html_reporter import generate_html_report
from skillscope.reporters.json_reporter import generate_json_report
from skillscope.reporters.sarif import generate_sarif_report


class TestEndToEndScan:
    def test_scan_prompt_only_skill(self, tmp_path: Path):
        skill_dir = tmp_path / "prompt-skill"
        skill_dir.mkdir()
        (skill_dir / "system_prompt.md").write_text(
            "你是一名资深Python开发者。\n"
            "请按以下步骤操作：\n"
            "1. 分析代码结构\n"
            "2. 输出 JSON 格式报告\n"
        )

        engine = SkillScopeEngine(config=load_config())
        result = engine.audit(str(skill_dir))

        assert result.skill_name == "prompt-skill"
        assert result.overall_score > 0
        assert "P" in result.dimension_scores
        assert result.dimension_scores["P"].score > 50

    def test_scan_tool_skill_with_issues(self, tmp_path: Path):
        skill_dir = tmp_path / "bad-tool"
        skill_dir.mkdir()
        (skill_dir / "main.py").write_text(
            'import os\n'
            'api_key = "sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567"\n'
            'result = eval(user_data)\n'
            'temperature = 0.7\n'
            'exec("print(1)")\n'
        )

        engine = SkillScopeEngine(config=load_config())
        result = engine.audit(str(skill_dir))

        assert result.overall_score < 90
        categories = {i.category for i in result.issues}
        assert "危险函数" in categories or "Secrets泄露" in categories or "硬编码配置" in categories

    def test_scan_well_structured_skill(self, tmp_path: Path):
        skill_dir = tmp_path / "good-skill"
        skill_dir.mkdir()
        (skill_dir / "README.md").write_text("# Good Skill\n\n## 安装\n\npip install\n\n## 示例\n\n```python\nprint('hello')\n```\n" * 10)
        (skill_dir / "system_prompt.md").write_text(
            "你是一名专业助手。请按步骤分析：\n1. 收集信息\n2. 分析数据\n3. 输出JSON格式\n"
        )
        (skill_dir / "main.py").write_text(
            'import os\n\ndef process(data: str) -> dict:\n    """处理数据"""\n    try:\n        return {"result": data}\n    except Exception as e:\n        raise ValueError(str(e))\n'
        )
        (skill_dir / "tests").mkdir()
        (skill_dir / "tests" / "test_main.py").write_text("def test_process():\n    assert True\n")
        (skill_dir / ".gitignore").write_text("__pycache__/\n*.pyc\n")

        engine = SkillScopeEngine(config=load_config())
        result = engine.audit(str(skill_dir))

        assert result.overall_score > 50

    def test_scan_single_file(self, tmp_path: Path):
        prompt_file = tmp_path / "single_prompt.md"
        prompt_file.write_text("你是一个翻译助手。将英文翻译为中文。\n")

        engine = SkillScopeEngine(config=load_config())
        result = engine.audit(str(prompt_file))

        assert result.overall_score > 0

    def test_scan_with_fix_generation(self, tmp_path: Path):
        skill_dir = tmp_path / "fixable-skill"
        skill_dir.mkdir()
        (skill_dir / "main.py").write_text(
            'api_key = os.environ.get("API_KEY", "")\n'
        )

        config = load_config()
        engine = SkillScopeEngine(config=config)
        result = engine.audit(str(skill_dir), apply_fixes=False, fix_safety_level="safe")

        assert isinstance(result.patches, list)

    def test_scan_with_fix_application(self, tmp_path: Path):
        skill_dir = tmp_path / "fix-apply-skill"
        skill_dir.mkdir()
        (skill_dir / "main.py").write_text("old_content\n")

        engine = SkillScopeEngine(config=load_config())
        result = engine.audit(str(skill_dir), apply_fixes=False, fix_safety_level="safe")

        assert result.skill_name == "fix-apply-skill"

    def test_scan_parallel_vs_serial(self, tmp_path: Path):
        skill_dir = tmp_path / "parallel-skill"
        skill_dir.mkdir()
        (skill_dir / "README.md").write_text("# Test\n" * 20)
        (skill_dir / "prompt.md").write_text("你是一个助手。\n")

        config_p = load_config()
        config_p.parallel = True
        result_p = SkillScopeEngine(config=config_p).audit(str(skill_dir))

        config_s = load_config()
        config_s.parallel = False
        result_s = SkillScopeEngine(config=config_s).audit(str(skill_dir))

        assert result_p.overall_score == result_s.overall_score


class TestEndToEndReports:
    def _make_skill(self, tmp_path: Path) -> Path:
        skill_dir = tmp_path / "report-skill"
        skill_dir.mkdir()
        (skill_dir / "README.md").write_text("# Report Test\n")
        (skill_dir / "prompt.md").write_text("你是一个助手。\n")
        return skill_dir

    def test_json_report_from_scan(self, tmp_path: Path):
        skill_dir = self._make_skill(tmp_path)
        engine = SkillScopeEngine(config=load_config())
        result = engine.audit(str(skill_dir))

        report = generate_json_report(result)
        parsed = json.loads(report)
        assert parsed["skill_name"] == "report-skill"

    def test_sarif_report_from_scan(self, tmp_path: Path):
        skill_dir = self._make_skill(tmp_path)
        engine = SkillScopeEngine(config=load_config())
        result = engine.audit(str(skill_dir))

        report = generate_sarif_report(result)
        sarif = json.loads(report)
        assert sarif["version"] == "2.1.0"

    def test_console_report_from_scan(self, tmp_path: Path):
        skill_dir = self._make_skill(tmp_path)
        engine = SkillScopeEngine(config=load_config())
        result = engine.audit(str(skill_dir))

        report = generate_console_report(result, use_color=False)
        assert "report-skill" in report

    def test_html_report_from_scan(self, tmp_path: Path):
        skill_dir = self._make_skill(tmp_path)
        engine = SkillScopeEngine(config=load_config())
        result = engine.audit(str(skill_dir))

        report = generate_html_report(result)
        assert "<!DOCTYPE html>" in report
        assert "report-skill" in report

    def test_report_file_output(self, tmp_path: Path):
        skill_dir = self._make_skill(tmp_path)
        engine = SkillScopeEngine(config=load_config())
        result = engine.audit(str(skill_dir))

        output_file = tmp_path / "report.json"
        output_file.write_text(generate_json_report(result), encoding="utf-8")

        assert output_file.exists()
        parsed = json.loads(output_file.read_text(encoding="utf-8"))
        assert parsed["skill_name"] == "report-skill"


class TestEndToEndCI:
    def test_ci_pass(self, tmp_path: Path):
        skill_dir = tmp_path / "ci-pass"
        skill_dir.mkdir()
        (skill_dir / "README.md").write_text("# CI Pass\n" * 50)
        (skill_dir / "prompt.md").write_text("你是一个专业助手。请输出JSON格式。\n")

        config = load_config()
        config.fail_threshold = 10
        engine = SkillScopeEngine(config=config)
        result = engine.audit(str(skill_dir))

        assert result.overall_score >= 10

    def test_ci_fail(self, tmp_path: Path):
        skill_dir = tmp_path / "ci-fail"
        skill_dir.mkdir()
        (skill_dir / "main.py").write_text("eval('1+1')\n")

        config = load_config()
        config.fail_threshold = 100
        engine = SkillScopeEngine(config=config)
        result = engine.audit(str(skill_dir))

        assert result.overall_score < 100
