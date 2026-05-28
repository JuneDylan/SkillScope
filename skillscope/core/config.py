"""
SkillScope 配置系统
支持 YAML/JSON 配置文件、预设加载、环境变量覆盖
"""
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional

import copy

import yaml

from skillscope.core.models import SkillScopeConfig, DimensionConfig, RuleConfig


DEFAULT_CONFIG: dict = {
    "version": "1.0",
    "dimensions": {
        "P": {
            "enabled": True,
            "weight": 0.20,
            "threshold": 70,
            "name": "Prompt质量",
        },
        "S": {
            "enabled": True,
            "weight": 0.25,
            "threshold": 80,
            "name": "安全性",
        },
        "X": {
            "enabled": True,
            "weight": 0.15,
            "threshold": 60,
            "name": "可维护性",
        },
        "F": {
            "enabled": True,
            "weight": 0.15,
            "threshold": 70,
            "name": "性能",
        },
        "C": {
            "enabled": True,
            "weight": 0.15,
            "threshold": 70,
            "name": "正确性",
        },
        "M": {
            "enabled": True,
            "weight": 0.10,
            "threshold": 60,
            "name": "兼容性",
        },
    },
    "output_format": "console",
    "cache_enabled": True,
    "parallel": True,
    "max_workers": 4,
    "ai_enabled": False,
}


def load_config(path: Optional[str] = None) -> SkillScopeConfig:
    """加载配置，优先级：传入路径 > 环境变量 > 默认配置"""
    merged = copy.deepcopy(DEFAULT_CONFIG)

    # 1. 加载预设（如果指定）
    preset = os.environ.get("SKILLSCOPE_PRESET")
    if preset:
        merged["preset"] = preset
        preset_data = _load_preset(preset)
        if preset_data:
            _deep_merge(merged, preset_data)

    # 2. 加载配置文件
    config_path = path or os.environ.get("SKILLSCOPE_CONFIG")
    if config_path and Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f) or {}
        _deep_merge(merged, user_config)

    # 3. 环境变量覆盖
    if os.environ.get("SKILLSCOPE_PARALLEL", "").lower() in ("0", "false", "no"):
        merged["parallel"] = False
    if os.environ.get("SKILLSCOPE_AI_ENABLED", "").lower() in ("1", "true", "yes"):
        merged["ai_enabled"] = True

    # 4. 规范化 dimensions
    dimensions = {}
    for dim_key, dim_val in merged.get("dimensions", {}).items():
        dimensions[dim_key] = DimensionConfig(**dim_val)
    merged["dimensions"] = dimensions

    return SkillScopeConfig(**merged)


def _load_preset(name: str) -> Optional[dict]:
    """加载内置预设"""
    preset_paths = [
        Path(__file__).parent.parent.parent / "presets" / "open-source" / f"{name}.yaml",
        Path.home() / ".skillscope" / "presets" / f"{name}.yaml",
    ]
    for p in preset_paths:
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return None


def _deep_merge(base: dict, override: dict) -> None:
    """深度合并字典"""
    for key, val in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(val, dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
