#!/usr/bin/env python3
"""Static BAT/SH input-tag and required-checkpoint guard audit (no model/GPU).

An output ``--tag`` is intentionally new and must NOT be required to exist.
Input ``--models`` / ``--init-from[-tag]`` / ``--kd-teacher-tag`` and explicit
required-file guards must resolve to a real, non-linked checkpoint. This is a
current-worktree gate, not an assertion that the model can load successfully.
"""
from __future__ import annotations

import argparse
from itertools import product
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from dryrun_batch import (  # noqa: E402
    _judge_model_spec, _judge_val, _judge_values, _norm_tok,
    _preset_parent, launcher_calls,
)

LOOP = re.compile(r"\bfor\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\s+([^;\n]+);\s*do")
SHELL_ASSIGN = re.compile(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)=(?:\"([^\"]*)\"|'([^']*)'|([^\s#;]+))\s*$")
BAT_ASSIGN = re.compile(r'(?im)^\s*set\s+"?([A-Za-z_][A-Za-z0-9_]*)=([^"\r\n]*)"?\s*$')
VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)|!([A-Za-z_][A-Za-z0-9_]*)!")
SHELL_REQUIRED = re.compile(r"(?:^|\s)-f\s+['\"]?([^'\"\s\]]+)", re.M)
BAT_REQUIRED = re.compile(r'(?im)\bif\s+not\s+exist\s+["\']?([^"\'\s]+)')
BAD_NAME = re.compile(r"[^A-Za-z0-9_.-]")


def _usable_checkpoint(path: Path) -> bool:
    return not path.is_symlink() and path.is_file()


def _resolve(root: Path, preset: str, data: str, tok: str, tag: str) -> tuple[Path | None, str]:
    if any(BAD_NAME.search(value) for value in (preset, data, tok, tag)):
        return None, "dynamic or unsafe checkpoint name"
    ckpt = root / "runs" / "ckpt"
    for parent in (preset, _preset_parent().get(preset)):
        if not parent:
            continue
        candidate = ckpt / f"{parent}_{data}_{tok}_{tag}.pt"
        if _usable_checkpoint(candidate):
            return candidate, "exact/preset-parent"
    hits = [path for path in ckpt.glob(f"*_{data}_{tok}_{tag}.pt")
            if _usable_checkpoint(path)]
    if len(hits) == 1:
        return hits[0], "single cross-preset match"
    return None, f"{len(hits)} matching independent checkpoint files"


