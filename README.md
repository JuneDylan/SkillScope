<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+" />
  <img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="Apache 2.0" />
  <img src="https://img.shields.io/badge/tests-137%20passed-brightgreen" alt="137 tests passed" />
  <img src="https://img.shields.io/badge/rules-45%2B-orange" alt="45+ rules" />
</p>

<p align="center">English | <a href="README_zh.md">中文</a></p>

<h1 align="center">SkillScope</h1>

<p align="center"><strong>Lighthouse for AI Skills — Audit, Score, and Auto-Fix Your Agent Skills</strong></p>

<p align="center">
  SkillScope is a <strong>quality audit and auto-fix tool</strong> designed for AI Agent / Skill / MCP / Prompt projects.<br/>
  It performs deep scanning across 6 dimensions × 30+ sub-dimensions, delivering quantified scores, actionable suggestions, and safe automated fixes.
</p>

---

## Why SkillScope?

AI Agents and Skills are exploding, yet lack unified quality standards:

- **Prompt Injection**: User input concatenated directly into LLM instructions, creating security vulnerabilities
- **Secrets Leaks**: API keys hardcoded in source code, ready to be exposed
- **Hallucination Induction**: Prompts containing phrases like "make up" or "guess" that encourage model hallucinations
- **Vendor Lock-in**: Deep coupling with OpenAI/Claude-specific APIs, making migration prohibitively expensive
- **No Tests**: Core logic without unit tests, making refactoring a minefield

SkillScope catches these issues automatically in your CI pipeline — just like ESLint for JavaScript or Bandit for Python security.

---

## Key Features

- **6-Dimension Audit**: Prompt Quality (P) / Security (S) / Maintainability (X) / Performance (F) / Correctness (C) / Compatibility (M)
- **30+ Sub-dimensions**: Each dimension breaks down into 4-7 sub-items for precise root-cause identification
- **45+ Detection Rules**: Covering secrets leaks, dangerous functions, prompt injection, deserialization attacks, and more
- **AI Judge**: Integrated DeepSeek/OpenAI LLMs for semantic-level prompt quality and hallucination risk assessment
- **Auto-Fix**: Three-tier safety system (Safe / Suggested / Dangerous) with one-click patch application
- **Web GUI**: Built-in Flask dashboard with radar charts, issue lists, and fix previews
- **Multi-format Reports**: Console / JSON / SARIF 2.1.0 / HTML (with Chart.js radar charts)
- **CI Integration**: GitHub Actions + SARIF native integration with Code Scanning
- **Incremental Cache**: File-hash-based caching for sub-second repeat scans
- **Parallel Analysis**: ThreadPoolExecutor for multi-dimensional parallelism — 3-5x speedup on large projects
- **Plugin Architecture**: Dynamic analyzer discovery for community-contributed dimensions

---

## Installation

```bash
# Core (deterministic analysis + basic fixes + Console/JSON/SARIF reports)
pip install skillscope

# With AI enhancement (LLM-as-a-Judge semantic analysis, requires DEEPSEEK_API_KEY)
pip install skillscope[ai]

# With Web GUI (Flask dashboard)
pip install skillscope[gui]

# Development (tests, linting)
pip install skillscope[dev]

# Everything
pip install skillscope[all]
```

Install from source:

```bash
git clone https://github.com/JuneDylan/SkillScope.git
cd SkillScope
pip install -e ".[all]"
```

---

## Quick Start

### 1. Scan a Skill

```bash
# Scan a local directory
skillscope scan ./my-skill

# Scan a single file
skillscope scan ./system_prompt.md

# Generate SARIF report (for GitHub Code Scanning)
skillscope scan ./my-skill --format sarif --output report.sarif

# Generate HTML report
skillscope scan ./my-skill --format html --output report.html

# Apply safe-level auto-fixes
skillscope scan ./my-skill --fix safe --apply-fixes

# Enable AI Judge (requires DEEPSEEK_API_KEY)
skillscope scan ./my-skill --ai-enabled
```

### 2. Launch Web GUI

