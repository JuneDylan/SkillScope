# Contributing to SkillScope

Thank you for your interest in contributing to SkillScope! We welcome all forms of contributions.

## Getting Started

### Prerequisites

- Python 3.9+
- Git

### Development Setup

```bash
git clone https://github.com/skillscope/skillscope.git
cd skillscope
pip install -e ".[all]"
```

### Running Tests

```bash
pytest tests/ -v -o addopts=""
```

### Linting

```bash
ruff check .
```

## How to Contribute

### Report Issues

- Use [GitHub Issues](https://github.com/skillscope/skillscope/issues)
- Include: Python version, OS, steps to reproduce, expected vs actual behavior

### Submit Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Ensure all tests pass: `pytest tests/ -v -o addopts=""`
5. Ensure linting passes: `ruff check .`
6. Commit with a clear message
7. Open a Pull Request

### Add New Analyzer Rules

1. Add rule patterns to `skillscope/utils/patterns.py`
2. Implement detection logic in the corresponding analyzer under `skillscope/analyzers/`
3. Add fix logic in `skillscope/fixers/` if auto-fixable
4. Add unit tests in `tests/unit/`
5. Update the preset YAML in `presets/open-source/`

### Add New Presets

1. Create a YAML file in `presets/open-source/`
2. Follow the schema in `presets/open-source/general.yaml`
3. Add documentation in the README

## Code Style

- Follow PEP 8
- Use type hints for all function signatures
- Use `from __future__ import annotations` in all files
- Line length: 120 characters max
- No unnecessary comments in code

## Commit Messages

- Use clear, descriptive commit messages
- Prefix with type: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`

## License

By contributing, you agree that your contributions will be licensed under the Apache-2.0 License.
