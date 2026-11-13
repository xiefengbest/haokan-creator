"""报错和日志里去掉密钥、口令和地址。"""

from __future__ import annotations

import re

SECRET_FIELDS = {
    "token",
    "pass",
    "password",
    "accesskeysecret",
    "accesskeyid",
    "securitytoken",
    "sign",
    "signkey",
    "secret",
}

_URL = re.compile(r"https?://\S+")
_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|secret|token|access[_-]?key[_-]?(?:id|secret)?|sign[_-]?key|security[_-]?token)\b"
    r"\s*[:=]\s*\S+"
)


def scrub_text(text: str) -> str:
    text = _URL.sub("（地址已隐藏）", text)
    return _ASSIGNMENT.sub(lambda match: f"{match.group(1)}=***", text)


def redact(value):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if str(key).lower().replace("_", "") in SECRET_FIELDS:
                cleaned[key] = "***"
            else:
                cleaned[key] = redact(item)
        return cleaned
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return scrub_text(value)
    return value
