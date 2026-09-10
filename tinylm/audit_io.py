# -*- coding: utf-8 -*-
"""평가·진단 산출물의 **파일·ID 계약**. 🚫모델도 GPU 도 import 하지 않는다.

## 출처 — 외부 조치 패키지 A08 (2026-09-10 도입)

`ai_dev_tool/20260909_report/A08/replacement/tinylm/audit_io.py` 를 받았다.
[적용 보고서](../docs/20260910_외부-조치-패키지-적용-보고서.md) §A08 이 무엇을 받고
무엇을 안 받았는지 적는다. **가져오면서 고친 것 둘**:

| # | 원본 | ★우리 판 | 왜 |
|---|---|---|---|
| **1** | `rows = obj[keys]` | ★`rows = obj[keys[0]]` | 🚫**실물 버그.** `keys` 는 리스트라 `dict[list]` 는 `TypeError: unhashable type: 'list'` 다. 그 분기는 **한 번도 안 돌았다는 뜻**이다 |
| **2** | `tinylm/eval/audit_io.py` 재수출 파일 | 🚫**안 만들었다** | 함정 18 — **한 개념을 두 곳에서 정의하지 않는다.** 새 코드는 `tinylm.audit_io` 를 직접 부른다 |

## 왜 이 파일이 우리에게 값어치가 있나

우리 진단 도구들이 각자 **JSON 을 읽고 쓰는 방식을 따로** 갖고 있었다. 특히 셋:

- ★**덮어쓰기 방지**(`write_json_new` 의 `open("x")`) — 🚫우리는 `Path.write_text` 로
  **먼저 지우고** 쓴 적이 있고 그것이 함정 35 다(인코딩 실패 시 0바이트).
- ★**문항 ID 규약**(`item_id`) — 자료가 바뀌면 **같은 ID 를 재사용하지 않는다**.
  held-out 이 v2.7 → v2.8 로 바뀌면서 우리가 정확히 이 문제를 만났다.
- ★**토크나이저 지문**(`tokenizer_digest`) — 🚫**해시를 추측하지 않고** 못 구하면 `TypeError`.
"""
from __future__ import annotations

import glob
import hashlib
import json
from pathlib import Path


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def digest_json(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def read_records(path):
    """`.jsonl` 또는 레코드 배열을 담은 `.json` 을 읽는다.

    ★**배열 키를 하나로 특정하지 못하면 거절한다** — `records`/`data`/`items`/`examples`
    중 둘 이상이 리스트면 어느 것이 본문인지 **추측하지 않는다**.
    """
    path = Path(path)
    if path.suffix.lower() == ".jsonl":
        with path.open(encoding="utf-8-sig") as f:
            rows = [json.loads(line) for line in f if line.strip()]
    else:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(obj, list):
            rows = obj
        elif isinstance(obj, dict):
            keys = [k for k in ("records", "data", "items", "examples")
                    if isinstance(obj.get(k), list)]
            if len(keys) != 1:
                raise ValueError(f"{path}: 레코드 배열 키를 하나로 특정할 수 없음: {keys}")
            # ★수정 1 — 원본은 `obj[keys]` 였다(리스트로 인덱싱 = TypeError).
            rows = obj[keys[0]]
        else:
            raise ValueError(f"{path}: list/object 필요")
    if not rows or any(not isinstance(r, dict) for r in rows):
        raise ValueError(f"{path}: 비어 있지 않은 object 레코드 배열 필요")
    return rows


def expanded_paths(patterns):
    found = {}
    for pattern in patterns or []:
        matches = sorted(glob.glob(str(pattern), recursive=True))
        if not matches:
            raise FileNotFoundError(f"일치 파일 없음: {pattern}")
        for name in matches:
            p = Path(name).resolve()
            if p.is_file():
                found[str(p)] = p
    return [found[k] for k in sorted(found)]


def write_json_new(path, obj):
    """★기존 산출물을 덮어쓰지 않는다(`open("x")`). 출력 경로는 호출자가 명시한다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def write_jsonl_new(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def item_id(task, row, index):
    """문항 ID. ★**자료가 바뀌면 같은 ID 를 재사용하지 않는다**(위치 + 내용 해시)."""
    explicit = row.get("id", row.get("task_id"))
    if explicit is not None:
        return f"{task}:{explicit}"
    return f"{task}:{index}:{digest_json(row)[:16]}"


def tokenizer_digest(tok):
    """토크나이저 지문. 🚫**직렬화를 못 구하면 해시를 추측하지 않고 `TypeError`.**"""
    backend = getattr(tok, "backend_tokenizer", None)
    if backend is not None:
        return hashlib.sha256(backend.to_str().encode("utf-8")).hexdigest()
    if hasattr(tok, "to_str"):
        return hashlib.sha256(tok.to_str().encode("utf-8")).hexdigest()
    inner = getattr(tok, "inner", None)
    if inner is not None:
        return tokenizer_digest(inner)
    raise TypeError("tokenizer serialization을 확인할 수 없음; 해시를 추측하지 않음")
