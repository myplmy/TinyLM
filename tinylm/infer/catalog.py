"""Checkpoint catalog backed by filenames and training JSON metadata.

Discovery never loads a checkpoint.  That keeps model selection cheap and lets
the interactive probe show the exact validation metric before the user chooses
to pay model-loading cost.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
from pathlib import Path


CKPT_NAME = re.compile(
    r"^(?P<preset>[^_]+)_(?P<data>[^_]+)_(?P<tokens>\d+(?:\.\d+)?[MB])_(?P<tag>.+)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ModelRecord:
    checkpoint: Path
    stem: str
    preset: str
    data: str
    tokens: str
    tag: str
    arch: str | None
    final_val: float | None
    best_val: float | None
    steps: int | None
    pool_tokens: int | None
    optimizer: str | None
    seed: int | None
    is_best: bool
    log_path: Path | None

    @property
    def display_val(self) -> float | None:
        return self.best_val if self.is_best else self.final_val

    @property
    def selector(self) -> str:
        return self.tag + ("_best" if self.is_best and not self.tag.endswith("_best") else "")


def _number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _integer_tokens(value):
    if value is None:
        return None
    text = str(value).strip()
    scale = 1
    if text[-1:].lower() == "m":
        text, scale = text[:-1], 1_000_000
    elif text[-1:].lower() == "b":
        text, scale = text[:-1], 1_000_000_000
    try:
        return int(float(text) * scale)
    except ValueError:
        return None


def discover_models(ckpt_dir: Path, log_dir: Path) -> list[ModelRecord]:
    records = []
    for checkpoint in sorted(Path(ckpt_dir).glob("*.pt")):
        is_best = checkpoint.stem.endswith("_best")
        base_stem = checkpoint.stem[:-5] if is_best else checkpoint.stem
        match = CKPT_NAME.match(base_stem)
        if match is None:
            preset = data = tokens = "?"
            tag = base_stem
        else:
            preset, data, tokens, tag = (
                match.group("preset"), match.group("data"),
                match.group("tokens"), match.group("tag"),
            )
        log_path = Path(log_dir) / f"{base_stem}.json"
        metadata = {}
        if log_path.is_file():
            try:
                metadata = json.loads(log_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                metadata = {}
        final = metadata.get("final") or {}
        pool = metadata.get("pool_tokens")
        records.append(ModelRecord(
            checkpoint=checkpoint.resolve(),
            stem=checkpoint.stem,
            preset=str(metadata.get("preset") or preset),
            data=str(metadata.get("data") or data),
            tokens=tokens,
            tag=tag,
            arch=(str(metadata["arch"]) if metadata.get("arch") else None),
            final_val=_number(final.get("val_loss")),
            best_val=_number(metadata.get("best_val")),
            steps=(int(metadata["steps"]) if metadata.get("steps") is not None else None),
            pool_tokens=_integer_tokens(pool),
            optimizer=(str(metadata["optimizer"]) if metadata.get("optimizer") else None),
            seed=(int(metadata["seed"]) if metadata.get("seed") is not None else None),
            is_best=is_best,
            log_path=log_path.resolve() if log_path.is_file() else None,
        ))
    return sorted(
        records,
        key=lambda row: (
            row.display_val is None,
            row.display_val if row.display_val is not None else float("inf"),
            row.stem,
        ),
    )


def filter_models(records: list[ModelRecord], query: str) -> list[ModelRecord]:
    needle = query.strip().lower()
    if not needle:
        return list(records)
    return [
        row for row in records
        if needle in " ".join((row.stem, row.tag, row.preset, row.data)).lower()
    ]


def resolve_selection(records: list[ModelRecord], selection: str) -> ModelRecord:
    text = selection.strip()
    if text.isdigit():
        index = int(text)
        if 1 <= index <= len(records):
            return records[index - 1]
        raise ValueError(f"번호 범위는 1..{len(records)}입니다")
    exact = [row for row in records if text.lower() in {row.selector.lower(), row.stem.lower()}]
    if len(exact) == 1:
        return exact[0]
    partial = filter_models(records, text)
    if len(partial) == 1:
        return partial[0]
    if not partial:
        raise ValueError(f"일치 모델이 없습니다: {text!r}")
    raise ValueError(
        f"{text!r}가 {len(partial)}개 모델과 일치합니다: "
        + ", ".join(row.selector for row in partial[:8])
    )