```bash
skillscope gui
# Opens http://127.0.0.1:8501 in your browser
```

### 3. Generate Config File

```bash
skillscope config --init
```

Creates `skillscope.yaml` for customizing rules, weights, and thresholds:

```yaml
version: "1.0"
preset: general
dimensions:
  P:
    enabled: true
    weight: 0.20
    threshold: 70
  S:
    enabled: true
    weight: 0.25
    threshold: 80
fail_threshold: 70
parallel: true
ai_enabled: false
```

---

## 6-Dimension Assessment Framework

| Dimension | ID | Weight | Sub-dims | Key Detection Items |
|-----------|-----|--------|----------|-------------------|
| **Prompt Quality** | P | 20% | 4 | Prompt injection, token efficiency, role definition clarity, instruction specificity |
| **Security** | S | 25% | 7 | 12 secret patterns, 14 dangerous functions, CVE dependencies, MCP permissions, hardcoded configs, insecure networking, log leaks |
| **Maintainability** | X | 15% | 5 | README quality, test coverage, version management, docstring coverage, cyclomatic complexity |
| **Performance** | F | 15% | 4 | Token cost estimation, in-loop API calls, sync blocking, streaming output |
| **Correctness** | C | 15% | 6 | Exception handling, type annotations, hallucination-inducing words, output validation, resource leaks, input sanitization |
| **Compatibility** | M | 10% | 4 | 7 vendor-lock APIs, protocol versions, platform lock-in, encoding compatibility |

All weights and thresholds are customizable in `skillscope.yaml`.

---

## AI Judge (LLM-as-a-Judge)

SkillScope supports calling LLMs for semantic-level deep analysis, bridging the gaps of deterministic rules:

| AI Judge | Dimension | What It Evaluates |
|----------|-----------|-------------------|
| **PromptQualityJudge** | P | Semantic clarity, instruction specificity, injection risk (context-aware) |
| **HallucinationJudge** | C | Hallucination-inducing expressions, contradictory instructions, missing factual constraints |

### Configuration

```bash
# Set API Key (supports DeepSeek and OpenAI)
export DEEPSEEK_API_KEY=sk-xxx
# or
export OPENAI_API_KEY=sk-xxx

# Enable during scan
skillscope scan ./my-skill --ai-enabled
```

### Features

- **Timeout Control**: Default 30s, customizable
- **Auto Retry**: Up to 2 retries with exponential backoff
- **Graceful Degradation**: Falls back to deterministic analysis when API is unavailable
- **Token Tracking**: Logs input/output tokens and latency

---

## Auto-Fix

SkillScope implements a three-tier fix safety system:

| Level | Description | Examples |
|-------|-------------|---------|
| **Safe** | High confidence, no side effects | Secrets → env vars, generate `.gitignore` |
| **Suggested** | Recommended fix, requires human semantic review | `eval()` → `ast.literal_eval()` |
| **Dangerous** | May change business semantics, must be human-reviewed | Architecture-level refactoring, prompt content rewriting |

```bash
# Preview fixable items only (no file modifications)
skillscope scan ./my-skill --fix safe

# Apply safe-level fixes to the filesystem
skillscope scan ./my-skill --fix safe --apply-fixes

# Preview suggested-level fixes (includes safe)
skillscope scan ./my-skill --fix suggested
```

---

## Web GUI

Launch the built-in visual dashboard:

```bash
skillscope gui
```

Features:
- Enter a Skill path and scan with one click
- Chart.js radar chart for 6-dimension scores
- Issues grouped by severity (Critical / Warning / Info)
- Fix preview and one-click apply
- Download HTML reports

---

## Output Formats

| Format | Use Case | Command |
|--------|----------|---------|
| **Console** | Local development | `--format console` (default) |
| **JSON** | Machine parsing, post-processing | `--format json` |
| **SARIF** | GitHub Code Scanning | `--format sarif` |
| **HTML** | Browser viewing, sharing | `--format html` |

---

## CI/CD Integration

### GitHub Actions

