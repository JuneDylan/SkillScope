"""
AI Judge 基类
支持：DeepSeek/OpenAI 兼容 API、结构化输出、优雅降级、超时/重试
"""
from __future__ import annotations

import json
import os
import time
from abc import ABC, abstractmethod

from pydantic import BaseModel


class AIJudgeMeta(BaseModel):
    model: str = ""
    model_version: str = ""
    temperature: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    status: str = "success"
    retries: int = 0


class BaseAIJudge(ABC):
    dimension: str = ""
    name: str = ""
    model: str = "deepseek-chat"
    temperature: float = 0.0
    timeout: int = 30
    max_retries: int = 2
    retry_delay: float = 1.0

    def __init__(self, model: str | None = None, timeout: int | None = None, max_retries: int | None = None):
        if model:
            self.model = model
        if timeout is not None:
            self.timeout = timeout
        if max_retries is not None:
            self.max_retries = max_retries

    def _get_client(self):
        try:
            from openai import OpenAI
            api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
            base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            if not api_key:
                return None
            return OpenAI(api_key=api_key, base_url=base_url, timeout=self.timeout)
        except ImportError:
            return None

    def evaluate(self, context: dict) -> tuple[dict, AIJudgeMeta]:
        client = self._get_client()
        if not client:
            return {}, AIJudgeMeta(
                model=self.model, status="unavailable",
            )

        system_prompt = self.build_system_prompt()
        user_prompt = self.build_user_prompt(context)

        last_error = None
        for attempt in range(self.max_retries + 1):
            start = time.perf_counter()
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    timeout=self.timeout,
                )
                latency = int((time.perf_counter() - start) * 1000)
                raw = response.choices[0].message.content or ""
                parsed = self.parse_response(raw)
                meta = AIJudgeMeta(
                    model=self.model,
                    temperature=self.temperature,
                    input_tokens=getattr(response.usage, "prompt_tokens", 0) if response.usage else 0,
                    output_tokens=getattr(response.usage, "completion_tokens", 0) if response.usage else 0,
                    latency_ms=latency,
                    status="success",
                    retries=attempt,
                )
                return parsed, meta
            except Exception as e:
                latency = int((time.perf_counter() - start) * 1000)
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (attempt + 1))

        return {}, AIJudgeMeta(
            model=self.model, status=f"error: {last_error}", latency_ms=0,
            retries=self.max_retries,
        )

    @abstractmethod
    def build_system_prompt(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def build_user_prompt(self, context: dict) -> str:
        raise NotImplementedError

    @abstractmethod
    def parse_response(self, response: str) -> dict:
        raise NotImplementedError

    def _extract_json(self, text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except json.JSONDecodeError:
                pass
        return {}
