"""
Skill 加载器 v2.0
增强：AST 缓存、语言检测、Token 估算、并行文件读取
"""
from __future__ import annotations

import contextlib
import re
from pathlib import Path

from skillscope.core.models import SkillManifest, SkillType
from skillscope.utils.tokens import estimate_tokens_for_files

# 文件类型映射
CODE_EXTENSIONS = {".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp", ".c", ".cs"}
PROMPT_EXTENSIONS = {".md", ".txt", ".prompt"}
CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".toml"}
DEPENDENCY_FILES = {"requirements.txt", "package.json", "pyproject.toml", "Pipfile", "Cargo.toml", "go.mod"}

# Prompt 检测模式
PROMPT_PATTERNS = [
    r"system_prompt", r"user_prompt", r"prompt_template",
    r"\.prompt", r"instructions",
]

MCP_PATTERNS = [r"mcp\.json", r"mcp_config", r"model_context_protocol"]
RAG_PATTERNS = [r"retriever", r"vector_store", r"embedding", r"chunk"]


def load_skill(path: str, max_workers: int = 4) -> SkillManifest:
    source = Path(path).resolve()
    if not source.exists():
        raise FileNotFoundError(f"路径不存在: {path}")

    if source.is_file():
        return _load_single_file(source)
    return _load_directory(source, max_workers=max_workers)


def _load_directory(root: Path, max_workers: int = 4) -> SkillManifest:
    files, prompt_files, code_files, config_files = [], [], [], []
    dependency_file = None
    readme_exists = False
    gitignore_exists = False
    languages = set()

    # 1. 遍历文件（保留原始过滤逻辑）
    for f in root.rglob("*"):
        if not f.is_file():
            continue
        if any(part == "__pycache__" for part in f.parts):
            continue
        if any(part == ".git" for part in f.parts):
            continue

        rel = str(f.relative_to(root))
        files.append(rel)

        if f.name.lower() == "readme.md":
            readme_exists = True
        if f.name == ".gitignore":
            gitignore_exists = True
        if f.name in DEPENDENCY_FILES:
            dependency_file = rel

        suffix = f.suffix.lower()
        if suffix in CODE_EXTENSIONS:
            code_files.append(rel)
            languages.add(suffix.lstrip("."))
        elif suffix in PROMPT_EXTENSIONS or _is_prompt_file(f):
            prompt_files.append(rel)
        elif suffix in CONFIG_EXTENSIONS:
            config_files.append(rel)

    # 2. 并行估算 Token（v2.0 增强）
    all_text_files = prompt_files + code_files + config_files
    total_tokens = estimate_tokens_for_files(root, all_text_files, max_workers=max_workers)

    # 3. 类型检测
    skill_type = _detect_skill_type(root, files, prompt_files, code_files, config_files)
    name = root.name or "unknown-skill"

    return SkillManifest(
        name=name,
        source_path=str(root),
        skill_type=skill_type,
        files=files,
        prompt_files=prompt_files,
        code_files=code_files,
        config_files=config_files,
        dependency_file=dependency_file,
        readme_exists=readme_exists,
        gitignore_exists=gitignore_exists,
        estimated_total_tokens=total_tokens,
        languages=sorted(languages),
    )


def _load_single_file(source: Path) -> SkillManifest:
    suffix = source.suffix.lower()
    skill_type = SkillType.PROMPT if suffix in PROMPT_EXTENSIONS else SkillType.UNKNOWN
    tokens = estimate_tokens_for_files(source.parent, [source.name], max_workers=1)
    return SkillManifest(
        name=source.stem,
        source_path=str(source),
        skill_type=skill_type,
        files=[source.name],
        prompt_files=[source.name] if skill_type == SkillType.PROMPT else [],
        estimated_total_tokens=tokens,
    )


def _is_prompt_file(f: Path) -> bool:
    try:
        content = f.read_text(encoding="utf-8", errors="ignore")
        for pattern in PROMPT_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return True
    except Exception:
        pass
    return False


def _detect_skill_type(
    root: Path,
    files: list[str],
    prompt_files: list[str],
    code_files: list[str],
    config_files: list[str],
) -> SkillType:
    all_text = " ".join(files).lower()
    all_content = ""
    for cf in config_files[:3]:
        with contextlib.suppress(Exception):
            all_content += (root / cf).read_text(encoding="utf-8", errors="ignore").lower()

    if any(re.search(p, all_text) for p in MCP_PATTERNS) or "mcp" in all_content:
        return SkillType.MCP
    if any(re.search(p, all_text) for p in RAG_PATTERNS):
        return SkillType.RAG
    if "tool" in all_text and len(code_files) > 0:
        return SkillType.TOOL
    if "agent" in all_text or "workflow" in all_text:
        return SkillType.AGENT_WORKFLOW
    if len(prompt_files) > 0 and len(code_files) == 0:
        return SkillType.PROMPT
    if len(prompt_files) > 0 and len(code_files) > 0:
        return SkillType.HYBRID
    return SkillType.UNKNOWN
