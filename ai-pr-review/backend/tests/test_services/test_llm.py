"""
Unit tests for LLM client.
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.llm import LLMClient, LLMResponse
from app.core.exceptions import LLMAPIError


class TestLLMClient:
    @pytest.mark.asyncio
    async def test_chat_completion_success(self):
        client = LLMClient()
        mock_response_data = {
            "choices": [{"message": {"content": '{"overall_score":85}'}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }
        with patch.object(client._client, "post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json = AsyncMock(return_value=mock_response_data)
            response = await client.chat_completion("system", "user")
            assert isinstance(response, LLMResponse)
            assert response.total_tokens == 150
            assert '"overall_score":85' in response.content

    @pytest.mark.asyncio
    async def test_chat_completion_unauthorized(self):
        client = LLMClient()
        with patch.object(client._client, "post") as mock_post:
            mock_post.return_value.status_code = 401
            with pytest.raises(LLMAPIError, match="authentication"):
                await client.chat_completion("system", "user")

    @pytest.mark.asyncio
    async def test_chat_completion_retry_success(self):
        """Should retry on 503 and succeed on 3rd attempt."""
        client = LLMClient()
        mock_response_data = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                resp = AsyncMock()
                resp.status_code = 503
                return resp
            resp = AsyncMock()
            resp.status_code = 200
            resp.json = AsyncMock(return_value=mock_response_data)
            return resp

        with patch.object(client._client, "post", mock_post):
            response = await client.chat_completion("system", "user")
            assert response.total_tokens == 15
            assert call_count == 3

    @pytest.mark.asyncio
    async def test_chat_completion_all_retries_fail(self):
        client = LLMClient()
        with patch.object(client._client, "post") as mock_post:
            mock_post.return_value.status_code = 503
            with pytest.raises(LLMAPIError, match="after 3 retries"):
                await client.chat_completion("system", "user")
