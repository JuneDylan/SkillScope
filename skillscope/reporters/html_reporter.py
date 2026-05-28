"""
HTML 报告生成器
生成单文件 HTML 报告，内嵌 CSS + JS + Chart.js 雷达图
"""
from __future__ import annotations

import json
from html import escape

from skillscope.core.models import AuditResult


def generate_html_report(result: AuditResult) -> str:
    dim_labels = []
    dim_scores = []
    dim_colors = []
    for dim, ds in result.dimension_scores.items():
        dim_labels.append(f"{dim} {escape(ds.name)}")
        dim_scores.append(ds.score)
        dim_colors.append(_score_color_hex(ds.score))

    sub_scores_data = {}
    for dim, ds in result.dimension_scores.items():
        if ds.sub_scores:
            sub_scores_data[dim] = {
                "name": ds.name,
                "subs": ds.sub_scores,
            }

    issues_by_severity = {"critical": [], "warning": [], "info": []}
    for issue in result.issues:
        sev = issue.severity.value
        if sev in issues_by_severity:
            issues_by_severity[sev].append({
                "category": issue.category,
                "message": issue.message,
                "location": issue.location,
                "fix_hint": issue.fix_hint,
                "auto_fixable": issue.auto_fixable,
                "source": issue.source,
            })

    patches_data = []
    for patch in result.patches:
        patches_data.append({
            "file_path": patch.file_path,
            "description": patch.description,
            "safety": patch.safety.value,
            "original": patch.original,
            "replacement": patch.replacement,
        })

    overall_color = _score_color_hex(result.overall_score)
    overall_level = (
        "优秀" if result.overall_score >= 90
        else "良好" if result.overall_score >= 70
        else "需改进" if result.overall_score >= 50
        else "差"
    )

    critical_count = len(issues_by_severity["critical"])
    warning_count = len(issues_by_severity["warning"])
    info_count = len(issues_by_severity["info"])

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SkillScope 体检报告 - {escape(result.skill_name)}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {{
  --bg: #0f172a;
  --card: #1e293b;
  --border: #334155;
  --text: #e2e8f0;
  --text-muted: #94a3b8;
  --green: #22c55e;
  --yellow: #eab308;
  --orange: #f97316;
  --red: #ef4444;
  --blue: #3b82f6;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
.container {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
h1 {{ font-size: 1.5rem; margin-bottom: 4px; }}
.subtitle {{ color: var(--text-muted); font-size: 0.9rem; margin-bottom: 24px; }}
.card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 20px; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
@media (max-width: 768px) {{ .grid {{ grid-template-columns: 1fr; }} }}
.score-big {{ text-align: center; }}
.score-big .number {{ font-size: 4rem; font-weight: 800; }}
.score-big .label {{ color: var(--text-muted); font-size: 0.9rem; }}
.meta-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 16px; }}
.meta-item {{ text-align: center; padding: 12px; background: rgba(255,255,255,0.03); border-radius: 8px; }}
.meta-item .val {{ font-size: 1.4rem; font-weight: 700; }}
.meta-item .lbl {{ font-size: 0.75rem; color: var(--text-muted); }}
.dim-bar {{ display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border); }}
.dim-bar:last-child {{ border-bottom: none; }}
.dim-label {{ width: 120px; font-weight: 600; flex-shrink: 0; }}
.dim-score {{ width: 50px; font-weight: 700; text-align: right; flex-shrink: 0; }}
.dim-track {{ flex: 1; height: 8px; background: rgba(255,255,255,0.06); border-radius: 4px; overflow: hidden; }}
.dim-fill {{ height: 100%; border-radius: 4px; transition: width 0.6s ease; }}
.sub-scores {{ margin-left: 132px; display: flex; flex-wrap: wrap; gap: 8px; padding-bottom: 8px; }}
.sub-tag {{ font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; background: rgba(255,255,255,0.05); }}
.sev-section {{ margin-bottom: 16px; }}
.sev-header {{ font-weight: 700; font-size: 1rem; padding: 8px 0; display: flex; align-items: center; gap: 8px; }}
.sev-dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; }}
.issue-item {{ padding: 12px 16px; margin: 8px 0; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid var(--border); }}
.issue-item .cat {{ font-weight: 600; font-size: 0.85rem; }}
.issue-item .msg {{ margin: 4px 0; }}
.issue-item .loc {{ font-size: 0.8rem; color: var(--text-muted); }}
.issue-item .hint {{ font-size: 0.8rem; color: var(--blue); margin-top: 4px; }}
.issue-item .src {{ font-size: 0.7rem; color: var(--text-muted); float: right; }}
.patch-item {{ padding: 12px 16px; margin: 8px 0; background: rgba(255,255,255,0.02); border-radius: 8px; }}
.patch-item .file {{ font-weight: 600; color: var(--blue); }}
.patch-item .desc {{ color: var(--text-muted); font-size: 0.85rem; }}
.badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }}
.badge-safe {{ background: rgba(34,197,94,0.15); color: var(--green); }}
.badge-suggested {{ background: rgba(234,179,8,0.15); color: var(--yellow); }}
.badge-ai {{ background: rgba(59,130,246,0.15); color: var(--blue); }}
.chart-wrap {{ position: relative; max-width: 380px; margin: 0 auto; }}
.tab-bar {{ display: flex; gap: 4px; margin-bottom: 16px; }}
.tab-btn {{ padding: 8px 16px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; border-radius: 6px; font-size: 0.85rem; }}
.tab-btn.active {{ background: var(--card); color: var(--text); }}
.tab-content {{ display: none; }}
.tab-content.active {{ display: block; }}
</style>
</head>
<body>
<div class="container">
  <h1>SkillScope 体检报告</h1>
  <p class="subtitle">{escape(result.skill_name)} &middot; {result.skill_type.value} &middot; {result.audit_timestamp[:19]}</p>

  <div class="grid">
    <div class="card score-big">
      <div class="number" style="color:{overall_color}">{result.overall_score}</div>
      <div class="label">总体评分 / 100 ({overall_level})</div>
      <div class="meta-grid">
        <div class="meta-item"><div class="val" style="color:var(--red)">{critical_count}</div><div class="lbl">严重</div></div>
        <div class="meta-item"><div class="val" style="color:var(--orange)">{warning_count}</div><div class="lbl">警告</div></div>
        <div class="meta-item"><div class="val" style="color:var(--blue)">{info_count}</div><div class="lbl">提示</div></div>
        <div class="meta-item"><div class="val">{result.scan_duration_ms or '-'}ms</div><div class="lbl">耗时</div></div>
      </div>
    </div>
    <div class="card">
      <div class="chart-wrap">
        <canvas id="radarChart"></canvas>
      </div>
    </div>
  </div>

  <div class="card">
    <h3 style="margin-bottom:16px">维度评分</h3>
    {_build_dimension_bars(result, sub_scores_data)}
  </div>

  <div class="card">
    <div class="tab-bar">
      <button class="tab-btn active" onclick="switchTab('issues', this)">问题清单 ({len(result.issues)})</button>
      <button class="tab-btn" onclick="switchTab('patches', this)">可自动修复 ({len(result.patches)})</button>
    </div>
    <div id="tab-issues" class="tab-content active">
      {_build_issues_html(issues_by_severity)}
    </div>
    <div id="tab-patches" class="tab-content">
      {_build_patches_html(patches_data)}
    </div>
  </div>
