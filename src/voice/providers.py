"""Small HTTP clients for explicitly selected commentary providers."""

from dataclasses import dataclass
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

PROVIDERS = {
    "Engine notes (offline)": ("template", ""),
    "LM Studio": ("lmstudio", "http://localhost:1234/v1"),
    "Ollama": ("ollama", "http://localhost:11434"),
    "Remote / OpenAI-compatible": ("remote", "https://api.openai.com/v1"),
}


class ProviderError(RuntimeError):
    """A user-facing provider error, without response bodies or credentials."""


@dataclass(frozen=True)
class ModelConfig:
    backend: str = "template"
    base_url: str = ""
    model: str = ""
    api_key: str = ""
    timeout: float = 45.0

    def endpoint(self, path: str) -> str:
        parts = urlsplit(self.base_url.strip())
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ProviderError("Enter an http:// or https:// server URL.")
        if parts.username or parts.password or parts.query or parts.fragment:
            raise ProviderError("Use a plain server URL; put credentials in the API key field.")
        return self.base_url.strip().rstrip("/") + path


def _request(config: ModelConfig, path: str, payload=None, timeout=None):
    headers = {"Content-Type": "application/json", "User-Agent": "pesc-i"}
    if config.api_key:
        headers["Authorization"] = "Bearer " + config.api_key
    request = Request(
        config.endpoint(path),
        data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers,
    )
    try:
        with urlopen(request, timeout=timeout or config.timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        exc.close()
        hints = {
            401: "Authentication failed. Check the API key.",
            403: "Access denied. Check model permissions.",
            404: "Endpoint or model not found. Check the base URL and model ID.",
            429: "Rate limit or quota reached. Try again later.",
        }
        raise ProviderError(hints.get(exc.code, f"Server returned HTTP {exc.code}.")) from None
    except (URLError, TimeoutError, OSError):
        raise ProviderError("Server unreachable or timed out. Check the URL and server.") from None
    except (ValueError, TypeError):
        raise ProviderError("Server returned invalid JSON.") from None


def discover_models(config: ModelConfig) -> list[str]:
    if config.backend == "template":
        return []
    data = _request(config, "/api/tags" if config.backend == "ollama" else "/models", timeout=5)
    try:
        items = data["models"] if config.backend == "ollama" else data["data"]
        names = [m["name"] if config.backend == "ollama" else m["id"] for m in items]
        # Embedding models cannot generate commentary.
        return sorted({n for n in names if isinstance(n, str) and "embed" not in n.lower()})
    except (KeyError, TypeError):
        raise ProviderError("The model list has an unexpected format.") from None


def complete(config: ModelConfig, messages: list[dict], max_tokens: int) -> str:
    if not config.model.strip():
        raise ProviderError("Choose a discovered model or enter its exact model ID.")
    payload = {"model": config.model, "messages": messages, "stream": False}
    if config.backend == "ollama":
        payload["think"] = False
        payload["options"] = {"temperature": 0.2, "num_predict": max_tokens}
        data = _request(config, "/api/chat", payload)
    else:
        payload.update(max_tokens=max_tokens, temperature=0.2)
        data = _request(config, "/chat/completions", payload)
    try:
        message = data["message"] if config.backend == "ollama" else data["choices"][0]["message"]
        content = message["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError
        # Some local models put their reasoning in the text content.
        import re

        content = re.sub(r"<think>.*?</think>", "", content, flags=re.S).strip()
        if not content or "<think>" in content:
            raise ValueError
        return content[:2400]
    except (KeyError, IndexError, TypeError, ValueError):
        raise ProviderError("The model returned no usable commentary. Try another model.") from None
