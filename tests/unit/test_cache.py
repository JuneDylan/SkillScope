"""
缓存系统单元测试
"""
from __future__ import annotations

from pathlib import Path

from skillscope.utils.cache import FileCache


class TestFileCache:
    def test_cache_miss(self, tmp_path: Path):
        cache = FileCache(cache_dir=str(tmp_path / "cache"))
        result = cache.get(str(tmp_path / "nonexistent.py"), "P")
        assert result is None

    def test_cache_set_and_get(self, tmp_path: Path):
        cache = FileCache(cache_dir=str(tmp_path / "cache"))
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        data = {"score": 85, "issues": []}
        cache.set(str(test_file), "P", data)

        result = cache.get(str(test_file), "P")
        assert result is not None
        assert result["score"] == 85

    def test_cache_invalidation_on_change(self, tmp_path: Path):
        cache = FileCache(cache_dir=str(tmp_path / "cache"))
        test_file = tmp_path / "test.py"
        test_file.write_text("version1")

        cache.set(str(test_file), "P", {"score": 50})
        result_before = cache.get(str(test_file), "P")
        assert result_before["score"] == 50

        test_file.write_text("version2")
        result_after = cache.get(str(test_file), "P")
        assert result_after is None

    def test_cache_different_analyzers(self, tmp_path: Path):
        cache = FileCache(cache_dir=str(tmp_path / "cache"))
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")

        cache.set(str(test_file), "P", {"score": 80})
        cache.set(str(test_file), "S", {"score": 60})

        assert cache.get(str(test_file), "P")["score"] == 80
        assert cache.get(str(test_file), "S")["score"] == 60

    def test_cache_directory_hash(self, tmp_path: Path):
        cache = FileCache(cache_dir=str(tmp_path / "cache"))
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        (skill_dir / "main.py").write_text("x = 1")

        cache.set(str(skill_dir), "P", {"score": 70})
        result = cache.get(str(skill_dir), "P")
        assert result is not None
        assert result["score"] == 70

    def test_cache_clear(self, tmp_path: Path):
        cache = FileCache(cache_dir=str(tmp_path / "cache"))
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")

        cache.set(str(test_file), "P", {"score": 90})
        assert cache.get(str(test_file), "P") is not None

        cache.clear()
        assert cache.get(str(test_file), "P") is None

    def test_cache_corrupt_file(self, tmp_path: Path):
        cache = FileCache(cache_dir=str(tmp_path / "cache"))
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")
        cache.set(str(test_file), "P", {"score": 90})

        cache_dir = tmp_path / "cache"
        for f in cache_dir.glob("*.json"):
            f.write_text("not valid json{{{")

        result = cache.get(str(test_file), "P")
        assert result is None
