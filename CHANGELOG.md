# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-05-19

### Added
- Six-dimension evaluation system (Prompt Quality, Security, Maintainability, Performance, Correctness, Compatibility)
- 24 sub-dimension scoring points across 6 dimensions
- Three-level safety fix system (Safe / Suggested / Dangerous)
- YAML configuration + preset system + environment variable override
- Parallel analysis with ThreadPoolExecutor
- SARIF 2.1.0 output (GitHub Code Scanning compatible)
- File hash-based incremental cache
- Plugin registry with dynamic analyzer discovery
- AI Judge framework (DeepSeek/OpenAI compatible)
- PromptQualityJudge: clarity, specificity, injection risk
- HallucinationJudge: hallucination risk, risk patterns
- Web GUI (Flask): scan, fix, HTML report download
- HTML report with Chart.js radar chart
- Console report (Lighthouse style)
- JSON report output
- CLI with scan, config, gui subcommands
- CI gate threshold support
- `.gitignore` auto-generation fix
- Secret replacement fix (hardcoded → os.environ.get)
- Dangerous function replacement fix (eval → ast.literal_eval)

### Fixed
- Config pollution: deep copy DEFAULT_CONFIG to prevent global mutation
- Directory cache: compute recursive hash for directory paths
- HTML report double-write: separate HTML and other format output logic
- Browser launch timing: delayed 1.5s thread for GUI
- Missing `__main__.py`: add entry point for `python -m skillscope`
- XSS vulnerability: HTML-escape all dynamic content in reports and GUI
- JSON serialization: handle non-serializable types with `default=str`
- `switchTab` implicit event: pass button element explicitly
- `tiktoken` offline failure: graceful fallback to character estimation
- Windows GBK encoding: safe print with Unicode error handling

## [0.1.0] - 2026-05-15

### Added
- Initial project structure
- Basic Prompt analyzer
- Basic Security scanner
- Console reporter
- CLI entry point
