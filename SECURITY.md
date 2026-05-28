# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in SkillScope, please report it responsibly.

**Please do NOT open a public GitHub Issue for security vulnerabilities.**

Instead, send an email to: **security@skillscope.dev**

Include the following details:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We aim to respond within 48 hours and will keep you updated on our progress.

## Security-related Features

SkillScope includes built-in security scanning capabilities:
- **Secrets detection**: API keys, tokens, passwords
- **Dangerous function detection**: `eval`, `exec`, `pickle.loads`, etc.
- **Insecure network pattern detection**: Unverified SSL, HTTP for sensitive data
- **Dependency vulnerability checks**: Known risky packages

These features are designed to help developers identify security issues in their AI Skills, but they do not replace professional security audits.