```yaml
name: SkillScope Audit
on: [push, pull_request]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install skillscope
      - run: skillscope scan . --fail-threshold 70 --format sarif --output skillscope.sarif
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: skillscope.sarif
```

### pre-commit hook

```yaml
repos:
  - repo: local
    hooks:
      - id: skillscope
        name: SkillScope Audit
        entry: skillscope scan . --fail-threshold 70
        language: system
        pass_filenames: false
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      SkillScope CLI                           │
├──────────────────────────────────────────────────────────────┤
│  Core Engine (Hybrid: Deterministic Analysis + AI Judge)     │
│  ├── Registry: Dynamic analyzer discovery & registration      │
│  ├── Config: YAML / Preset / Env var three-tier config       │
│  ├── Loader: Parallel file scan + Token estimation + AST     │
│  ├── Cache: File-hash incremental cache for sub-second scans │
│  └── FixManager: Three-tier safety fix filtering + Patch     │
├──────────────────────────────────────────────────────────────┤
│  Analyzers (6 dims × 4-7 sub-dims = 30+ sub-dimensions)     │
│  ├── PromptAnalyzer: Injection / Token / Clarity / Specificity│
│  ├── SecurityScanner: Secrets / Dangerous funcs / Deps / MCP │
│  │                  / Insecure network / Log leaks / Config   │
│  ├── MaintainabilityAnalyzer: Docs / Tests / Version / Docs  │
│  ├── PerformanceAnalyzer: Cost / API efficiency / Latency    │
│  ├── CorrectnessAnalyzer: Exceptions / Types / Hallucination │
│  └── CompatibilityAnalyzer: Vendor lock / Protocol / Platform│
├──────────────────────────────────────────────────────────────┤
│  AI Judges (LLM-as-a-Judge)                                  │
│  ├── PromptQualityJudge: Semantic clarity / Specificity      │
│  └── HallucinationJudge: Hallucination risk / Contradictions │
├──────────────────────────────────────────────────────────────┤
│  Reporters: Console / JSON / SARIF 2.1.0 / HTML              │
├──────────────────────────────────────────────────────────────┤
│  Web GUI: Flask + Chart.js radar charts + Fix preview         │
└──────────────────────────────────────────────────────────────┘
```

---

## Detection Rules Overview

### Secrets Leaks (12 patterns)
OpenAI API Key / Anthropic Key / Generic API Key / Password / AWS Access Key / GitHub Token / JWT Token / Private Key / Slack Token / Stripe Key / Google API Key / Slack Webhook

### Dangerous Functions (14 types)
eval / exec / os.system / subprocess.call / subprocess.run / subprocess.Popen / input / pickle.loads / pickle.load / yaml.load / marshal.loads / \_\_import\_\_ / compile / shelve.open

### Prompt Injection (5 patterns)
f-string interpolation / .format() / % formatting / string concatenation / SSTI template injection

### Vendor Lock-in (7 APIs)
OpenAI functions / tool_choice / json_schema / Claude top_k / Azure Endpoint / AWS Bedrock / Vertex AI

### Other Rules
Insecure network communication (3) / Sensitive info in logs (2) / Encoding compatibility (2) / Resource leaks / Input sanitization / Streaming output / ...

---

## Configuration & Presets

### Available Presets

| Preset | Use Case |
|--------|----------|
| `general` | General AI Skill projects (default) |

```bash
skillscope scan ./my-skill --preset general
```

### Environment Variable Overrides

```bash
export SKILLSCOPE_PRESET=general
export SKILLSCOPE_CONFIG=./my-skillscope.yaml
export SKILLSCOPE_PARALLEL=true
export SKILLSCOPE_AI_ENABLED=true
export DEEPSEEK_API_KEY=sk-xxx
skillscope scan ./my-skill
```

---

## Project Structure

