from __future__ import annotations

import json
import os
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tfexplain.ai import append_ai_to_output, explain_with_ai, redact_sensitive_text


class AITest(unittest.TestCase):
    def test_openai_request_uses_env_key_and_model(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch("tfexplain.ai.urllib.request.urlopen", return_value=FakeResponse(openai_response())) as urlopen:
                result = explain_with_ai("Plan: create 1", "Explain plan", "openai", "test-model")

        self.assertEqual(result.provider, "openai")
        self.assertEqual(result.model, "test-model")
        self.assertEqual(result.explanation, "mock OpenAI explanation")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.openai.com/v1/chat/completions")
        self.assertEqual(request.headers["Authorization"], "Bearer test-key")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "test-model")

    def test_ollama_request_uses_local_endpoint_without_api_key(self) -> None:
        with patch.dict(os.environ, {"OLLAMA_BASE_URL": "http://localhost:11434"}, clear=True):
            with patch("tfexplain.ai.urllib.request.urlopen", return_value=FakeResponse(ollama_response())) as urlopen:
                result = explain_with_ai("Code: terraform_data", "Explain code", "ollama", "llama-test")

        self.assertEqual(result.provider, "ollama")
        self.assertEqual(result.model, "llama-test")
        self.assertEqual(result.explanation, "mock Ollama explanation")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://localhost:11434/api/chat")
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "llama-test")
        self.assertFalse(payload["stream"])

    def test_append_ai_to_json_output(self) -> None:
        content = '{"counts": {"create": 1}}'
        result = type("Result", (), {"provider": "openai", "model": "m", "explanation": "text"})()

        rendered = append_ai_to_output(content, result, "json")

        payload = json.loads(rendered)
        self.assertEqual(payload["counts"]["create"], 1)
        self.assertEqual(payload["ai"]["provider"], "openai")
        self.assertEqual(payload["ai"]["explanation"], "text")

    def test_redacts_sensitive_content_before_ai_request(self) -> None:
        content = 'password = "super-secret"\napi_key: abc123\nAuthorization: Bearer tok_123'

        redacted = redact_sensitive_text(content)

        self.assertNotIn("super-secret", redacted)
        self.assertNotIn("abc123", redacted)
        self.assertNotIn("tok_123", redacted)
        self.assertIn("[REDACTED]", redacted)

    def test_ai_request_uses_redacted_prompt(self) -> None:
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch("tfexplain.ai.urllib.request.urlopen", return_value=FakeResponse(openai_response())) as urlopen:
                explain_with_ai('token = "secret-token"', "Explain plan", "openai", "test-model")

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        user_content = payload["messages"][1]["content"]
        self.assertNotIn("secret-token", user_content)
        self.assertIn("[REDACTED]", user_content)


def openai_response() -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": "mock OpenAI explanation",
                }
            }
        ]
    }


def ollama_response() -> dict[str, object]:
    return {
        "message": {
            "content": "mock Ollama explanation",
        }
    }


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")
