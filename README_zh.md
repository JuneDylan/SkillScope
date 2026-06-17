<p align="center">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+" />
  <img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="Apache 2.0" />
  <img src="https://img.shields.io/badge/tests-137%20passed-brightgreen" alt="137 tests passed" />
  <img src="https://img.shields.io/badge/rules-45%2B-orange" alt="45+ rules" />
</p>

<p align="center"><a href="README_EN.md">English</a> | 中文</p>

<h1 align="center">SkillScope</h1>

<p align="center"><strong>像 Lighthouse 检查网页一样，检查你的 AI Skill</strong></p>

<p align="center">
  SkillScope 是一个专为 AI Agent / Skill / MCP / Prompt 项目设计的<strong>质量体检与自动修复工具</strong>。<br/>
  从 6 个维度 × 30+ 子维度深度扫描，给出可量化评分、可操作建议，并支持安全自动修复。
</p>

---

## 为什么需要 SkillScope？

AI Agent 和 Skill 正在爆发式增长，但缺乏统一的质量标准：

- **Prompt 注入**：用户输入直接拼接到 LLM 指令中，存在安全漏洞
- **Secrets 泄露**：API Key 硬编码在代码中，随时可能被泄露
- **幻觉诱导**：Prompt 中包含"编造""猜测"等诱导模型产生幻觉的表述
- **厂商锁定**：深度绑定 OpenAI/Claude 特有 API，迁移成本极高
- **缺乏测试**：核心逻辑没有单元测试，重构如履薄冰

SkillScope 帮你在 CI 中自动检测这些问题，就像 ESLint 检查 JavaScript、Bandit 检查 Python 安全一样。

---

## 核心特性

- **六维体检**：Prompt 质量 (P) / 安全性 (S) / 可维护性 (X) / 性能 (F) / 正确性 (C) / 兼容性 (M)
- **30+ 子维度**：每个维度细分 4-7 个子项，精准定位问题根因
- **45+ 检测规则**：覆盖 Secrets 泄露、危险函数、Prompt 注入、反序列化攻击等
- **AI Judge**：集成 DeepSeek/OpenAI 大模型，语义级 Prompt 质量与幻觉风险评估
- **自动修复**：三级安全体系 (Safe / Suggested / Dangerous)，一键应用安全补丁
- **Web GUI**：内置 Flask 可视化界面，雷达图 + 问题清单 + 修复预览
- **多格式报告**：Console / JSON / SARIF 2.1.0 / HTML（含 Chart.js 雷达图）
- **CI 集成**：GitHub Actions + SARIF 原生对接 Code Scanning
- **增量缓存**：基于文件哈希，重复扫描秒级完成
- **并行分析**：ThreadPoolExecutor 多维度并行，大项目 3-5x 提速
- **插件化架构**：动态发现分析器，社区可自定义扩展维度

---

## 安装

```bash
# 基础版（确定性分析 + 基础修复 + Console/JSON/SARIF 报告）
pip install skillscope

# 含 AI 增强（LLM-as-a-Judge 语义分析，需 DEEPSEEK_API_KEY）
pip install skillscope[ai]

# 含 Web GUI（Flask 可视化界面）
pip install skillscope[gui]

# 开发版（含测试、lint）
pip install skillscope[dev]

# 全部功能
pip install skillscope[all]
```

从源码安装：

```bash
git clone https://github.com/skillscope/skillscope.git
cd skillscope
pip install -e ".[all]"
```

---

## 快速开始

### 1. 扫描一个 Skill

```bash
# 扫描本地目录
skillscope scan ./my-skill

# 扫描单文件
skillscope scan ./system_prompt.md

# 生成 SARIF 报告（用于 GitHub Code Scanning）
skillscope scan ./my-skill --format sarif --output report.sarif

# 生成 HTML 报告
skillscope scan ./my-skill --format html --output report.html

# 应用安全级别的自动修复
skillscope scan ./my-skill --fix safe --apply-fixes

# 启用 AI Judge（需设置 DEEPSEEK_API_KEY）
skillscope scan ./my-skill --ai-enabled
```

