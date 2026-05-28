"""
修复器抽象基类
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional

from skillscope.core.models import SkillManifest, Issue, FixPatch


class BaseFixer(ABC):
    """修复器基类：将 Issue 转换为 FixPatch"""
    name: str = ""
    supported_rules: list[str] = []  # 支持修复的规则ID列表

    def can_fix(self, issue: Issue) -> bool:
        """判断是否能修复该问题"""
        if not issue.auto_fixable:
            return False
        if issue.rule_id and issue.rule_id in self.supported_rules:
            return True
        return False

    @abstractmethod
    def generate_patch(self, manifest: SkillManifest, issue: Issue) -> Optional[FixPatch]:
        """生成修复补丁，失败返回 None"""
        raise NotImplementedError
