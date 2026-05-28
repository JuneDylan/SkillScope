"""
正确性 AI Judge - 幻觉风险评估
使用 LLM 检测 Prompt 中可能诱导模型产生幻觉的表述
"""
from __future__ import annotations

from skillscope.ai_judges.base import BaseAIJudge


class HallucinationJudge(BaseAIJudge):
    dimension = "C"
    name = "幻觉风险(AI)"

    def __init__(self, model=None, timeout=None, max_retries=None, retry_delay=None):
        super().__init__(model=model, timeout=timeout, max_retries=max_retries)
        if retry_delay is not None:
            self.retry_delay = retry_delay

    SYSTEM_PROMPT = """你是一个 AI 幻觉风险评估专家。请分析给定的 Prompt 和代码，评估其诱导 LLM 产生幻觉的风险，返回 JSON 格式：

{
  "hallucination_risk": {"score": 0-100, "reason": "..."},
  "risk_patterns": ["..."],
  "suggestions": ["..."]
}

评估标准：
- 是否要求模型"编造"或"猜测"不确定信息
- 是否缺少事实性约束（如"仅基于提供的上下文回答"）
- 是否存在自相矛盾的指令
- 输出格式是否足够结构化以减少自由发挥
- 是否缺少"不确定时声明不知道"的指令

评分规则：
- 90-100: 低风险，有充分的防幻觉机制
- 70-89: 中低风险，有少量可改进项
- 50-69: 中高风险，缺少关键防护
- 0-49: 高风险，极易产生幻觉

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
            parts.append("未找到可分析的内容。")
        return "\n\n".join(parts)

    def parse_response(self, response: str) -> dict:
        return self._extract_json(response)
