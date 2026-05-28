"""
SkillScope 核心数据模型 (v2.0)
支持：评估、修复、配置、分层评分
"""
from __future__ import annotations
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


class SkillType(str, Enum):
    PROMPT = "prompt"
    TOOL = "tool"
    MCP = "mcp"
    AGENT_WORKFLOW = "agent_workflow"
    RAG = "rag"
    HYBRID = "hybrid"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class FixSafety(str, Enum):
    """修复操作的安全级别"""
    SAFE = "safe"           # 确定性高，无副作用
    SUGGESTED = "suggested"  # 建议但需确认
    DANGEROUS = "dangerous"  # 可能改变语义，必须人工审核


class Issue(BaseModel):
    """问题项（增强版：支持修复元数据）"""
    dimension: str
    severity: Severity
    category: str
    location: str
    message: str
    fix_hint: str = ""
    auto_fixable: bool = False
    fix_safety: FixSafety = FixSafety.SAFE
    fix_replacement: Optional[str] = None
    rule_id: Optional[str] = None
    source: str = "deterministic"
    metadata: dict[str, Any] = Field(default_factory=dict)


class FixPatch(BaseModel):
    """代码修复补丁"""
    file_path: str
    original: str
    replacement: str
    description: str
    safety: FixSafety = FixSafety.SAFE
    issue_rule_id: Optional[str] = None


class DimensionScore(BaseModel):
    """维度评分（增强版：支持配置化权重）"""
    dimension: str
    name: str
    score: int = Field(ge=0, le=100)
    weight: float = Field(ge=0.0, le=1.0)
    issues: list[Issue] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    sub_scores: dict[str, int] = Field(default_factory=dict)  # 子维度细分

    @field_validator("weight")
    @classmethod
    def weight_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("weight must be in [0.0, 1.0]")
        return v


class AuditResult(BaseModel):
    """审计结果（增强版：支持修复补丁和配置快照）"""
    skill_name: str
    skill_source: str
    skill_type: SkillType
    overall_score: int = Field(ge=0, le=100)
    dimension_scores: dict[str, DimensionScore]
    issues: list[Issue] = Field(default_factory=list)
    patches: list[FixPatch] = Field(default_factory=list)
    summary: str
    audit_timestamp: str
    config_snapshot: Optional[dict[str, Any]] = None  # 记录本次扫描使用的配置
    scan_duration_ms: Optional[int] = None
    files_scanned: int = 0


class SkillManifest(BaseModel):
    """扫描时识别的 Skill 结构信息（增强版：支持 AST 和缓存）"""
    name: str
    source_path: str
    skill_type: SkillType
    files: list[str] = Field(default_factory=list)
    prompt_files: list[str] = Field(default_factory=list)
    code_files: list[str] = Field(default_factory=list)
    config_files: list[str] = Field(default_factory=list)
    dependency_file: Optional[str] = None
    readme_exists: bool = False
    gitignore_exists: bool = False
    # v2.0 新增
    estimated_total_tokens: int = 0
    languages: list[str] = Field(default_factory=list)  # 检测到的编程语言
    ast_cache: dict[str, Any] = Field(default_factory=dict)  # AST 缓存（tree-sitter）


class RuleConfig(BaseModel):
    """单条规则配置"""
    enabled: bool = True
    severity: Optional[Severity] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DimensionConfig(BaseModel):
    """维度配置"""
    enabled: bool = True
    weight: float = 1.0
    rules: dict[str, RuleConfig] = Field(default_factory=dict)
    threshold: int = 70  # 及格线


class SkillScopeConfig(BaseModel):
    """全局配置模型"""
    version: str = "1.0"
    preset: Optional[str] = None
    dimensions: dict[str, DimensionConfig] = Field(default_factory=dict)
    output_format: str = "console"  # console | json | sarif
    fail_threshold: Optional[int] = None  # CI 门禁阈值
    cache_enabled: bool = True
    parallel: bool = True
    max_workers: int = 4
    ai_enabled: bool = False  # 是否启用 LLM Judge
    ai_model: Optional[str] = None

    @field_validator("max_workers")
    @classmethod
    def max_workers_positive(cls, v: int) -> int:
        if v < 1:
            return 1
        return v
