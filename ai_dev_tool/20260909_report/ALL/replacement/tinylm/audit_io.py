"""평가/파일럿의 파일·ID 계약. 모델 및 GPU를 import하지 않는다."""
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
            rows = obj[keys]
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
    """기존 산출물을 덮어쓰지 않는다. 출력 경로는 호출자가 명시한다."""
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
    explicit = row.get("id", row.get("task_id"))
    if explicit is not None:
        return f"{task}:{explicit}"
    # 위치와 내용 모두 고정한다. 자료 변경 시 같은 ID를 재사용하지 않는다.
    return f"{task}:{index}:{digest_json(row)[:16]}"


def tokenizer_digest(tok):
    backend = getattr(tok, "backend_tokenizer", None)
    if backend is not None:
        return hashlib.sha256(backend.to_str().encode("utf-8")).hexdigest()
    if hasattr(tok, "to_str"):
        return hashlib.sha256(tok.to_str().encode("utf-8")).hexdigest()
    inner = getattr(tok, "inner", None)
    if inner is not None:
        return tokenizer_digest(inner)
    raise TypeError("tokenizer serialization을 확인할 수 없음; 해시를 추측하지 않음")
