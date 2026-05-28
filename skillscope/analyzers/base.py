"""
分析器抽象基类 v2.0
支持：配置注入、子维度评分、AI 增强钩子
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional, Any

from skillscope.core.models import SkillManifest, DimensionScore, DimensionConfig


class BaseAnalyzer(ABC):
    dimension: str = ""
    name: str = ""
    weight: float = 1.0
    _config: Optional[DimensionConfig] = None

    def apply_config(self, config: DimensionConfig | dict) -> None:
        """应用维度配置"""
        if isinstance(config, dict):
            config = DimensionConfig(**config)
        self._config = config
        if config.weight is not None:
            self.weight = config.weight

    @abstractmethod
    def analyze(self, manifest: SkillManifest) -> DimensionScore:
        raise NotImplementedError

    def _should_run_rule(self, rule_id: str) -> bool:
        """检查规则是否启用（支持配置化禁用）"""
        if self._config is None or self._config.rules is None:
            return True
        rule_cfg = self._config.rules.get(rule_id)
        if rule_cfg is None:
            return True
        return rule_cfg.enabled

    def _sub_scores_average(self, sub_scores: dict[str, int]) -> int:
        """计算子维度平均分"""
        if not sub_scores:
            return 0
        return int(sum(sub_scores.values()) / len(sub_scores))
