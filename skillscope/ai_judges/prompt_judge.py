"""
Prompt 质量 AI Judge
使用 LLM 对 Prompt 的语义清晰度、特异性、注入风险进行深度评估
"""
from __future__ import annotations
from skillscope.ai_judges.base import BaseAIJudge


class PromptQualityJudge(BaseAIJudge):
    dimension = "P"
    name = "Prompt质量(AI)"

    def __init__(self, model=None, timeout=None, max_retries=None, retry_delay=None):
        super().__init__(model=model, timeout=timeout, max_retries=max_retries)
        if retry_delay is not None:
            self.retry_delay = retry_delay

    SYSTEM_PROMPT = """你是一个 AI Prompt 质量评估专家。请从以下维度评估给定 Prompt 的质量，返回 JSON 格式：

{
  "clarity": {"score": 0-100, "reason": "..."},
  "specificity": {"score": 0-100, "reason": "..."},
  "injection_risk": {"score": 0-100, "reason": "...", "vulnerable_lines": ["..."]},
  "overall_comment": "..."
}

评估标准：
- clarity (清晰度): 指令是否清晰无歧义，角色定义是否明确，输出格式是否指定
- specificity (特异性): 是否针对特定领域/任务，还是过于通用
- injection_risk (注入风险): 是否存在用户输入直接拼接到 Prompt 的风险，是否缺少输入验证

评分规则：
- 90-100: 优秀，几乎无改进空间
- 70-89: 良好，有少量可优化项
- 50-69: 一般，存在明显问题
- 0-49: 差，存在严重问题

只返回 JSON，不要返回其他内容。"""

    def build_system_prompt(self) -> str:
        return self.SYSTEM_PROMPT

    def build_user_prompt(self, context: dict) -> str:
        prompt_content = context.get("prompt_content", "")
        code_content = context.get("code_content", "")
        parts = []
        if prompt_content:
            parts.append(f"## Prompt 内容\n```\n{prompt_content[:6000]}\n```")
        if code_content:
            parts.append(f"## 相关代码\n```\n{code_content[:4000]}\n```")
        if not parts:
            parts.append("未找到可分析的 Prompt 内容。")
        return "\n\n".join(parts)

    def parse_response(self, response: str) -> dict:
        return self._extract_json(response)