</div>

<script>
const ctx = document.getElementById('radarChart').getContext('2d');
new Chart(ctx, {{
  type: 'radar',
  data: {{
    labels: {json.dumps(dim_labels)},
    datasets: [{{
      data: {json.dumps(dim_scores)},
      backgroundColor: 'rgba(59,130,246,0.15)',
      borderColor: 'rgba(59,130,246,0.8)',
      borderWidth: 2,
      pointBackgroundColor: {json.dumps(dim_colors)},
      pointRadius: 5,
    }}]
  }},
  options: {{
    responsive: true,
    scales: {{
      r: {{
        min: 0, max: 100,
        ticks: {{ stepSize: 20, color: '#94a3b8', backdropColor: 'transparent' }},
        grid: {{ color: 'rgba(255,255,255,0.06)' }},
        angleLines: {{ color: 'rgba(255,255,255,0.06)' }},
        pointLabels: {{ color: '#e2e8f0', font: {{ size: 12 }} }}
      }}
    }},
    plugins: {{ legend: {{ display: false }} }}
  }}
}});

function switchTab(name, btn) {{
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
}}
</script>
</body>
</html>"""
    return html


def _score_color_hex(score: int) -> str:
    if score >= 90:
        return "#22c55e"
    if score >= 70:
        return "#eab308"
    if score >= 50:
        return "#f97316"
    return "#ef4444"


def _build_dimension_bars(result: AuditResult, sub_scores_data: dict) -> str:
    parts = []
    for dim, ds in result.dimension_scores.items():
        color = _score_color_hex(ds.score)
        parts.append(f"""
      <div class="dim-bar">
        <div class="dim-label">{dim} {escape(ds.name)}</div>
        <div class="dim-score" style="color:{color}">{ds.score}</div>
        <div class="dim-track"><div class="dim-fill" style="width:{ds.score}%;background:{color}"></div></div>
      </div>""")
        if ds.sub_scores:
            sub_tags = []
            for k, v in ds.sub_scores.items():
                sc = _score_color_hex(v)
                label = escape(k.replace("_ai", " (AI)"))
                sub_tags.append(f'<span class="sub-tag" style="color:{sc}">{label}: {v}</span>')
            parts.append(f'<div class="sub-scores">{"".join(sub_tags)}</div>')
    return "".join(parts)


def _build_issues_html(issues_by_severity: dict) -> str:
    sev_config = {
        "critical": ("🔴 严重", "var(--red)"),
        "warning": ("🟠 警告", "var(--orange)"),
        "info": ("🔵 提示", "var(--blue)"),
    }
    parts = []
    for sev, (label, color) in sev_config.items():
        items = issues_by_severity.get(sev, [])
        if not items:
            continue
        parts.append(f'<div class="sev-section"><div class="sev-header"><span class="sev-dot" style="background:{color}"></span>{label} ({len(items)})</div>')
        for item in items:
            src_badge = ""
            if item.get("source") == "ai_judge":
                src_badge = '<span class="badge badge-ai">AI</span>'
            fixable_badge = ""
            if item.get("auto_fixable"):
                fixable_badge = '<span class="badge badge-safe">可修复</span>'
            hint_html = f'<div class="hint">💡 {escape(item["fix_hint"])}</div>' if item.get("fix_hint") else ""
            parts.append(f"""
        <div class="issue-item" style="border-left-color:{color}">
          <span class="src">{src_badge} {fixable_badge}</span>
          <div class="cat">{escape(item["category"])}</div>
          <div class="msg">{escape(item["message"])}</div>
          <div class="loc">📍 {escape(item["location"])}</div>
          {hint_html}
        </div>""")
        parts.append("</div>")
    if not any(issues_by_severity.values()):
        parts.append('<p style="color:var(--text-muted);text-align:center;padding:24px">🎉 未发现问题</p>')
    return "".join(parts)


def _build_patches_html(patches_data: list) -> str:
    if not patches_data:
        return '<p style="color:var(--text-muted);text-align:center;padding:24px">无可自动修复项</p>'
    parts = []
    for p in patches_data:
        safety_class = "badge-safe" if p["safety"] == "safe" else "badge-suggested"
        parts.append(f"""
      <div class="patch-item">
        <span class="badge {safety_class}">{p["safety"]}</span>
        <span class="file">{escape(p["file_path"])}</span>
        <div class="desc">{escape(p["description"])}</div>
      </div>""")
    return "".join(parts)
