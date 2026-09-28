#!/usr/bin/env python3
"""Bounded, secret-redacted Prism teacher HTTP error evidence.

Keep a body digest and short message for diagnosis. Only the model's exact
PEG-native envelope failure is a known invalid-output category; all other
HTTP errors remain unknown tool failures until inspected.
"""
from __future__ import annotations

import hashlib
from io import BytesIO
import json
import re
from urllib.error import HTTPError

PEG_MESSAGE = "The model produced output that does not match the expected peg-native format"


def capture_http_error(exc: HTTPError, key: str) -> dict:
    body = exc.read(16_384)
    raw = body.decode("utf-8", errors="replace")
    raw = raw.replace(key, "<redacted-api-key>")
    raw = re.sub(r"(?i)bearer\s+[a-z0-9._-]+", "Bearer <redacted>", raw)
    try:
        value = json.loads(raw)
        candidate = value.get("error", value) if isinstance(value, dict) else value
        message = candidate.get("message", "") if isinstance(candidate, dict) else ""
        category = candidate.get("type", "") if isinstance(candidate, dict) else ""
    except json.JSONDecodeError:
        message, category = raw, "UNPARSEABLE_BODY"
    message = str(message)[:2500]
    known_peg = exc.code == 500 and PEG_MESSAGE in message
    return {"http_status": exc.code, "body_sha256": hashlib.sha256(body).hexdigest().upper(),
            "body_bytes_read": len(body), "error_type": str(category)[:120],
            "message": message, "body_excerpt": raw[:4000],
            "classification": "PEG_NATIVE_MISMATCH" if known_peg else "UNKNOWN_BACKEND_ERROR"}


def self_test() -> None:
    body = json.dumps({"error": {"type": "server_error", "message": PEG_MESSAGE}}).encode()
    error = HTTPError("http://127.0.0.1", 500, "error", {}, BytesIO(body))
    parsed = capture_http_error(error, "SECRET")
    assert parsed["classification"] == "PEG_NATIVE_MISMATCH"
    other = HTTPError("http://127.0.0.1", 500, "error", {}, BytesIO(b'{"error":{"message":"out of memory"}}'))
    assert capture_http_error(other, "SECRET")["classification"] == "UNKNOWN_BACKEND_ERROR"
    leak = HTTPError("http://127.0.0.1", 500, "error", {}, BytesIO(b"Bearer SECRET"))
    assert "SECRET" not in capture_http_error(leak, "SECRET")["body_excerpt"]
    print("[PASS] bounded HTTP body hash, exact PEG classification, API key redaction")


if __name__ == "__main__":
    self_test()
