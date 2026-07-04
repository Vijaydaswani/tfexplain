from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from .errors import AnalysisError


SYSTEM_PROMPT = """You explain Terraform analysis for infrastructure reviewers.
Use concise, practical language.
Focus on risk, reviewer attention, security, reliability, cost, and next steps.
Do not invent resource values that are not present in the analysis.
If the input is a deterministic summary, treat it as the source of truth.
"""

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "claude": "claude-3-5-haiku-latest",
    "azure-openai": None,
    "ollama": "llama3.1",
}


@dataclass(frozen=True)
class AIResult:
    provider: str
    model: str
    explanation: str


def explain_with_ai(
    content: str,
    task: str,
    provider: str,
    model: str | None = None,
) -> AIResult:
    resolved_model = resolve_model(provider, model)
    prompt = build_prompt(redact_sensitive_text(content), task)

    if provider == "openai":
        explanation = call_openai(prompt, resolved_model)
    elif provider == "claude":
        explanation = call_claude(prompt, resolved_model)
    elif provider == "azure-openai":
        explanation = call_azure_openai(prompt, resolved_model)
    elif provider == "ollama":
        explanation = call_ollama(prompt, resolved_model)
    else:
        raise AnalysisError(f"Unsupported AI provider: {provider}")

    return AIResult(provider=provider, model=resolved_model, explanation=explanation.strip())


def build_prompt(content: str, task: str) -> str:
    return "\n".join(
        [
            f"Task: {task}",
            "",
            "Terraform analysis:",
            content,
            "",
            "Return:",
            "- summary",
            "- key risks",
            "- reviewer focus",
            "- recommended next steps",
        ]
    )


SECRET_KEYWORDS = (
    "access_key",
    "api_key",
    "authorization",
    "client_secret",
    "password",
    "private_key",
    "private_key_pem",
    "secret",
    "token",
)


def redact_sensitive_text(content: str) -> str:
    redacted = content
    for keyword in SECRET_KEYWORDS:
        redacted = re.sub(
            rf"(?i)({re.escape(keyword)}\s*[:=]\s*)([^\n,}}]+)",
            rf"\1[REDACTED]",
            redacted,
        )
    redacted = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]", redacted)
    redacted = re.sub(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
        "[REDACTED PRIVATE KEY]",
        redacted,
        flags=re.DOTALL,
    )
    return redacted


def resolve_model(provider: str, model: str | None) -> str:
    if model:
        return model
    if provider == "openai":
        return os.environ.get("OPENAI_MODEL") or DEFAULT_MODELS["openai"]
    if provider == "claude":
        return os.environ.get("ANTHROPIC_MODEL") or DEFAULT_MODELS["claude"]
    if provider == "azure-openai":
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        if not deployment:
            raise AnalysisError("Azure OpenAI requires --model or AZURE_OPENAI_DEPLOYMENT.")
        return deployment
    if provider == "ollama":
        return os.environ.get("OLLAMA_MODEL") or DEFAULT_MODELS["ollama"]
    raise AnalysisError(f"Unsupported AI provider: {provider}")


def call_openai(prompt: str, model: str) -> str:
    api_key = require_env("OPENAI_API_KEY", "OpenAI")
    url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    data = post_json(
        url,
        payload,
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    return extract_chat_completion(data, "OpenAI")


def call_claude(prompt: str, model: str) -> str:
    api_key = require_env("ANTHROPIC_API_KEY", "Claude")
    payload = {
        "model": model,
        "max_tokens": int(os.environ.get("TFEXPLAIN_AI_MAX_TOKENS", "1200")),
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    data = post_json(
        os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1/messages"),
        payload,
        {
            "x-api-key": api_key,
            "anthropic-version": os.environ.get("ANTHROPIC_VERSION", "2023-06-01"),
            "Content-Type": "application/json",
        },
    )
    content = data.get("content")
    if isinstance(content, list):
        text_parts = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
        if text_parts:
            return "\n".join(text_parts)
    raise AnalysisError("Claude response did not contain text content.")


def call_azure_openai(prompt: str, deployment: str) -> str:
    api_key = require_env("AZURE_OPENAI_API_KEY", "Azure OpenAI")
    endpoint = require_env("AZURE_OPENAI_ENDPOINT", "Azure OpenAI").rstrip("/")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    data = post_json(
        url,
        payload,
        {
            "api-key": api_key,
            "Content-Type": "application/json",
        },
    )
    return extract_chat_completion(data, "Azure OpenAI")


def call_ollama(prompt: str, model: str) -> str:
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }
    data = post_json(
        f"{base_url}/api/chat",
        payload,
        {"Content-Type": "application/json"},
    )
    message = data.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return message["content"]
    if isinstance(data.get("response"), str):
        return data["response"]
    raise AnalysisError("Ollama response did not contain message content.")


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=int(os.environ.get("TFEXPLAIN_AI_TIMEOUT", "60"))) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AnalysisError(f"AI provider request failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise AnalysisError(f"AI provider request failed: {exc.reason}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AnalysisError("AI provider returned invalid JSON.") from exc
    if not isinstance(data, dict):
        raise AnalysisError("AI provider returned an unexpected JSON response.")
    return data


def extract_chat_completion(data: dict[str, Any], provider_name: str) -> str:
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]
            if isinstance(first.get("text"), str):
                return first["text"]
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    raise AnalysisError(f"{provider_name} response did not contain generated text.")


def require_env(name: str, provider_name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise AnalysisError(f"{provider_name} requires {name}.")
    return value


def append_ai_to_output(content: str, result: AIResult, output_format: str) -> str:
    if output_format == "json":
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise AnalysisError("Cannot attach AI output to invalid JSON content.") from exc
        if not isinstance(payload, dict):
            payload = {"result": payload}
        payload["ai"] = {
            "provider": result.provider,
            "model": result.model,
            "explanation": result.explanation,
        }
        return json.dumps(payload, indent=2, sort_keys=True)

    if output_format == "markdown":
        return "\n\n".join(
            [
                content,
                "## AI-Assisted Explanation",
                f"_Provider: `{result.provider}`, model: `{result.model}`_",
                "",
                result.explanation,
            ]
        )

    return "\n\n".join(
        [
            content,
            "AI-Assisted Explanation",
            f"Provider: {result.provider}",
            f"Model: {result.model}",
            "",
            result.explanation,
        ]
    )