```
skillscope/
├── __init__.py              # Package entry, version
├── __main__.py              # python -m skillscope entry
├── cli.py                   # CLI commands (scan/config/gui)
├── core/
│   ├── engine.py            # Hybrid analysis engine
│   ├── models.py            # Data models (Pydantic v2)
│   ├── config.py            # Config loading & merging
│   ├── loader.py            # Skill file scanning & token estimation
│   └── registry.py          # Dynamic analyzer registry
├── analyzers/
│   ├── base.py              # Analyzer base class
│   ├── prompt.py            # Prompt quality analyzer
│   ├── security.py          # Security scanner
│   ├── maintainability.py   # Maintainability analyzer
│   ├── performance.py       # Performance analyzer
│   ├── correctness.py       # Correctness analyzer
│   └── compatibility.py     # Compatibility analyzer
├── ai_judges/
│   ├── base.py              # AI Judge base (timeout/retry/degradation)
│   ├── prompt_judge.py      # Prompt quality AI Judge
│   └── hallucination_judge.py # Hallucination risk AI Judge
├── fixers/
│   ├── base.py              # Fixer base class
│   ├── manager.py           # Fix manager
│   ├── security_fixer.py    # Security fixer
│   └── prompt_fixer.py      # Prompt fixer
├── reporters/
│   ├── console.py           # Console report (Lighthouse-style)
│   ├── json_reporter.py     # JSON report
│   ├── sarif.py             # SARIF 2.1.0 report
│   └── html_reporter.py     # HTML report (with Chart.js)
├── gui/
│   └── app.py               # Flask Web GUI
└── utils/
    ├── patterns.py          # 45+ detection rule pattern library
    ├── parser.py            # Code parsing utilities
    ├── tokens.py            # Token estimation (tiktoken + fallback)
    └── cache.py             # File-hash incremental cache
```

---

## Roadmap

### v0.2.x (Current)
- [x] 6-dimension assessment framework (30+ sub-dimensions)
- [x] 45+ detection rules
- [x] Auto-fix engine (Safe / Suggested / Dangerous)
- [x] AI Judge (Prompt quality + Hallucination risk)
- [x] SARIF / JSON / Console / HTML reports
- [x] Web GUI (Flask + Chart.js)
- [x] Configuration system + presets
- [x] Parallel scanning + incremental cache
- [x] Plugin registry
- [x] CI/CD integration

### v0.3.x (Near-term)
- [ ] tree-sitter AST semantic analysis (data flow tracking)
- [ ] OSV API real-time vulnerability queries
- [ ] Embedding-based prompt redundancy detection
- [ ] VS Code extension
- [ ] More industry presets

### v0.4.x (Long-term)
- [ ] Team Dashboard (trend analysis, tech debt board)
- [ ] Industry compliance preset library (finance, healthcare, education)
- [ ] Advanced architecture refactoring suggestions (commercial)

---

## Open Source & Commercial

SkillScope follows an **Open Core** model:

| Feature | Open Source (Apache-2.0) | Commercial |
|---------|--------------------------|------------|
| 6-dimension assessment engine | ✅ | ✅ |
| 45+ detection rules | ✅ | ✅ |
| AI Judge (DeepSeek/OpenAI) | ✅ | ✅ |
| Auto-fix (Safe/Suggested) | ✅ | ✅ |
| SARIF / JSON / HTML reports | ✅ | ✅ |
| Web GUI | ✅ | ✅ |
| CI integration | ✅ | ✅ |
| Industry compliance presets | ❌ | ✅ |
| Team Dashboard | ❌ | ✅ |
| Private deployment + offline LLM | ❌ | ✅ |
| Advanced architecture refactoring | ❌ | ✅ |

---

## Contributing

We welcome all forms of contribution! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

- **Report Issues**: [GitHub Issues](https://github.com/JuneDylan/SkillScope/issues)
- **Submit PRs**: Ensure `pytest tests/` and `ruff check .` pass
- **Contribute Rules**: Add new detection patterns in `skillscope/utils/patterns.py`
- **Contribute Presets**: Add general-purpose presets in `presets/open-source/`

Development setup:

```bash
git clone https://github.com/JuneDylan/SkillScope.git
cd SkillScope
pip install -e ".[all]"
pytest tests/ -v -o addopts=""
ruff check .
```

---

## License

[Apache-2.0](LICENSE)

---

> **Every AI Skill deserves a quality check.**
