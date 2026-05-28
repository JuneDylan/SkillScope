"""
GUI 单元测试
使用 Flask test client，无需启动真实服务器
"""
from __future__ import annotations

from pathlib import Path

import pytest

from skillscope.core.config import load_config


@pytest.fixture
def client(tmp_path: Path):
    try:
        from skillscope.gui.app import create_app
    except ImportError:
        pytest.skip("Flask not installed")

    config = load_config()
    app = create_app(config=config)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture
def sample_skill(tmp_path: Path):
    skill_dir = tmp_path / "sample-skill"
    skill_dir.mkdir()
    (skill_dir / "README.md").write_text("# Sample Skill\n\nA test skill.\n")
    (skill_dir / "system_prompt.md").write_text("你是一个助手。\n")
    return skill_dir


class TestGUIIndex:
    def test_index_page(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"SkillScope" in resp.data


class TestGUIScanAPI:
    def test_scan_missing_path(self, client):
        resp = client.post("/api/scan", json={})
        assert resp.status_code == 400

    def test_scan_nonexistent_path(self, client):
        resp = client.post("/api/scan", json={"path": "/nonexistent/path"})
        assert resp.status_code == 400

    def test_scan_valid_skill(self, client, sample_skill):
        resp = client.post("/api/scan", json={"path": str(sample_skill)})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["skill_name"] == "sample-skill"
        assert "overall_score" in data
        assert "dimension_scores" in data

    def test_scan_with_fix_level(self, client, sample_skill):
        resp = client.post("/api/scan", json={
            "path": str(sample_skill),
            "fix_level": "safe",
        })
        assert resp.status_code == 200

    def test_scan_with_ai_enabled(self, client, sample_skill):
        resp = client.post("/api/scan", json={
            "path": str(sample_skill),
            "ai_enabled": True,
        })
        assert resp.status_code == 200


class TestGUIFixAPI:
    def test_fix_missing_path(self, client):
        resp = client.post("/api/fix", json={})
        assert resp.status_code == 400

    def test_fix_valid_skill(self, client, sample_skill):
        resp = client.post("/api/fix", json={
            "path": str(sample_skill),
            "fix_level": "safe",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "applied" in data


class TestGUIHTMLReportAPI:
    def test_html_report_missing_path(self, client):
        resp = client.post("/api/html_report", json={})
        assert resp.status_code == 400

    def test_html_report_valid_skill(self, client, sample_skill):
        resp = client.post("/api/html_report", json={"path": str(sample_skill)})
        assert resp.status_code == 200
        assert resp.content_type.startswith("text/html")
        assert b"SkillScope" in resp.data
