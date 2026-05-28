"""
文件解析工具 v2.0
增强：tree-sitter AST 支持（可选）、多语言检测
"""
from __future__ import annotations

import re
from pathlib import Path


def extract_python_code(file_path: str) -> list[tuple[int, str]]:
    """提取 Python 文件中的代码行，返回 (行号, 代码) 列表"""
    path = Path(file_path)
    if not path.exists() or path.suffix != ".py":
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return [(i + 1, line) for i, line in enumerate(lines)]


def extract_prompt_content(file_path: str) -> str:
    """提取 prompt 文件内容"""
    path = Path(file_path)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def has_try_except(file_path: str) -> bool:
    """检查文件是否有 try-except 块"""
    path = Path(file_path)
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8", errors="ignore")
    return "try:" in content and "except" in content


def count_functions(file_path: str) -> int:
    """统计 Python 文件中的函数数量"""
    path = Path(file_path)
    if not path.exists() or path.suffix != ".py":
        return 0
    content = path.read_text(encoding="utf-8", errors="ignore")
    return len(re.findall(r"^\s*def\s+\w+\s*\(", content, re.MULTILINE))


def is_config_hardcoded(file_path: str) -> list[str]:
    """检测硬编码的配置项"""
    path = Path(file_path)
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8", errors="ignore")
    hardcoded = []
    patterns = [
        r'(?:model|temperature|max_tokens|top_p)\s*=\s*[\'"]?[^\'"\s\)]+',
        r'(?:base_url|api_url|endpoint)\s*=\s*[\'"]https?://[^\'"]+[\'"]',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, content):
            hardcoded.append(match.group(0))
    return hardcoded


def parse_ast(file_path: str) -> dict | None:
    """v2.0: 尝试使用 tree-sitter 解析 AST（如果已安装）"""
    try:
        from tree_sitter import Language, Parser  # noqa: F401
        # 简化实现：实际项目中需要编译语言 so 文件
        path = Path(file_path)
        if not path.exists():
            return None
        # 返回占位，表示 AST 扩展点
        return {"file": file_path, "ast_available": False, "note": "Install tree-sitter for AST analysis"}
    except ImportError:
        return None
