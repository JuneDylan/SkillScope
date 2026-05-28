"""
JSON 报告生成器
"""
from __future__ import annotations

import json

from skillscope.core.models import AuditResult


def generate_json_report(result: AuditResult) -> str:
    return json.dumps(result.model_dump(), indent=2, ensure_ascii=False, default=str)
