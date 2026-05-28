"""
分析器单元测试
"""
from __future__ import annotations

from pathlib import Path

from skillscope.analyzers.compatibility import CompatibilityAnalyzer
from skillscope.analyzers.correctness import CorrectnessAnalyzer
from skillscope.analyzers.maintainability import MaintainabilityAnalyzer
from skillscope.analyzers.performance import PerformanceAnalyzer
from skillscope.analyzers.prompt import PromptAnalyzer
from skillscope.analyzers.security import SecurityScanner
from skillscope.core.models import SkillManifest, SkillType


class TestPromptAnalyzer:
    def test_missing_prompt(self, tmp_path: Path):
        manifest = SkillManifest(
            name="test", source_path=str(tmp_path),
            skill_type=SkillType.UNKNOWN, files=["main.py"], code_files=["main.py"]
        )
        analyzer = PromptAnalyzer()
        result = analyzer.analyze(manifest)
        assert result.score == 0
        assert any(i.category == "缺失Prompt" for i in result.issues)

    def test_good_prompt(self, tmp_path: Path):
        prompt_file = tmp_path / "prompt.md"
        prompt_file.write_text(
            "你是一名资深云架构师。\n"
            "请按以下步骤分析：\n"
            "1. 识别架构模式\n"
            "2. 输出 JSON 格式报告\n"
        )
        manifest = SkillManifest(
            name="test", source_path=str(tmp_path),
            skill_type=SkillType.PROMPT, files=["prompt.md"], prompt_files=["prompt.md"]
        )
        analyzer = PromptAnalyzer()
        result = analyzer.analyze(manifest)
        assert result.score > 70
        assert "clarity" in result.sub_scores

    def test_injection_risk(self, tmp_path: Path):
        code_file = tmp_path / "main.py"
        code_file.write_text('prompt = f"Tell me about {user_input}"\n')
        manifest = SkillManifest(
            name="test", source_path=str(tmp_path),
            skill_type=SkillType.TOOL, files=["main.py"], code_files=["main.py"]
        )
        analyzer = PromptAnalyzer()
        result = analyzer.analyze(manifest)
        assert any(i.category == "Prompt注入" for i in result.issues)


class TestSecurityScanner:
    def test_secret_detection(self, tmp_path: Path):
        code_file = tmp_path / "main.py"
        code_file.write_text('api_key = "sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567"\n')
        manifest = SkillManifest(
            name="test", source_path=str(tmp_path),
            skill_type=SkillType.TOOL, files=["main.py"], code_files=["main.py"]
        )
        analyzer = SecurityScanner()
        result = analyzer.analyze(manifest)
        assert any(i.category == "Secrets泄露" for i in result.issues)
        assert result.score < 100

    def test_dangerous_function(self, tmp_path: Path):
        code_file = tmp_path / "main.py"
        code_file.write_text("result = eval(user_data)\n")
        manifest = SkillManifest(
            name="test", source_path=str(tmp_path),
            skill_type=SkillType.TOOL, files=["main.py"], code_files=["main.py"]
        )
        analyzer = SecurityScanner()
        result = analyzer.analyze(manifest)
        assert any(i.category == "危险函数" for i in result.issues)

    def test_hardcoded_config(self, tmp_path: Path):
        code_file = tmp_path / "main.py"
        code_file.write_text('temperature = 0.7\n')
        manifest = SkillManifest(
            name="test", source_path=str(tmp_path),
            skill_type=SkillType.TOOL, files=["main.py"], code_files=["main.py"]
        )
        analyzer = SecurityScanner()
        result = analyzer.analyze(manifest)
        assert any(i.category == "硬编码配置" for i in result.issues)


class TestMaintainabilityAnalyzer:
    def test_no_readme(self, tmp_path: Path):
        manifest = SkillManifest(
            name="test", source_path=str(tmp_path),
            skill_type=SkillType.UNKNOWN, files=[]
        )
        analyzer = MaintainabilityAnalyzer()
        result = analyzer.analyze(manifest)
        assert any(i.category == "缺少文档" for i in result.issues)

    def test_good_readme(self, tmp_path: Path):
        readme = tmp_path / "README.md"
        readme.write_text("# Test\n\n## 安装\n\n## 示例\n" * 100)
        manifest = SkillManifest(
            name="test", source_path=str(tmp_path),
            skill_type=SkillType.UNKNOWN, files=["README.md"], readme_exists=True
        )
        analyzer = MaintainabilityAnalyzer()
        result = analyzer.analyze(manifest)
        assert result.score > 60


class TestPerformanceAnalyzer:
    def test_token_cost(self, tmp_path: Path):
        manifest = SkillManifest(
            name="test", source_path=str(tmp_path),
            skill_type=SkillType.PROMPT, files=["prompt.md"], prompt_files=["prompt.md"],
            estimated_total_tokens=9000
        )
        analyzer = PerformanceAnalyzer()
        result = analyzer.analyze(manifest)
        assert result.score < 100
        assert "token_cost" in result.sub_scores


class TestCorrectnessAnalyzer:
    def test_bare_except(self, tmp_path: Path):
        code_file = tmp_path / "main.py"
        code_file.write_text("try:\n    pass\nexcept:\n    pass\n")
        manifest = SkillManifest(
            name="test", source_path=str(tmp_path),
            skill_type=SkillType.TOOL, files=["main.py"], code_files=["main.py"]
        )
        analyzer = CorrectnessAnalyzer()
        result = analyzer.analyze(manifest)
        assert any(i.category == "异常处理" for i in result.issues)


class TestCompatibilityAnalyzer:
    def test_vendor_lock(self, tmp_path: Path):
        code_file = tmp_path / "main.py"
        code_file.write_text('response = client.chat.completions.create(model="gpt-4", functions=tools)\n')
        manifest = SkillManifest(
            name="test", source_path=str(tmp_path),
            skill_type=SkillType.TOOL, files=["main.py"], code_files=["main.py"]
        )
        analyzer = CompatibilityAnalyzer()
        result = analyzer.analyze(manifest)
        assert any(i.category == "厂商锁定" for i in result.issues)
