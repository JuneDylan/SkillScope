"""
SkillScope 插件注册表
支持动态发现、注册、配置化启用/禁用分析器
"""
from __future__ import annotations
from typing import Type, Optional
import importlib
import pkgutil

from skillscope.analyzers.base import BaseAnalyzer


class AnalyzerRegistry:
    """分析器注册表（单例模式）"""
    _instance: Optional["AnalyzerRegistry"] = None
    _analyzers: dict[str, Type[BaseAnalyzer]] = {}

    def __new__(cls) -> "AnalyzerRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._analyzers = {}
        return cls._instance

    def register(self, analyzer_class: Type[BaseAnalyzer]) -> None:
        """注册分析器类"""
        instance = analyzer_class()
        key = instance.dimension
        self._analyzers[key] = analyzer_class

    def get(self, dimension: str) -> Optional[Type[BaseAnalyzer]]:
        """按维度获取分析器类"""
        return self._analyzers.get(dimension)

    def list_dimensions(self) -> list[str]:
        """列出所有已注册的维度"""
        return list(self._analyzers.keys())

    def build_analyzers(
        self,
        enabled_dimensions: Optional[list[str]] = None,
        config: Optional[dict] = None,
    ) -> list[BaseAnalyzer]:
        """构建分析器实例列表"""
        instances = []
        for dim, cls in self._analyzers.items():
            if enabled_dimensions is not None and dim not in enabled_dimensions:
                continue
            inst = cls()
            if config and dim in config:
                inst.apply_config(config[dim])
            instances.append(inst)
        return instances

    def auto_discover(self, package_name: str = "skillscope.analyzers") -> None:
        """自动发现包内所有分析器"""
        try:
            package = importlib.import_module(package_name)
            for _, module_name, _ in pkgutil.iter_modules(package.__path__):
                if module_name in ("base",):
                    continue
                try:
                    module = importlib.import_module(f"{package_name}.{module_name}")
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, BaseAnalyzer)
                            and attr is not BaseAnalyzer
                            and not getattr(attr, "_abstract", False)
                        ):
                            self.register(attr)
                except Exception:
                    continue
        except Exception:
            pass


# 全局注册表实例
registry = AnalyzerRegistry()
