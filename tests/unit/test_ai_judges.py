"""
AI Judge 单元测试
测试基类和 Judge 逻辑，不依赖真实 API 调用
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from skillscope.ai_judges.base import AIJudgeMeta
from skillscope.ai_judges.hallucination_judge import HallucinationJudge
from skillscope.ai_judges.prompt_judge import PromptQualityJudge


class TestBaseAIJudge:
    def test_no_api_key_returns_empty(self):
        judge = PromptQualityJudge()
        with patch.dict("os.environ", {}, clear=True):
            result, meta = judge.evaluate({"prompt_content": "test"})
            assert result == {}
            assert meta.status == "unavailable"

    def test_meta_defaults(self):
        meta = AIJudgeMeta()
        assert meta.model == ""
        assert meta.status == "success"
        assert meta.input_tokens == 0

    def test_extract_json_from_text(self):
        judge = PromptQualityJudge()
        text = 'Here is the result: {"clarity": {"score": 80}} end'
        result = judge._extract_json(text)
        assert result["clarity"]["score"] == 80

    def test_extract_json_no_json(self):
        judge = PromptQualityJudge()
        result = judge._extract_json("no json here")
        assert result == {}


class TestPromptQualityJudge:
    def test_dimension_and_name(self):
        judge = PromptQualityJudge()
        assert judge.dimension == "P"
        assert "Prompt" in judge.name

    def test_build_system_prompt(self):
        judge = PromptQualityJudge()
        prompt = judge.build_system_prompt()
        assert "clarity" in prompt
        assert "specificity" in prompt

    def test_build_user_prompt_with_content(self):
        judge = PromptQualityJudge()
        context = {"prompt_content": "你是一个助手", "code_content": "def foo(): pass"}
        prompt = judge.build_user_prompt(context)
        assert "助手" in prompt
        assert "foo" in prompt

    def test_build_user_prompt_empty(self):
        judge = PromptQualityJudge()
        context = {}
        prompt = judge.build_user_prompt(context)
        assert isinstance(prompt, str)

    def test_parse_response_valid(self):
        judge = PromptQualityJudge()
        raw = '{"clarity": {"score": 85, "reason": "清晰"}, "specificity": {"score": 70, "reason": "一般"}, "injection_risk": {"score": 95, "reason": "安全"}, "overall_comment": "良好"}'
        result = judge.parse_response(raw)
        assert result["clarity"]["score"] == 85

    def test_parse_response_with_wrapper(self):
        judge = PromptQualityJudge()
        raw = '```json\n{"clarity": {"score": 90, "reason": "ok"}, "specificity": {"score": 80, "reason": "ok"}, "injection_risk": {"score": 100, "reason": "ok"}, "overall_comment": "ok"}\n```'
        result = judge.parse_response(raw)
        assert result["clarity"]["score"] == 90


class TestHallucinationJudge:
    def test_dimension_and_name(self):
        judge = HallucinationJudge()
        assert judge.dimension == "C"
        assert "幻觉" in judge.name

    def test_build_system_prompt(self):
        judge = HallucinationJudge()
        prompt = judge.build_system_prompt()
        assert "幻觉" in prompt or "hallucination" in prompt.lower()

    def test_build_user_prompt(self):
        judge = HallucinationJudge()
        context = {"prompt_content": "你是一个万能助手", "code_content": "def foo(): pass"}
        prompt = judge.build_user_prompt(context)
        assert isinstance(prompt, str)

    def test_parse_response(self):
        judge = HallucinationJudge()
        raw = '{"hallucination_risk": {"score": 30, "reason": "低风险"}, "risk_patterns": ["万能"], "overall_comment": "注意"}'
        result = judge.parse_response(raw)
        assert result["hallucination_risk"]["score"] == 30


class TestAIJudgeWithMockedAPI:
    def test_evaluate_with_mocked_client(self):
        judge = PromptQualityJudge()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"clarity": {"score": 85, "reason": "清晰"}, "specificity": {"score": 80, "reason": "具体"}, "injection_risk": {"score": 95, "reason": "安全"}, "overall_comment": "良好"}'
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch.object(judge, "_get_client", return_value=mock_client):
            result, meta = judge.evaluate({"prompt_content": "你是一个助手"})

        assert result["clarity"]["score"] == 85
        assert meta.status == "success"
        assert meta.input_tokens == 100
        assert meta.output_tokens == 50

    def test_evaluate_api_error(self):
        judge = PromptQualityJudge(max_retries=0)

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        with patch.object(judge, "_get_client", return_value=mock_client):
            result, meta = judge.evaluate({"prompt_content": "test"})

        assert result == {}
        assert "error" in meta.status

    def test_evaluate_retry_success(self):
        judge = PromptQualityJudge(max_retries=2, retry_delay=0.01)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"clarity": {"score": 90, "reason": "ok"}, "specificity": {"score": 85, "reason": "ok"}, "injection_risk": {"score": 95, "reason": "ok"}, "overall_comment": "ok"}'
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 50
        mock_response.usage.completion_tokens = 30

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            Exception("timeout"),
            mock_response,
        ]

        with patch.object(judge, "_get_client", return_value=mock_client):
            result, meta = judge.evaluate({"prompt_content": "test"})

        assert result["clarity"]["score"] == 90
        assert meta.status == "success"
        assert meta.retries == 1

    def test_evaluate_all_retries_fail(self):
        judge = PromptQualityJudge(max_retries=1, retry_delay=0.01)

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("persistent error")

        with patch.object(judge, "_get_client", return_value=mock_client):
            result, meta = judge.evaluate({"prompt_content": "test"})

        assert result == {}
        assert "error" in meta.status
        assert meta.retries == 1

    def test_custom_timeout(self):
        judge = PromptQualityJudge(timeout=60)
        assert judge.timeout == 60

    def test_custom_max_retries(self):
        judge = PromptQualityJudge(max_retries=5)
        assert judge.max_retries == 5

    def test_meta_retries_field(self):
        meta = AIJudgeMeta(retries=3)
        assert meta.retries == 3
