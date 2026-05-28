"""
SkillScope Web GUI
基于 Flask 的可视化界面，支持扫描、报告展示、修复预览
"""
from __future__ import annotations

import webbrowser
from pathlib import Path

from skillscope.core.config import load_config
from skillscope.core.engine import SkillScopeEngine
from skillscope.core.models import SkillScopeConfig
from skillscope.reporters.html_reporter import generate_html_report


def create_app(config: SkillScopeConfig | None = None):
    try:
        from flask import Flask, jsonify, render_template_string, request
    except ImportError as err:
        raise ImportError(
            "Web GUI 需要 Flask，请运行: pip install skillscope[gui]"
        ) from err

    app = Flask(__name__)
    app.config["JSON_AS_ASCII"] = False

    @app.route("/")
    def index():
        return render_template_string(INDEX_HTML)

    @app.route("/api/scan", methods=["POST"])
    def api_scan():
        data = request.get_json(force=True)
        path = data.get("path", "").strip()
        if not path:
            return jsonify({"error": "请输入 Skill 路径"}), 400
        if not Path(path).exists():
            return jsonify({"error": f"路径不存在: {path}"}), 400

        fix_level = data.get("fix_level", "none")
        ai_enabled = data.get("ai_enabled", False)

        cfg = config or load_config()
        cfg.ai_enabled = ai_enabled

        try:
            engine = SkillScopeEngine(config=cfg)
            result = engine.audit(
                path,
                apply_fixes=False,
                fix_safety_level=fix_level,
            )
            return jsonify(result.model_dump())
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/fix", methods=["POST"])
    def api_fix():
        data = request.get_json(force=True)
        path = data.get("path", "").strip()
        fix_level = data.get("fix_level", "safe")
        if not path:
            return jsonify({"error": "请输入 Skill 路径"}), 400

        cfg = config or load_config()
        try:
            engine = SkillScopeEngine(config=cfg)
            result = engine.audit(
                path,
                apply_fixes=True,
                fix_safety_level=fix_level,
            )
            applied = len(list(result.patches))
            return jsonify({
                "applied": applied,
                "patches": [p.model_dump() for p in result.patches],
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/html_report", methods=["POST"])
    def api_html_report():
        data = request.get_json(force=True)
        path = data.get("path", "").strip()
        if not path:
            return jsonify({"error": "请输入 Skill 路径"}), 400

        cfg = config or load_config()
        cfg.ai_enabled = data.get("ai_enabled", False)
        try:
            engine = SkillScopeEngine(config=cfg)
            result = engine.audit(path, apply_fixes=False, fix_safety_level="none")
            html = generate_html_report(result)
            return html, 200, {"Content-Type": "text/html; charset=utf-8"}
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


def launch_gui(host: str = "127.0.0.1", port: int = 8501, config: SkillScopeConfig | None = None):
    app = create_app(config)
    url = f"http://{host}:{port}"
    print(f"SkillScope GUI 启动中: {url}")

    import threading
    def _open_browser():
        import time
        time.sleep(1.5)
        webbrowser.open(url)

    threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host=host, port=port, debug=False)


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SkillScope GUI</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
:root {
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
  --purple: #a855f7;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
.container { max-width: 1200px; margin: 0 auto; padding: 24px; }
h1 { font-size: 1.5rem; margin-bottom: 4px; }
.subtitle { color: var(--text-muted); font-size: 0.85rem; margin-bottom: 24px; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 20px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 768px) { .grid { grid-template-columns: 1fr; } }
.input-row { display: flex; gap: 12px; margin-bottom: 16px; }
.input-row input[type="text"] { flex: 1; padding: 10px 16px; border-radius: 8px; border: 1px solid var(--border); background: var(--bg); color: var(--text); font-size: 0.95rem; outline: none; }
.input-row input[type="text"]:focus { border-color: var(--blue); }
.btn { padding: 10px 24px; border: none; border-radius: 8px; font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: all 0.2s; }
.btn-primary { background: var(--blue); color: white; }
.btn-primary:hover { background: #2563eb; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-success { background: var(--green); color: white; }
.btn-success:hover { background: #16a34a; }
.btn-outline { background: transparent; color: var(--text-muted); border: 1px solid var(--border); }
.btn-outline:hover { border-color: var(--text-muted); }
.options-row { display: flex; gap: 16px; align-items: center; flex-wrap: wrap; margin-bottom: 16px; }
.options-row label { font-size: 0.85rem; color: var(--text-muted); display: flex; align-items: center; gap: 6px; }
.options-row select { padding: 6px 12px; border-radius: 6px; border: 1px solid var(--border); background: var(--bg); color: var(--text); font-size: 0.85rem; }
.options-row input[type="checkbox"] { accent-color: var(--blue); }
.score-big { text-align: center; }
.score-big .number { font-size: 4rem; font-weight: 800; }
.score-big .label { color: var(--text-muted); font-size: 0.9rem; }
.meta-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 16px; }
.meta-item { text-align: center; padding: 12px; background: rgba(255,255,255,0.03); border-radius: 8px; }
.meta-item .val { font-size: 1.4rem; font-weight: 700; }
.meta-item .lbl { font-size: 0.75rem; color: var(--text-muted); }
.dim-bar { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--border); }
.dim-bar:last-child { border-bottom: none; }
.dim-label { width: 120px; font-weight: 600; flex-shrink: 0; }
.dim-score { width: 50px; font-weight: 700; text-align: right; flex-shrink: 0; }
.dim-track { flex: 1; height: 8px; background: rgba(255,255,255,0.06); border-radius: 4px; overflow: hidden; }
.dim-fill { height: 100%; border-radius: 4px; transition: width 0.6s ease; }
.sub-scores { margin-left: 132px; display: flex; flex-wrap: wrap; gap: 8px; padding-bottom: 8px; }
.sub-tag { font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; background: rgba(255,255,255,0.05); }
.sev-section { margin-bottom: 16px; }
.sev-header { font-weight: 700; font-size: 1rem; padding: 8px 0; display: flex; align-items: center; gap: 8px; }
.sev-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.issue-item { padding: 12px 16px; margin: 8px 0; background: rgba(255,255,255,0.02); border-radius: 8px; border-left: 3px solid var(--border); }
.issue-item .cat { font-weight: 600; font-size: 0.85rem; }
.issue-item .msg { margin: 4px 0; }
.issue-item .loc { font-size: 0.8rem; color: var(--text-muted); }
.issue-item .hint { font-size: 0.8rem; color: var(--blue); margin-top: 4px; }
.issue-item .src { font-size: 0.7rem; color: var(--text-muted); float: right; }
.patch-item { padding: 12px 16px; margin: 8px 0; background: rgba(255,255,255,0.02); border-radius: 8px; }
.patch-item .file { font-weight: 600; color: var(--blue); }
.patch-item .desc { color: var(--text-muted); font-size: 0.85rem; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
.badge-safe { background: rgba(34,197,94,0.15); color: var(--green); }
.badge-suggested { background: rgba(234,179,8,0.15); color: var(--yellow); }
.badge-ai { background: rgba(59,130,246,0.15); color: var(--blue); }
.chart-wrap { position: relative; max-width: 380px; margin: 0 auto; }
.tab-bar { display: flex; gap: 4px; margin-bottom: 16px; }
.tab-btn { padding: 8px 16px; border: none; background: transparent; color: var(--text-muted); cursor: pointer; border-radius: 6px; font-size: 0.85rem; }
.tab-btn.active { background: var(--card); color: var(--text); }
.tab-content { display: none; }
.tab-content.active { display: block; }
.loading { text-align: center; padding: 48px; color: var(--text-muted); }
.loading .spinner { display: inline-block; width: 32px; height: 32px; border: 3px solid var(--border); border-top-color: var(--blue); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
#results { display: none; }
.error-msg { color: var(--red); padding: 16px; text-align: center; }
</style>
</head>
<body>
<div class="container">
  <h1>SkillScope</h1>
  <p class="subtitle">AI Skill 质量体检工具 &middot; 像 Lighthouse 一样检查你的 Skill</p>

  <div class="card">
    <div class="input-row">
      <input type="text" id="skillPath" placeholder="输入 Skill 路径（本地目录或文件）..." />
      <button class="btn btn-primary" id="scanBtn" onclick="runScan()">开始扫描</button>
    </div>
    <div class="options-row">
      <label>修复级别:
        <select id="fixLevel">
          <option value="none">不修复</option>
          <option value="safe">Safe</option>
          <option value="suggested">Suggested</option>
        </select>
      </label>
      <label><input type="checkbox" id="aiEnabled" /> AI Judge (DeepSeek)</label>
      <button class="btn btn-outline" onclick="downloadHTML()">下载 HTML 报告</button>
    </div>
  </div>

  <div id="loading" class="loading" style="display:none">
    <div class="spinner"></div>
    <p style="margin-top:12px">正在扫描分析中...</p>
  </div>

  <div id="errorBox" style="display:none"><div class="card"><p class="error-msg" id="errorText"></p></div></div>

  <div id="results">
    <div class="grid">
      <div class="card score-big">
        <div class="number" id="overallScore">-</div>
        <div class="label" id="overallLabel">总体评分 / 100</div>
        <div class="meta-grid">
          <div class="meta-item"><div class="val" style="color:var(--red)" id="critCount">0</div><div class="lbl">严重</div></div>
          <div class="meta-item"><div class="val" style="color:var(--orange)" id="warnCount">0</div><div class="lbl">警告</div></div>
          <div class="meta-item"><div class="val" style="color:var(--blue)" id="infoCount">0</div><div class="lbl">提示</div></div>
          <div class="meta-item"><div class="val" id="duration">-</div><div class="lbl">耗时</div></div>
        </div>
      </div>
      <div class="card">
        <div class="chart-wrap"><canvas id="radarChart"></canvas></div>
      </div>
    </div>

    <div class="card">
      <h3 style="margin-bottom:16px">维度评分</h3>
      <div id="dimBars"></div>
    </div>

    <div class="card">
      <div class="tab-bar">
        <button class="tab-btn active" onclick="switchTab('issues', this)">问题清单</button>
        <button class="tab-btn" onclick="switchTab('patches', this)">可自动修复</button>
      </div>
      <div id="tab-issues" class="tab-content active"></div>
      <div id="tab-patches" class="tab-content"></div>
    </div>
  </div>
</div>

<script>
let lastResult = null;
let radarChart = null;

function escapeHtml(s) {
  if (s == null) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function scoreColor(s) {
  if (s >= 90) return '#22c55e';
  if (s >= 70) return '#eab308';
  if (s >= 50) return '#f97316';
  return '#ef4444';
}

function scoreLevel(s) {
  if (s >= 90) return '优秀';
  if (s >= 70) return '良好';
  if (s >= 50) return '需改进';
  return '差';
}

async function runScan() {
  const path = document.getElementById('skillPath').value.trim();
  if (!path) { alert('请输入 Skill 路径'); return; }

  document.getElementById('scanBtn').disabled = true;
  document.getElementById('loading').style.display = '';
  document.getElementById('results').style.display = 'none';
  document.getElementById('errorBox').style.display = 'none';

  try {
    const resp = await fetch('/api/scan', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        path: path,
        fix_level: document.getElementById('fixLevel').value,
        ai_enabled: document.getElementById('aiEnabled').checked,
      })
    });
    const data = await resp.json();
    if (data.error) {
      document.getElementById('errorText').textContent = data.error;
      document.getElementById('errorBox').style.display = '';
    } else {
      lastResult = data;
      renderResults(data);
    }
  } catch(e) {
    document.getElementById('errorText').textContent = '请求失败: ' + e.message;
    document.getElementById('errorBox').style.display = '';
  } finally {
    document.getElementById('scanBtn').disabled = false;
    document.getElementById('loading').style.display = 'none';
  }
}

function renderResults(data) {
  document.getElementById('results').style.display = '';

  const score = data.overall_score;
  const el = document.getElementById('overallScore');
  el.textContent = score;
  el.style.color = scoreColor(score);
  document.getElementById('overallLabel').textContent = '总体评分 / 100 (' + scoreLevel(score) + ')';

  const issues = data.issues || [];
  const crit = issues.filter(i => i.severity === 'critical').length;
  const warn = issues.filter(i => i.severity === 'warning').length;
  const info = issues.filter(i => i.severity === 'info').length;
  document.getElementById('critCount').textContent = crit;
  document.getElementById('warnCount').textContent = warn;
  document.getElementById('infoCount').textContent = info;
  document.getElementById('duration').textContent = (data.scan_duration_ms || '-') + 'ms';

  renderRadar(data.dimension_scores);
  renderDimBars(data.dimension_scores);
  renderIssues(issues);
  renderPatches(data.patches || []);
}

function renderRadar(dimScores) {
  const labels = [], scores = [], colors = [];
  const order = ['P','S','X','F','C','M'];
  for (const d of order) {
    if (dimScores[d]) {
      labels.push(d + ' ' + dimScores[d].name);
      scores.push(dimScores[d].score);
      colors.push(scoreColor(dimScores[d].score));
    }
  }
  if (radarChart) radarChart.destroy();
  radarChart = new Chart(document.getElementById('radarChart').getContext('2d'), {
    type: 'radar',
    data: {
      labels: labels,
      datasets: [{
        data: scores,
        backgroundColor: 'rgba(59,130,246,0.15)',
        borderColor: 'rgba(59,130,246,0.8)',
        borderWidth: 2,
        pointBackgroundColor: colors,
        pointRadius: 5,
      }]
    },
    options: {
      responsive: true,
      scales: {
        r: {
          min: 0, max: 100,
          ticks: { stepSize: 20, color: '#94a3b8', backdropColor: 'transparent' },
          grid: { color: 'rgba(255,255,255,0.06)' },
          angleLines: { color: 'rgba(255,255,255,0.06)' },
          pointLabels: { color: '#e2e8f0', font: { size: 12 } }
        }
      },
      plugins: { legend: { display: false } }
    }
  });
}

function renderDimBars(dimScores) {
  const order = ['P','S','X','F','C','M'];
  let html = '';
  for (const d of order) {
    if (!dimScores[d]) continue;
    const ds = dimScores[d];
    const c = scoreColor(ds.score);
    html += '<div class="dim-bar"><div class="dim-label">' + d + ' ' + escapeHtml(ds.name) + '</div>';
    html += '<div class="dim-score" style="color:' + c + '">' + ds.score + '</div>';
    html += '<div class="dim-track"><div class="dim-fill" style="width:' + ds.score + '%;background:' + c + '"></div></div></div>';
    if (ds.sub_scores && Object.keys(ds.sub_scores).length > 0) {
      html += '<div class="sub-scores">';
      for (const [k,v] of Object.entries(ds.sub_scores)) {
        const sc = scoreColor(v);
        const label = escapeHtml(k.replace(/_ai$/, ' (AI)'));
        html += '<span class="sub-tag" style="color:' + sc + '">' + label + ': ' + v + '</span>';
      }
      html += '</div>';
    }
  }
  document.getElementById('dimBars').innerHTML = html;
}

function renderIssues(issues) {
  const groups = {critical: [], warning: [], info: []};
  for (const i of issues) { if (groups[i.severity]) groups[i.severity].push(i); }

  const sevConf = {
    critical: ['🔴 严重', 'var(--red)'],
    warning: ['🟠 警告', 'var(--orange)'],
    info: ['🔵 提示', 'var(--blue)'],
  };
  let html = '';
  for (const [sev, [label, color]] of Object.entries(sevConf)) {
    const items = groups[sev];
    if (!items.length) continue;
    html += '<div class="sev-section"><div class="sev-header"><span class="sev-dot" style="background:' + color + '"></span>' + label + ' (' + items.length + ')</div>';
    for (const item of items) {
      let badges = '';
      if (item.source === 'ai_judge') badges += '<span class="badge badge-ai">AI</span> ';
      if (item.auto_fixable) badges += '<span class="badge badge-safe">可修复</span>';
      const hint = item.fix_hint ? '<div class="hint">💡 ' + escapeHtml(item.fix_hint) + '</div>' : '';
      html += '<div class="issue-item" style="border-left-color:' + color + '">' +
        '<span class="src">' + badges + '</span>' +
        '<div class="cat">' + escapeHtml(item.category) + '</div>' +
        '<div class="msg">' + escapeHtml(item.message) + '</div>' +
        '<div class="loc">📍 ' + escapeHtml(item.location) + '</div>' +
        hint + '</div>';
    }
    html += '</div>';
  }
  if (!issues.length) html = '<p style="color:var(--text-muted);text-align:center;padding:24px">🎉 未发现问题</p>';
  document.getElementById('tab-issues').innerHTML = html;
}

function renderPatches(patches) {
  if (!patches.length) {
    document.getElementById('tab-patches').innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:24px">无可自动修复项</p>';
    return;
  }
  let html = '';
  for (const p of patches) {
    const cls = p.safety === 'safe' ? 'badge-safe' : 'badge-suggested';
    html += '<div class="patch-item"><span class="badge ' + cls + '">' + escapeHtml(p.safety) + '</span> <span class="file">' + escapeHtml(p.file_path) + '</span><div class="desc">' + escapeHtml(p.description) + '</div></div>';
  }
  document.getElementById('tab-patches').innerHTML = html;
}

function switchTab(name, btn) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  btn.classList.add('active');
}

async function downloadHTML() {
  const path = document.getElementById('skillPath').value.trim();
  if (!path) { alert('请先输入路径并扫描'); return; }
  try {
    const resp = await fetch('/api/html_report', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        path: path,
        ai_enabled: document.getElementById('aiEnabled').checked,
      })
    });
    const html = await resp.text();
    const blob = new Blob([html], {type: 'text/html'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'skillscope_report.html'; a.click();
    URL.revokeObjectURL(url);
  } catch(e) {
    alert('下载失败: ' + e.message);
  }
}

document.getElementById('skillPath').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') runScan();
});
</script>
</body>
</html>"""
