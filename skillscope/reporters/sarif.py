"""
SARIF 2.1.0 报告生成器
兼容 GitHub Code Scanning 和主流安全平台
"""
from __future__ import annotations

import json

from skillscope.core.models import AuditResult


def generate_sarif_report(result: AuditResult, tool_name: str = "SkillScope") -> str:
    rules = {}
    for issue in result.issues:
        if issue.rule_id and issue.rule_id not in rules:
            rules[issue.rule_id] = {
                "id": issue.rule_id,
                "name": issue.category,
                "shortDescription": {"text": issue.message},
                "defaultConfiguration": {
                    "level": _severity_to_sarif_level(issue.severity.value)
                },
            }

    results = []
    for issue in result.issues:
        location = _parse_location(issue.location)
        results.append({
            "ruleId": issue.rule_id or issue.category,
            "level": _severity_to_sarif_level(issue.severity.value),
            "message": {"text": issue.message + (f"\nFix: {issue.fix_hint}" if issue.fix_hint else "")},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": location["uri"]},
                    "region": {"startLine": location.get("line", 1)} if location.get("line") else {}
                }
            }],
        })

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": tool_name,
                    "informationUri": "https://github.com/skillscope/skillscope",
                    "rules": list(rules.values()),
                }
            },
            "results": results,
        }]
    }

    return json.dumps(sarif, indent=2, ensure_ascii=False)


def _severity_to_sarif_level(severity: str) -> str:
    mapping = {"critical": "error", "warning": "warning", "info": "note"}
    return mapping.get(severity, "warning")


def _parse_location(location: str) -> dict:
    import re as _re
    m = _re.search(r":(\d+)\s*$", location)
    if m:
        line_num = int(m.group(1))
        uri = location[: m.start()]
        return {"uri": uri, "line": line_num}
    return {"uri": location}
