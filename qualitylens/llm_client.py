"""Minimal OpenAI-compatible chat client (works with Ollama, vLLM, LM Studio or hosted APIs).

Configure with QL_LLM_BASE_URL (e.g. http://localhost:11434/v1), QL_LLM_MODEL (e.g. granite3.3:8b)
and optionally QL_LLM_API_KEY. The transport is injectable so tests run without a network.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Callable

Transport = Callable[[str, dict, dict, float], dict]


def _http_transport(url: str, headers: dict, body: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - URL comes from user config
        return json.loads(resp.read().decode())


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, base_url: str | None = None, model: str | None = None, api_key: str | None = None,
                 transport: Transport | None = None, retries: int = 2, timeout: float = 120.0):
        self.base_url = (base_url or os.environ.get("QL_LLM_BASE_URL", "")).rstrip("/")
        self.model = model or os.environ.get("QL_LLM_MODEL", "")
        self.api_key = api_key or os.environ.get("QL_LLM_API_KEY", "")
        self.transport = transport or _http_transport
        self.retries = retries
        self.timeout = timeout
        if not self.base_url or not self.model:
            raise LLMError("Set QL_LLM_BASE_URL and QL_LLM_MODEL to use the LLM backend.")

    def chat(self, system: str, user: str, temperature: float = 0.1) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {"model": self.model, "temperature": temperature,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                data = self.transport(f"{self.base_url}/chat/completions", headers, body, self.timeout)
                return data["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as exc:
                last = exc
                if exc.code not in (429, 500, 502, 503, 504):
                    break
            except (urllib.error.URLError, TimeoutError, KeyError, IndexError, json.JSONDecodeError) as exc:
                last = exc
            time.sleep(min(2 ** attempt, 8) * 0.5)
        raise LLMError(f"LLM request failed: {last}")


def extract_code(text: str) -> str:
    blocks = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, flags=re.S)
    return (max(blocks, key=len) if blocks else text).strip() + "\n"


def extract_json(text: str):
    m = re.search(r"```(?:json)?\s*\n(.*?)```", text, flags=re.S)
    raw = m.group(1) if m else text
    start = min([i for i in (raw.find("["), raw.find("{")) if i >= 0], default=-1)
    if start < 0:
        raise ValueError("no JSON found")
    return json.loads(raw[start:])
