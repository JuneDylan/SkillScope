"""
Token 估算工具 v2.0
优先使用 tiktoken，降级到字符估算
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def estimate_token_count(text: str, encoding_name: str = "cl100k_base") -> int:
    """精确估算 token 数，优先使用 tiktoken"""
    if not text:
        return 0
    try:
        import tiktoken
        try:
            enc = tiktoken.get_encoding(encoding_name)
            return len(enc.encode(text))
        except Exception:
            return int(len(text) / 3.5)
    except ImportError:
        return int(len(text) / 3.5)


def estimate_tokens_for_files(root: Path, files: list[str], max_workers: int = 4) -> int:
    """并行估算多个文件的 token 总数"""
    def _count_file(rel_path: str) -> int:
        try:
            content = (root / rel_path).read_text(encoding="utf-8", errors="ignore")
            return estimate_token_count(content)
        except Exception:
            return 0

    if max_workers <= 1 or len(files) <= 1:
        return sum(_count_file(f) for f in files)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return sum(pool.map(_count_file, files))
