"""
简单文件缓存系统
用于增量扫描，避免重复分析未变更文件
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


class FileCache:
    def __init__(self, cache_dir: str = ".skillscope_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

    def _file_hash(self, file_path: str) -> str:
        p = Path(file_path)
        try:
            if p.is_file():
                content = p.read_bytes()
                return hashlib.sha256(content).hexdigest()[:16]
            elif p.is_dir():
                h = hashlib.sha256()
                for f in sorted(p.rglob("*")):
                    excluded = ("__pycache__", ".git", ".skillscope_cache")
                    if f.is_file() and not any(part in f.parts for part in excluded):
                        try:
                            h.update(f.relative_to(p).as_posix().encode())
                            h.update(f.read_bytes())
                        except Exception:
                            pass
                return h.hexdigest()[:16]
        except Exception:
            pass
        return ""

    def get(self, file_path: str, analyzer_name: str) -> dict | None:
        h = self._file_hash(file_path)
        if not h:
            return None
        cache_file = self.cache_dir / f"{h}_{analyzer_name}.json"
        if cache_file.exists():
            try:
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception:
                return None
        return None

    def set(self, file_path: str, analyzer_name: str, data: dict) -> None:
        h = self._file_hash(file_path)
        if not h:
            return
        cache_file = self.cache_dir / f"{h}_{analyzer_name}.json"
        cache_file.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def clear(self) -> None:
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