### 2. 启动 Web GUI

```bash
skillscope gui
# 浏览器自动打开 http://127.0.0.1:8501
```

### 3. 生成配置文件

```bash
skillscope config --init
```

生成 `skillscope.yaml`，可自定义规则、权重、阈值：

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

## 六维评估体系

| 维度 | 标识 | 权重 | 子维度数 | 关键检测项 |
|------|------|------|---------|-----------|
| **Prompt 质量** | P | 20% | 4 | Prompt 注入、Token 效率、角色定义清晰度、指令特异性 |
| **安全性** | S | 25% | 7 | 12 种 Secrets 模式、14 种危险函数、CVE 依赖、MCP 权限、硬编码配置、不安全网络、日志泄露 |
| **可维护性** | X | 15% | 5 | README 质量、测试覆盖、版本管理、docstring 覆盖率、圈复杂度 |
| **性能** | F | 15% | 4 | Token 成本估算、循环内 API 调用、同步阻塞、流式输出 |
| **正确性** | C | 15% | 6 | 异常处理、类型注解、幻觉诱导词、输出验证、资源泄露、输入净化 |
| **兼容性** | M | 10% | 4 | 7 种厂商锁定 API、协议版本、平台锁定、编码兼容 |

权重和阈值均可在 `skillscope.yaml` 中自定义。

---

## AI Judge（LLM-as-a-Judge）

SkillScope 支持调用大语言模型进行语义级深度分析，弥补确定性规则的盲区：

| AI Judge | 维度 | 评估内容 |
|----------|------|---------|
| **PromptQualityJudge** | P | 语义清晰度、指令特异性、注入风险（上下文感知） |
| **HallucinationJudge** | C | 幻觉诱导表述、矛盾指令、事实性约束缺失 |

### 配置

```bash
# 设置 API Key（支持 DeepSeek 和 OpenAI）
export DEEPSEEK_API_KEY=sk-xxx
# 或
export OPENAI_API_KEY=sk-xxx

# 扫描时启用
skillscope scan ./my-skill --ai-enabled
```

### 特性

- **超时控制**：默认 30s，可自定义
- **自动重试**：失败后最多重试 2 次，指数退避
- **优雅降级**：API 不可用时自动回退到确定性分析，不影响扫描流程
- **Token 统计**：记录 input/output tokens 和延迟

---

## 自动修复

SkillScope 支持三级修复安全体系：

| 级别 | 说明 | 示例 |
|------|------|------|
| **Safe** 🛡️ | 确定性高，无副作用 | Secrets → 环境变量、生成 `.gitignore` |
| **Suggested** ⚠️ | 建议修复，需人工确认语义 | `eval()` → `ast.literal_eval()` |
| **Dangerous** ☠️ | 可能改变业务语义，必须人工审核 | 架构级重构、Prompt 内容改写 |

```bash
# 只预览可修复项（不修改文件）
skillscope scan ./my-skill --fix safe

# 应用 safe 级别修复到文件系统
skillscope scan ./my-skill --fix safe --apply-fixes

# 预览 suggested 级别（含 safe）
skillscope scan ./my-skill --fix suggested
```

---

## Web GUI

启动内置可视化界面：

```bash
skillscope gui
```

功能：
- 输入 Skill 路径，一键扫描
- Chart.js 雷达图展示六维评分
- 问题清单按严重级别分组（Critical / Warning / Info）
- 修复预览与一键应用
- 下载 HTML 报告

---

## 输出格式

| 格式 | 用途 | 命令 |
|------|------|------|
| **Console** | 本地开发查看 | `--format console` (默认) |
| **JSON** | 机器解析、二次处理 | `--format json` |
| **SARIF** | GitHub Code Scanning | `--format sarif` |
| **HTML** | 浏览器查看、分享 | `--format html` |

---

## CI/CD 集成

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

