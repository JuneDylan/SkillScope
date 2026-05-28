"""
SkillScope: AI Agent Skill 体检与重构工具 v2.0
像 Lighthouse 检查网页一样检查你的 AI Skill

架构：
  - core: 引擎、模型、配置、注册表、加载器
  - analyzers: 多维度分析器（P/S/X/F/C/M）
  - fixers: 自动修复引擎
  - reporters: 多格式报告（Console/JSON/SARIF）
  - utils: 工具函数
"""

__version__ = "0.2.0"
__all__ = ["__version__"]
