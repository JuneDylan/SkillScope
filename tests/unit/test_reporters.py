"""
报告生成器单元测试
"""
from __future__ import annotations
import json
import pytest
from pathlib import Path

from skillscope.core.models import (
    AuditResult, DimensionScore, Issue, Severity, FixSafety,
    FixPatch, SkillType,
)
from skillscope.reporters.json_reporter import generate_json_report
from skillscope.reporters.sarif import generate_sarif_report
from skillscope.reporters.console import generate_console_report
from skillscope.reporters.html_reporter import generate_html_report


def _make_result(**overrides) -> AuditResult:
    defaults = {
        "skill_name": "test-skill",
        "skill_source": "/tmp/test-skill",
        "skill_type": SkillType.HYBRID,
        "overall_score": 75,
        "dimension_scores": {
            "P": DimensionScore(dimension="P", name="Prompt质量", score=80, weight=0.20),
            "S": DimensionScore(dimension="S", name="安全性", score=70, weight=0.25),
            "X": DimensionScore(dimension="X", name="可维护性", score=60, weight=0.15),
            "F": DimensionScore(dimension="F", name="性能", score=85, weight=0.15),
            "C": DimensionScore(dimension="C", name="正确性", score=75, weight=0.15),
            "M": DimensionScore(dimension="M", name="兼容性", score=80, weight=0.10),
        },
        "issues": [
            Issue(
                dimension="S", severity=Severity.CRITICAL,
                category="Secrets泄露", location="main.py:3",
                message="检测到 API Key", fix_hint="使用环境变量",
                rule_id="sec_secrets",
            ),
            Issue(
                dimension="X", severity=Severity.WARNING,
                category="缺少测试", location="/tmp/test-skill",
                message="未检测到测试文件",
                rule_id="maint_tests",
            ),
        ],
        "patches": [
            FixPatch(
                file_path="main.py", original="api_key = 'sk-xxx'",
                replacement="api_key = os.environ.get('API_KEY')",
                description="替换硬编码密钥", safety=FixSafety.SAFE,
            ),
        ],
        "summary": "Skill 'test-skill' 体检完成: 总体评分 75/100",
        "audit_timestamp": "2026-05-19T12:00:00+00:00",
        "scan_duration_ms": 150,
        "files_scanned": 5,
    }
    defaults.update(overrides)
    return AuditResult(**defaults)


class TestJSONReporter:
    def test_valid_json_output(self):
        result = _make_result()
        output = generate_json_report(result)
        parsed = json.loads(output)
        assert parsed["skill_name"] == "test-skill"
        assert parsed["overall_score"] == 75
        assert len(parsed["issues"]) == 2

    def test_json_contains_all_dimensions(self):
        result = _make_result()
        parsed = json.loads(generate_json_report(result))
        dims = parsed["dimension_scores"]
        assert set(dims.keys()) == {"P", "S", "X", "F", "C", "M"}

    def test_json_contains_patches(self):
        result = _make_result()
        parsed = json.loads(generate_json_report(result))
        assert len(parsed["patches"]) == 1
        assert parsed["patches"][0]["file_path"] == "main.py"

    def test_json_no_issues(self):
        result = _make_result(issues=[], patches=[], overall_score=100)
        parsed = json.loads(generate_json_report(result))
        assert parsed["issues"] == []
        assert parsed["patches"] == []


class TestSARIFReporter:
    def test_sarif_schema_version(self):
        result = _make_result()
        output = generate_sarif_report(result)
        sarif = json.loads(output)
        assert sarif["version"] == "2.1.0"
        assert "$schema" in sarif

    def test_sarif_has_runs(self):
        result = _make_result()
        sarif = json.loads(generate_sarif_report(result))
        assert len(sarif["runs"]) == 1
        run = sarif["runs"][0]
        assert run["tool"]["driver"]["name"] == "SkillScope"

    def test_sarif_rules_extracted(self):
        result = _make_result()
        sarif = json.loads(generate_sarif_report(result))
        rules = sarif["runs"][0]["tool"]["driver"]["rules"]
        rule_ids = [r["id"] for r in rules]
        assert "sec_secrets" in rule_ids
        assert "maint_tests" in rule_ids

    def test_sarif_results_mapping(self):
        result = _make_result()
        sarif = json.loads(generate_sarif_report(result))
        results = sarif["runs"][0]["results"]
        assert len(results) == 2
        critical_results = [r for r in results if r["level"] == "error"]
        assert len(critical_results) == 1

    def test_sarif_severity_mapping(self):
        result = _make_result()
        sarif = json.loads(generate_sarif_report(result))
        results = sarif["runs"][0]["results"]
        levels = {r["level"] for r in results}
        assert "error" in levels
        assert "warning" in levels

    def test_sarif_location_parsing(self):
        result = _make_result()
        sarif = json.loads(generate_sarif_report(result))
        results = sarif["runs"][0]["results"]
        loc = results[0]["locations"][0]["physicalLocation"]
        assert loc["artifactLocation"]["uri"] == "main.py"
        assert loc["region"]["startLine"] == 3


class TestConsoleReporter:
    def test_console_contains_skill_name(self):
        result = _make_result()
        output = generate_console_report(result, use_color=False)
        assert "test-skill" in output

    def test_console_contains_overall_score(self):
        result = _make_result()
        output = generate_console_report(result, use_color=False)
        assert "75" in output

    def test_console_contains_issues(self):
        result = _make_result()
        output = generate_console_report(result, use_color=False)
        assert "Secrets泄露" in output
        assert "缺少测试" in output

    def test_console_no_color_mode(self):
        result = _make_result()
        output = generate_console_report(result, use_color=False)
        assert "\033[" not in output

    def test_console_with_color_mode(self):
        result = _make_result()
        output = generate_console_report(result, use_color=True)
        assert "\033[" in output

    def test_console_contains_patches(self):
        result = _make_result()
        output = generate_console_report(result, use_color=False)
        assert "可自动修复" in output

    def test_console_empty_issues(self):
        result = _make_result(issues=[], patches=[], overall_score=100)
        output = generate_console_report(result, use_color=False)
        assert "test-skill" in output


class TestHTMLReporter:
    def test_html_valid_structure(self):
        result = _make_result()
        html = generate_html_report(result)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_html_contains_skill_name(self):
        result = _make_result()
        html = generate_html_report(result)
        assert "test-skill" in html

    def test_html_contains_score(self):
        result = _make_result()
        html = generate_html_report(result)
        assert "75" in html

    def test_html_xss_escaping(self):
        result = _make_result(
            issues=[
                Issue(
                    dimension="S", severity=Severity.WARNING,
                    category="<script>alert('xss')</script>",
                    location="main.py",
                    message="<img onerror=alert(1) src=x>",
                    rule_id="test_xss",
                )
            ],
            patches=[],
        )
        html = generate_html_report(result)
        assert "&lt;script&gt;alert(" in html
        assert "&lt;img onerror" in html

    def test_html_contains_chart_js(self):
        result = _make_result()
        html = generate_html_report(result)
        assert "chart.js" in html.lower() or "Chart" in html

    def test_html_contains_issues_section(self):
        result = _make_result()
        html = generate_html_report(result)
        assert "Secrets泄露" in html

    def test_html_empty_result(self):
        result = _make_result(issues=[], patches=[], overall_score=100)
        html = generate_html_report(result)
        assert "未发现问题" in html
