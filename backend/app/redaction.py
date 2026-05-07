import re
from typing import Any

_SENSITIVE_KEYS = {
    "apikey", "api_key", "x-mbx-apikey", "signature", "secret",
    "secret_key", "secretkey", "authorization", "token", "password",
}

_QUERY_REDACT = re.compile(r"(signature|apiKey|api_key|secret)=([^&\s]+)", re.IGNORECASE)


def redact_string(s: str) -> str:
    """Redact known sensitive query params or header values inside a string."""
    return _QUERY_REDACT.sub(r"\1=REDACTED", s)


def redact_mapping(d: Any) -> Any:
    """Recursively redact sensitive keys inside dict/list structures.

    Returns a new structure; never mutates the input.
    """
    if isinstance(d, dict):
        return {
            k: ("REDACTED" if k.lower() in _SENSITIVE_KEYS else redact_mapping(v))
            for k, v in d.items()
        }
    if isinstance(d, list):
        return [redact_mapping(x) for x in d]
    if isinstance(d, str):
        return redact_string(d)
    return d
