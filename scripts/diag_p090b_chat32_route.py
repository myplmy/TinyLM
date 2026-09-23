#!/usr/bin/env python3
"""P090B chat32 prepare negative-contract fixture; no data/model/GPU writes."""
from __future__ import annotations

import inspect
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    from tinylm.data.prepare import prepare, chat_tokenizer_path, tokenizer_path
    if inspect.signature(prepare).parameters["chat32"].default is not False:
        raise AssertionError("chat32 must be opt-in")
    if chat_tokenizer_path("ko-en") == tokenizer_path("ko-en"):
        raise AssertionError("chat32 tokenizer would overwrite legacy")
    invalid = (
        dict(name="synthetic", n_tokens=2, exact=True, chat32=True),
        dict(name="ko-en", n_tokens=2, exact=False, chat32=True),
        dict(name="ko-en", n_tokens=2, exact=True, hf_tok="external", chat32=True),
    )
    for kwargs in invalid:
        try:
            prepare(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid chat32 preparation reached an I/O path")
    print("[PASS] chat32 opt-in, isolated name and forbidden-route guards; cache/model/GPU NOT_RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