## 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│                      SkillScope CLI                           │
├──────────────────────────────────────────────────────────────┤
│  Core Engine (Hybrid: 确定性分析 + AI Judge)                  │
│  ├── Registry: 动态分析器发现与注册                             │
│  ├── Config: YAML / 预设 / 环境变量 三级配置                    │
│  ├── Loader: 并行文件扫描 + Token 估算 + AST 缓存               │
│  ├── Cache: 文件哈希增量缓存，重复扫描秒级完成                    │
│  └── FixManager: 三级安全修复过滤 + Patch 应用                  │
├──────────────────────────────────────────────────────────────┤
│  Analyzers (6 维度 × 4-7 子维度 = 30+ 子维度)                  │
│  ├── PromptAnalyzer: 注入 / Token / 清晰度 / 特异性            │
│  ├── SecurityScanner: Secrets / 危险函数 / 依赖 / MCP / 配置    │
│  │                  / 不安全网络 / 日志泄露                      │
│  ├── MaintainabilityAnalyzer: 文档 / 测试 / 版本 / 注释 / 复杂度 │
│  ├── PerformanceAnalyzer: 成本 / API 效率 / 延迟 / 流式输出      │
│  ├── CorrectnessAnalyzer: 异常 / 类型 / 幻觉 / 验证 / 资源 / 输入│
│  └── CompatibilityAnalyzer: 厂商锁定 / 协议 / 平台 / 编码       │
├──────────────────────────────────────────────────────────────┤
│  AI Judges (LLM-as-a-Judge)                                   │
│  ├── PromptQualityJudge: 语义清晰度 / 特异性 / 注入风险          │
│  └── HallucinationJudge: 幻觉诱导 / 矛盾指令 / 事实约束          │
├──────────────────────────────────────────────────────────────┤
│  Reporters: Console / JSON / SARIF 2.1.0 / HTML               │
├──────────────────────────────────────────────────────────────┤
│  Web GUI: Flask + Chart.js 雷达图 + 修复预览                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 检测规则一览

### Secrets 泄露 (12 种模式)
OpenAI API Key / Anthropic Key / Generic API Key / Password / AWS Access Key / GitHub Token / JWT Token / Private Key / Slack Token / Stripe Key / Google API Key / Slack Webhook

### 危险函数 (14 种)
eval / exec / os.system / subprocess.call / subprocess.run / subprocess.Popen / input / pickle.loads / pickle.load / yaml.load / marshal.loads / \_\_import\_\_ / compile / shelve.open

### Prompt 注入 (5 种)
f-string 拼接 / .format() 拼接 / % 格式化 / 字符串拼接 / SSTI 模板注入

### 厂商锁定 (7 种)
OpenAI functions / tool_choice / json_schema / Claude top_k / Azure Endpoint / AWS Bedrock / Vertex AI

### 其他规则
不安全网络通信 (3) / 敏感信息日志 (2) / 编码兼容 (2) / 资源泄露 / 输入净化 / 流式输出 / ...

---

## 配置与预设

### 预设列表

| 预设 | 适用场景 |
|------|---------|
| `general` | 通用 AI Skill 项目（默认） |

```bash
skillscope scan ./my-skill --preset general
```

### 环境变量覆盖

```bash
export SKILLSCOPE_PRESET=general
export SKILLSCOPE_CONFIG=./my-skillscope.yaml
export SKILLSCOPE_PARALLEL=true
export SKILLSCOPE_AI_ENABLED=true
export DEEPSEEK_API_KEY=sk-xxx
skillscope scan ./my-skill
```

---

## 项目结构

