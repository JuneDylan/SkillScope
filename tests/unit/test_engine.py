"""
引擎单元测试
"""
from __future__ import annotations
import pytest
from pathlib import Path

from skillscope.core.engine import SkillScopeEngine
from skillscope.core.config import load_config


class TestSkillScopeEngine:
    def test_engine_init_default(self):
        engine = SkillScopeEngine()
        assert engine.config is not None

    def test_engine_audit_empty_skill(self, tmp_path: Path):
        # 创建最小 Skill 结构
        skill_dir = tmp_path / "empty-skill"
        skill_dir.mkdir()
        (skill_dir / "README.md").write_text("# Empty Skill")

        engine = SkillScopeEngine(config=load_config())
        result = engine.audit(str(skill_dir))

        assert result.skill_name == "empty-skill"
        assert result.overall_score >= 0
        assert result.overall_score <= 100
        assert result.scan_duration_ms is not None
        assert result.scan_duration_ms >= 0

    def test_engine_audit_with_prompt(self, tmp_path: Path):
        skill_dir = tmp_path / "prompt-skill"
        skill_dir.mkdir()
        (skill_dir / "system_prompt.md").write_text(
            "你是一名专家。请回答以下问题。\n"
        )

        engine = SkillScopeEngine(config=load_config())
        result = engine.audit(str(skill_dir))

        assert result.skill_type.value == "prompt"
        assert "P" in result.dimension_scores

    def test_engine_ci_threshold_fail(self, tmp_path: Path):
        skill_dir = tmp_path / "bad-skill"
        skill_dir.mkdir()
        # 无 README，无测试，有 eval
        (skill_dir / "main.py").write_text("eval(user_input)\n")

        config = load_config()
        config.fail_threshold = 100  # 不可能达到
        engine = SkillScopeEngine(config=config)
        result = engine.audit(str(skill_dir))

        assert result.overall_score < 100

    def test_compute_overall_weighted(self):
        from skillscope.core.models import DimensionScore
        scores = {
            "A": DimensionScore(dimension="A", name="TestA", score=80, weight=0.5),
            "B": DimensionScore(dimension="B", name="TestB", score=60, weight=0.5),
        }
        engine = SkillScopeEngine()
        overall = engine._compute_overall(scores)
        assert overall == 70

    def test_parallel_vs_serial_same_result(self, tmp_path: Path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "README.md").write_text("# Test\n" * 50)
        (skill_dir / "prompt.md").write_text("You are an expert.\n")

        config_parallel = load_config()
        config_parallel.parallel = True
        result_parallel = SkillScopeEngine(config=config_parallel).audit(str(skill_dir))

        config_serial = load_config()
        config_serial.parallel = False
        result_serial = SkillScopeEngine(config=config_serial).audit(str(skill_dir))

        assert result_parallel.overall_score == result_serial.overall_score
