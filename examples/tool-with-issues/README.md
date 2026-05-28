# Data Processor Skill

A tool-type Skill with both code and prompt, demonstrating common issues that SkillScope can detect.

## Usage

```bash
skillscope scan ./tool-with-issues
```

## Expected Results

This Skill intentionally contains several issues that SkillScope should detect:
- Hardcoded API key (Security - Critical)
- Use of `eval()` (Security - Warning)
- Hardcoded temperature config (Security - Info)
- No error handling (Correctness - Warning)
- No type annotations (Correctness - Info)