```
skillscope/
├── __init__.py              # 包入口，版本号
├── __main__.py              # python -m skillscope 入口
├── cli.py                   # CLI 命令（scan/config/gui）
├── core/
│   ├── engine.py            # 混合分析引擎
│   ├── models.py            # 数据模型（Pydantic v2）
│   ├── config.py            # 配置加载与合并
│   ├── loader.py            # Skill 文件扫描与 Token 估算
│   └── registry.py          # 分析器动态注册表
├── analyzers/
│   ├── base.py              # 分析器基类
│   ├── prompt.py            # Prompt 质量分析器
│   ├── security.py          # 安全扫描分析器
│   ├── maintainability.py   # 可维护性分析器
│   ├── performance.py       # 性能分析器
│   ├── correctness.py       # 正确性分析器
│   └── compatibility.py     # 兼容性分析器
├── ai_judges/
│   ├── base.py              # AI Judge 基类（超时/重试/降级）
│   ├── prompt_judge.py      # Prompt 质量 AI Judge
│   └── hallucination_judge.py # 幻觉风险 AI Judge
├── fixers/
│   ├── base.py              # 修复器基类
│   ├── manager.py           # 修复管理器
│   ├── security_fixer.py    # 安全修复器
│   └── prompt_fixer.py      # Prompt 修复器
├── reporters/
│   ├── console.py           # Console 报告（Lighthouse 风格）
│   ├── json_reporter.py     # JSON 报告
│   ├── sarif.py             # SARIF 2.1.0 报告
│   └── html_reporter.py     # HTML 报告（含 Chart.js）
├── gui/
│   └── app.py               # Flask Web GUI
└── utils/
    ├── patterns.py          # 45+ 检测规则模式库
    ├── parser.py            # 代码解析工具
    ├── tokens.py            # Token 估算（tiktoken + 降级）
    └── cache.py             # 文件哈希增量缓存
```

---

## 路线图

### v0.2.x（当前）
- [x] 六维评估体系（30+ 子维度）
- [x] 45+ 检测规则
- [x] 自动修复引擎（Safe / Suggested / Dangerous）
- [x] AI Judge（Prompt 质量 + 幻觉风险）
- [x] SARIF / JSON / Console / HTML 报告
- [x] Web GUI（Flask + Chart.js）
- [x] 配置系统 + 预设
- [x] 并行扫描 + 增量缓存
- [x] 插件注册表
- [x] CI/CD 集成

### v0.3.x（近期）
- [ ] tree-sitter AST 语义分析（数据流追踪）
- [ ] OSV API 实时漏洞查询
- [ ] Embedding-based Prompt 冗余检测
- [ ] VS Code 插件
- [ ] 更多行业预设

### v0.4.x（远期）
- [ ] 团队 Dashboard（趋势分析、技术债务看板）
- [ ] 行业合规预设库（金融、医疗、教育）
- [ ] 高级架构重构建议（商业版）

---

## 开源与商业

SkillScope 采用 **Open Core** 模式：

| 功能 | 开源版 (Apache-2.0) | 商业版 |
|------|---------------------|--------|
| 六维评估引擎 | ✅ | ✅ |
| 45+ 检测规则 | ✅ | ✅ |
| AI Judge (DeepSeek/OpenAI) | ✅ | ✅ |
| 自动修复 (Safe/Suggested) | ✅ | ✅ |
| SARIF / JSON / HTML 报告 | ✅ | ✅ |
| Web GUI | ✅ | ✅ |
| CI 集成 | ✅ | ✅ |
| 行业合规预设 | ❌ | ✅ |
| 团队 Dashboard | ❌ | ✅ |
| 私有部署 + 离线 LLM | ❌ | ✅ |
| 高级架构重构 | ❌ | ✅ |

---

## 贡献

我们欢迎所有形式的贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

- **报告问题**：[GitHub Issues](https://github.com/skillscope/skillscope/issues)
- **提交 PR**：确保通过 `pytest tests/` 和 `ruff check .`
- **贡献规则**：在 `skillscope/utils/patterns.py` 中添加新的检测模式
- **贡献预设**：在 `presets/open-source/` 中添加通用场景预设

开发环境搭建：

```bash
git clone https://github.com/skillscope/skillscope.git
cd skillscope
pip install -e ".[all]"
pytest tests/ -v -o addopts=""
ruff check .
```

---

## License

[Apache-2.0](LICENSE)

---

> **让每一个 AI Skill 都经得起质量检验。**
