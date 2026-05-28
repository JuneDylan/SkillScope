"""
配置系统单元测试
"""
from __future__ import annotations
import pytest
from pathlib import Path

from skillscope.core.config import load_config, DEFAULT_CONFIG


class TestLoadConfig:
    def test_default_config(self):
        config = load_config()
        assert config.version == "1.0"
        assert config.parallel is True
        assert config.max_workers == 4
        assert config.ai_enabled is False

    def test_config_from_yaml(self, tmp_path: Path):
        yaml_file = tmp_path / "skillscope.yaml"
        yaml_file.write_text("""version: "1.0"
preset: general
dimensions:
  P:
    enabled: true
    weight: 0.30
    threshold: 80
output_format: json
fail_threshold: 60
parallel: false
max_workers: 2
""", encoding="utf-8")
        config = load_config(str(yaml_file))
        assert config.output_format == "json"
        assert config.fail_threshold == 60
        assert config.parallel is False
        assert config.max_workers == 2

    def test_default_config_not_mutated(self):
        config1 = load_config()
        config1.fail_threshold = 99
        config2 = load_config()
        assert config2.fail_threshold != 99 or config2.fail_threshold is None

    def test_max_workers_validator(self):
        from skillscope.core.models import SkillScopeConfig
        config = SkillScopeConfig(max_workers=0)
        assert config.max_workers == 1

    def test_max_workers_negative(self):
        from skillscope.core.models import SkillScopeConfig
        config = SkillScopeConfig(max_workers=-5)
        assert config.max_workers == 1