def _variables(text: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for match in LOOP.finditer(text):
        raw = match.group(2).split()
        if raw and all(not any(char in token for char in "*$!()") for token in raw):
            values[match.group(1)] = [token.strip("\"'") for token in raw]
    for pattern in (SHELL_ASSIGN, BAT_ASSIGN):
        for match in pattern.finditer(text):
            name = match.group(1)
            raw = next((part for part in match.groups()[1:] if part is not None), "")
            if "$ (" in raw or "$(" in raw:
                continue
            expanded = _expand(raw, values)
            if expanded is not None:
                values[name] = expanded
    return values


def _expand(raw: str, values: dict[str, list[str]]) -> list[str] | None:
    names = list(dict.fromkeys(next(group for group in match.groups() if group)
                               for match in VAR.finditer(raw)))
    if not names:
        return [raw.strip("\"'")]
    if any(name not in values for name in names):
        return None
    combinations = list(product(*(values[name] for name in names)))
    if len(combinations) > 128:
        return None
    output = []
    for combination in combinations:
        selected = dict(zip(names, combination))
        output.append(VAR.sub(
            lambda match: selected[next(group for group in match.groups() if group)], raw
        ).strip("\"'"))
    return sorted(set(output))


def _required_guards(text: str, variables: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    paths, errors = [], []
    logical = re.sub(r"\\[ \t]*\r?\n[ \t]*", " ", text)
    for pattern in (SHELL_REQUIRED, BAT_REQUIRED):
        for match in pattern.finditer(logical):
            raw = match.group(1).strip("\"'")
            expanded = _expand(raw, variables)
            if expanded is None:
                if "ckpt" in raw.lower() or raw.startswith(("$", "!")):
                    errors.append(f"unresolved required-file guard variable: {raw}")
                continue
            for path in expanded:
                norm = path.replace("\\", "/")
                if norm.startswith("runs/ckpt/"):
                    paths.append(norm)
    return sorted(set(paths)), errors


def _reference_calls(text: str, variables: dict[str, list[str]]):
    for script, rest in launcher_calls(text):
        name = Path(script.replace("\\", "/")).name
        preset = _judge_val(rest, "--preset", "m100")
        data = _judge_val(rest, "--data", "ko-en")
        tok = _norm_tok(_judge_val(rest, "--ckpt-tokens")
                        or _judge_val(rest, "--tokens", "300M"))
        if name == "run100m.py" and re.match(r"\s*train\b", rest):
            inputs = []
            init_tag = _judge_val(rest, "--init-from-tag")
            if init_tag:
                inputs.append(("init-from-tag", init_tag, preset, data, tok))
            elif re.search(r"(?:^|\s)--init-from(?:\s|$)", rest):
                inputs.append(("init-from", "dense", preset, data, tok))
            if re.search(r"(?:^|\s)--kd(?:\s|$)", rest):
                kd_tag = (_judge_val(rest, "--kd-teacher-tag")
                          or ("dense_best" if "--kd-best" in rest else "dense"))
                inputs.append(("kd-teacher", kd_tag, preset, data, tok))
            for item in inputs:
                yield item
            continue
        if "--models" not in rest:
            continue
        tags = _judge_values(rest, "--models")
        if not tags:
            yield ("models", "UNRESOLVED_MODELS", preset, data, tok)
            continue
        per_data = _judge_values(rest, "--model-data")
        if not per_data and name == "common_bpb.py":
            per_data = _judge_values(rest, "--data")
        if len(per_data) == 1:
            per_data *= len(tags)
        if len(per_data) != len(tags):
            per_data = [data] * len(tags)
        per_tokens = _judge_values(rest, "--tokens")
        if len(per_tokens) != len(tags):
            per_tokens = [tok] * len(tags)
        else:
            per_tokens = [_norm_tok(value) for value in per_tokens]
        for raw, tdata, ctok in zip(tags, per_data, per_tokens):
            expanded = _expand(raw, variables)
            if expanded is None:
                yield ("models", "UNRESOLVED_MODELS", preset, tdata, ctok)
                continue
            for value in expanded:
                tag, model_preset = _judge_model_spec(value, preset)
                yield ("models", tag, model_preset, tdata, ctok)


def audit_launcher(root: Path, launcher: Path, source_text: str | None = None) -> tuple[list[str], int]:
    text = source_text if source_text is not None else launcher.read_text(encoding="utf-8")
    variables = _variables(text)
    errors: list[str] = []
    checked = 0
    guards, guard_errors = _required_guards(text, variables)
    errors.extend(guard_errors)
    for name in guards:
        checked += 1
        path = root / name
        if not _usable_checkpoint(path):
            errors.append(f"required checkpoint guard does not resolve: {name}")
    for role, tag, preset, data, tok in _reference_calls(text, variables):
        checked += 1
        found, reason = _resolve(root, preset, data, tok, tag)
        if found is None:
            errors.append(f"{role} input tag absent/ambiguous: {tag} "
                          f"(preset={preset},data={data},ckpt-tokens={tok}; {reason})")
    return sorted(set(errors)), checked


def live_launchers(root: Path) -> list[Path]:
    # scripts/batch/tool_*.bat are parameterized helpers, not standalone
    # experiment launchers; their TL_MODELS values can be overridden by a
    # caller. Audit the resolved root run_*.bat/.sh instead.
    paths = [*root.glob("run*.bat"), *root.glob("run*.sh")]
    return sorted((path for path in paths if path.is_file()
                   and "-done" not in path.name and "-cancel" not in path.name
                   and "-hold" not in path.name),
                  key=lambda path: path.as_posix())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("launchers", nargs="*")
    args = parser.parse_args()
    paths = [ROOT / item for item in args.launchers] if args.launchers else live_launchers(ROOT)
    errors, checked = [], 0
    for path in paths:
        if path.is_symlink() or not path.is_file():
            errors.append(f"launcher missing or linked: {path}")
            continue
        current, count = audit_launcher(ROOT, path)
        checked += count
        for problem in current:
            errors.append(f"{path.relative_to(ROOT)}: {problem}")
    for problem in errors:
        print("[FAIL] " + problem)
    print(f"SUMMARY launchers={len(paths)} input_tag_or_guard_refs={checked} errors={len(errors)} "
          "output_tags_are_new_and_not_required_to_exist=1")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
