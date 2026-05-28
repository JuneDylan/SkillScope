"""
工具模块单元测试
"""
from __future__ import annotations
import pytest
from pathlib import Path

from skillscope.utils.tokens import estimate_token_count, estimate_tokens_for_files
from skillscope.utils.parser import (
    extract_python_code, extract_prompt_content, has_try_except,
    count_functions, is_config_hardcoded,
)
from skillscope.utils.patterns import (
    SECRET_PATTERNS, DANGEROUS_FUNCTIONS, PROMPT_INJECTION_PATTERNS,
    VENDOR_SPECIFIC_APIS, INSECURE_NETWORK_PATTERNS,
    LOGGING_SENSITIVE_PATTERNS, ENCODING_PATTERNS,
)


class TestTokenEstimation:
    def test_empty_string(self):
        assert estimate_token_count("") == 0

    def test_basic_estimation(self):
        tokens = estimate_token_count("Hello, this is a test sentence.")
        assert tokens > 0

    def test_long_text(self):
        tokens = estimate_token_count("word " * 1000)
        assert tokens > 100

    def test_files_estimation(self, tmp_path: Path):
        (tmp_path / "a.py").write_text("print('hello')")
        (tmp_path / "b.py").write_text("x = 1 + 2")

        total = estimate_tokens_for_files(tmp_path, ["a.py", "b.py"])
        assert total > 0

    def test_single_file_estimation(self, tmp_path: Path):
        (tmp_path / "single.py").write_text("x = 1")
        total = estimate_tokens_for_files(tmp_path, ["single.py"], max_workers=1)
        assert total > 0

    def test_nonexistent_file(self, tmp_path: Path):
        total = estimate_tokens_for_files(tmp_path, ["nonexistent.py"])
        assert total == 0


class TestParser:
    def test_extract_python_code(self, tmp_path: Path):
        f = tmp_path / "test.py"
        f.write_text("x = 1\ny = 2\n")
        lines = extract_python_code(str(f))
        assert len(lines) == 2
        assert lines[0] == (1, "x = 1")

    def test_extract_python_code_non_py(self, tmp_path: Path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        lines = extract_python_code(str(f))
        assert lines == []

    def test_extract_prompt_content(self, tmp_path: Path):
        f = tmp_path / "prompt.md"
        f.write_text("You are an assistant", encoding="utf-8")
        content = extract_prompt_content(str(f))
        assert "assistant" in content

    def test_extract_prompt_nonexistent(self):
        content = extract_prompt_content("/nonexistent/file.md")
        assert content == ""

    def test_has_try_except(self, tmp_path: Path):
        f = tmp_path / "code.py"
        f.write_text("try:\n    pass\nexcept:\n    pass\n")
        assert has_try_except(str(f)) is True

    def test_has_no_try_except(self, tmp_path: Path):
        f = tmp_path / "code.py"
        f.write_text("x = 1\n")
        assert has_try_except(str(f)) is False

    def test_count_functions(self, tmp_path: Path):
        f = tmp_path / "code.py"
        f.write_text("def foo(): pass\ndef bar(): pass\nclass Baz: pass\n")
        assert count_functions(str(f)) == 2

    def test_is_config_hardcoded(self, tmp_path: Path):
        f = tmp_path / "code.py"
        f.write_text('temperature = 0.7\nmodel = "gpt-4"\n')
        hardcoded = is_config_hardcoded(str(f))
        assert len(hardcoded) > 0


class TestPatterns:
    def test_secret_patterns_exist(self):
        assert len(SECRET_PATTERNS) >= 10

    def test_dangerous_functions_exist(self):
        assert len(DANGEROUS_FUNCTIONS) >= 10
        patterns = [p[0] for p in DANGEROUS_FUNCTIONS]
        assert any("eval" in p for p in patterns)
        assert any("pickle" in p for p in patterns)

    def test_injection_patterns_exist(self):
        assert len(PROMPT_INJECTION_PATTERNS) >= 4

    def test_vendor_lock_patterns_exist(self):
        assert len(VENDOR_SPECIFIC_APIS) >= 5

    def test_insecure_network_patterns_exist(self):
        assert len(INSECURE_NETWORK_PATTERNS) >= 2

    def test_logging_sensitive_patterns_exist(self):
        assert len(LOGGING_SENSITIVE_PATTERNS) >= 2

    def test_encoding_patterns_exist(self):
        assert len(ENCODING_PATTERNS) >= 2

    def test_total_rule_count(self):
        total = (
            len(SECRET_PATTERNS)
            + len(DANGEROUS_FUNCTIONS)
            + len(PROMPT_INJECTION_PATTERNS)
            + len(VENDOR_SPECIFIC_APIS)
            + len(INSECURE_NETWORK_PATTERNS)
            + len(LOGGING_SENSITIVE_PATTERNS)
            + len(ENCODING_PATTERNS)
        )
        assert total >= 40
