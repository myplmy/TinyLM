#!/usr/bin/env python3
"""Public C preparation for P106B; no network, protected data or model execution.

The 75M target is non-padding chat32 train tokens, not padded positions. Public
normalization stays distinct from teacher-generated pseudo-labels. Every row
retains pinned source and group provenance. A shortfall is recorded, not filled
by repeating rows. Outputs are new ignored <=20MB shards, never prior corpora.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_shards import ShardWriter, verify
from tinylm.chat.canonical import normalize, validate
from tinylm.data.sft import IGNORE, conversation_split_key, encode_conversation, sft_targets

OUTPUT = ROOT / "HF/sft_ready/p106b_mixed_public_v1"
TOKENIZER = ROOT / "data_cache/tok-ko-en-32768-chat32.json"
TOK_SHA = "9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E"
GOAL = 37_500_000
# Source identities, not a blacklist of supposedly incorrect answer strings.
COLLECTION_EXCLUDED = {"PIQA (T)", "Flan-lambada (T)", "Flan-unified-QA (T)",
                       "Flan-CoT-submix (T)"}
COLLECTION_FILES = (
    ("HF/sft_sources/aya_collection_ko/korean/train-00000-of-00002.parquet",
     "0EED3F48935418B4B8C1FF55AD8DD8D2EDCDEA2BEFDB2A61A6953CC5403340F1"),
    ("HF/sft_sources/aya_collection_ko/korean/train-00001-of-00002.parquet",
     "42BD2F8956B74881F5FE02787388A984EA9C62A7115E98E49350F3EA963015E3"),
)
EXTRA_MANIFEST = ROOT / "HF/sft_ready/p106b_mixed_extra_public_sources.json"


def digest(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"exact input missing or linked: {path}")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest().upper()


def public_file(relative):
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts or not raw.parts[:2] == ("HF", "sft_sources"):
        raise ValueError("extra public source must be an exact HF/sft_sources file")
    path = ROOT / raw
    for part in (path, *path.parents):
        if part == ROOT:
            break
        if part.is_symlink():
            raise ValueError("linked public input refused")
    if not path.is_file():
        raise ValueError("extra public source absent")
    return path


def safe_repo_path(path):
    """Refuse linked parents before any user-owned read or new output write."""
    path = Path(path)
    if not path.is_relative_to(ROOT) or path == ROOT:
        raise ValueError("path escapes the checkout")
    for part in (path, *path.parents):
        if part == ROOT:
            break
        if part.is_symlink():
            raise ValueError("linked path component refused")
    return path


def source_specs():
    from scripts.prepare_public_sft import SOURCES
    specs = []
    for name, directory in (("aya", "aya"), ("oasst1", "oasst")):
        spec = SOURCES["aya" if name == "aya" else "oasst"]
        specs.append({"family": name, "path": f"HF/sft_sources/{directory}/{spec['data']}",
                      "repo": spec["repo"], "revision": spec["revision"], "license": spec["license"],
                      "sha256": {"aya": "51BAA85043B569BA117F41516B32D1B0E4E2647FB203A08933F98A556FB1FB06",
                                 "oasst1": "2A9A8FD343E9B28E04A895A669D3253F82D93E9C174D440199AE19D5FAFBDFF7"}[name]})
    specs.append({"family": "oasst2", "path": "HF/sft_sources/p090_oasst2_179dd21/2023-11-05_oasst2_ready.trees.jsonl.gz",
                  "repo": "OpenAssistant/oasst2", "revision": "179dd21fc55192153d94adb0e0ce8f69e222bf75",
                  "license": "Apache-2.0", "sha256": "7A886A16CCFC1173C4F00A6897523E3C95B2785A86EE44A18A98F4F2807EE29B"})
    for relative, sha in COLLECTION_FILES:
        specs.append({"family": "aya_collection", "path": relative, "sha256": sha,
                      "repo": "CohereLabs/aya_collection_language_split",
                      "revision": "a3af2fde4b4cb5b2775830b11244a1a20b5f004f", "license": "Apache-2.0_card"})
    safe_repo_path(EXTRA_MANIFEST)
    if EXTRA_MANIFEST.exists() or EXTRA_MANIFEST.is_symlink():
        digest(EXTRA_MANIFEST)
        extra = json.loads(EXTRA_MANIFEST.read_text(encoding="utf-8"))
        if extra.get("schema") != "P106B_EXTRA_PUBLIC_SOURCES_V1":
            raise ValueError("extra public manifest schema differs")
        for item in extra.get("sources", []):
            if (item.get("family") != "messages_parquet" or item.get("language") != "en"
                    or item.get("original_split") != "train_sft" or item.get("usage_review") != "USER_DECLARED"
                    or not item.get("license") or len(item.get("revision", "")) != 40):
                raise ValueError("extra source needs pinned English train_sft and user-declared usage")
            if item.get("repo") != "HuggingFaceH4/ultrachat_200k":
                raise ValueError("extra repo not in the investigated source adapter")
            specs.append(item)
    for spec in specs:
        if digest(public_file(spec["path"])) != spec["sha256"]:
            raise ValueError(f"pinned public source SHA differs: {spec['family']}")
    return specs


def attach(messages, spec, ident, language, family=None):
    return validate(normalize({"messages": messages, "meta": {
        "source": "p106b_public_direct", "source_family": family or spec["family"],
        "source_id": str(ident), "source_repo": spec["repo"], "source_revision": spec["revision"],
        "source_sha256": spec["sha256"], "source_license": spec["license"],
        "source_transform": "public_normalization", "rights_status": "CARD_ONLY",
        "language": language, "label_status": "PUBLIC_SOURCE_UNVERIFIED",
        "semantic_truth": "NOT_REVIEWED"}}))


def reviewed(n, role, language, parent=None):
    return (isinstance(n, dict) and n.get("role") == role and n.get("lang") == language
            and n.get("review_result") is True and isinstance(n.get("review_count"), int)
            and n["review_count"] >= 1 and not n.get("deleted") and n.get("synthetic") is False
            and isinstance(n.get("text"), str) and bool(n["text"].strip())
            and isinstance(n.get("message_id"), str)
            and (parent is None or n.get("parent_id") == parent))


def rows_for(spec):
    path = public_file(spec["path"])
    if spec["family"] in {"aya", "aya_collection", "messages_parquet"}:
        import pyarrow.parquet as pq
        columns = {"aya": ["inputs", "targets", "language_code", "annotation_type"],
                   "aya_collection": ["id", "inputs", "targets", "dataset_name"],
                   "messages_parquet": ["prompt_id", "messages"]}[spec["family"]]
        index = 0
        for batch in pq.ParquetFile(path).iter_batches(batch_size=512, columns=columns):
            for row in batch.to_pylist():
                ordinal = index
                index += 1
                if spec["family"] == "messages_parquet":
                    messages = row.get("messages")
                    if not isinstance(messages, list) or len(messages) < 2:
                        continue
                    yield attach(messages, spec, row.get("prompt_id") or ordinal, "en")
                    continue
                family = row.get("dataset_name") or "aya:" + str(row.get("annotation_type"))
                if spec["family"] == "aya_collection" and family in COLLECTION_EXCLUDED:
                    continue
                language = "ko" if spec["family"] == "aya_collection" else {"eng": "en", "kor": "ko"}.get(row.get("language_code"))
                q, a = row.get("inputs"), row.get("targets")
                if language is None or not isinstance(q, str) or not isinstance(a, str) or not q.strip() or not a.strip():
                    continue
                messages = [{"role": "user", "content": q.strip()}, {"role": "assistant", "content": a.strip()}]
                yield attach(messages, spec, f"{Path(spec['path']).name}:{ordinal}", language, family)
    else:
        from scripts.prepare_public_sft import oasst_tree_to_canonical
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                tree = json.loads(line)
                if spec["family"] == "oasst1":
                    row = oasst_tree_to_canonical(tree)
                    if row is not None:
                        yield attach(row["messages"], spec, row["meta"]["source_id"], row["meta"]["language"])
                    continue
                node = tree.get("prompt")
                language = node.get("lang") if isinstance(node, dict) else None
                if tree.get("tree_state") != "ready_for_export" or language not in {"ko", "en"} or not reviewed(node, "prompter", language):
                    continue
                messages = []
                while node is not None:
                    role = "prompter" if not messages or messages[-1]["role"] == "assistant" else "assistant"
                    if not reviewed(node, role, language):
                        break
                    messages.append({"role": "user" if role == "prompter" else "assistant", "content": node["text"].strip()})
                    nxt = "assistant" if role == "prompter" else "prompter"
                    children = [c for c in (node.get("replies") or []) if reviewed(c, nxt, language, node["message_id"])]
                    node = min(children, key=lambda c: (c.get("rank") is None, c["rank"] if isinstance(c.get("rank"), int) else 999, c["message_id"])) if children else None
                if len(messages) >= 2 and messages[-1]["role"] == "assistant":
                    yield attach(messages, spec, tree.get("message_tree_id") or tree["prompt"]["message_id"], language)


class Selector:
    def __init__(self, tok, *, goal=GOAL, probe_keys=()):
        self.tok, self.goal = tok, goal
        self.seen, self.probes = set(), set(probe_keys)
        self.tokens, self.targets, self.rows, self.rejections, self.families = Counter(), Counter(), Counter(), Counter(), Counter()

    def consider(self, row):
        from scripts.p106b_teacher_wrapper import BOUNDARY_MARKERS
        roles = [message.get("role") for message in row["messages"]]
        conversational = roles[1:] if roles[:1] == ["system"] else roles
        if (len(conversational) < 2 or conversational[-1] != "assistant"
                or any(role != ("user" if i % 2 == 0 else "assistant") for i, role in enumerate(conversational))):
            self.rejections["role_order"] += 1
            return None
        for message in row["messages"]:
            for block in message["content"]:
                if block.get("type") != "text":
                    self.rejections["unsupported_block_type"] += 1
                    return None
                value = block["text"]
                if any(marker in value for marker in BOUNDARY_MARKERS) or any(ord(c) < 32 and c not in "\n\t" for c in value):
                    self.rejections["chat_boundary_or_control"] += 1
                    return None
        key = conversation_split_key(row)
        language = row["meta"]["language"]
        split = "val" if int.from_bytes(key[:4], "big") % 20 == 0 else "train"
        quota = self.goal if split == "train" else max(1, self.goal // 19)
        if self.tokens[split + ":" + language] >= quota:
            return None
        if key in self.probes:
            self.rejections["fixed_probe_question"] += 1
            return None
        if key in self.seen:
            self.rejections["same_first_question"] += 1
            return None
        ids, labels, _ = encode_conversation(row, self.tok)
        x, y = sft_targets(ids, labels)
        count = sum(v != IGNORE for v in y)
        if not 0 < len(x) <= 1024 or count == 0:
            self.rejections["context_or_mask"] += 1
            return None
        # Only complete rows contribute, with <=1023 token quota overshoot.
        self.seen.add(key)
        name = split + ":" + language
        self.tokens[name] += len(x)
        self.targets[name] += count
        self.rows[name] += 1
        self.families[name + ":" + row["meta"]["source_family"]] += len(x)
        row["meta"].update(source_split=split, parent_concept_id=key.hex().upper(),
                           processed_x_tokens=len(x), assistant_targets=count)
        return split, row

    def report(self):
        deficits = {lang: max(0, self.goal - self.tokens["train:" + lang]) for lang in ("ko", "en")}
        return {"rows": dict(self.rows), "nonpadding_tokens": dict(self.tokens),
                "assistant_targets": dict(self.targets), "family_tokens": dict(self.families),
                "rejected": dict(self.rejections), "teacher_deficit_tokens": deficits,
                "token_target_ready": not any(deficits.values()), "formal_train_ready": False,
                "semantic_quality": "NOT_REVIEWED", "broad_benchmark_contamination": "NOT_RUN"}


def prepare(specs):
    from tokenizers import Tokenizer
    from scripts.p106b_education_followup import PROBES
    safe_repo_path(OUTPUT)
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError("preserve public C output; next retry requires a new version")
    tok = Tokenizer.from_file(str(TOKENIZER))
    probes = [conversation_split_key(normalize({"messages": [{"role": "user", "content": q}, {"role": "assistant", "content": "probe"}]})) for _, q in PROBES]
    selector = Selector(tok, probe_keys=probes)
    OUTPUT.mkdir(parents=True, exist_ok=False)
    writers = {s: ShardWriter(OUTPUT, s) for s in ("train", "val")}
    began = time.perf_counter()
    for spec in specs:
        for row in rows_for(spec):
            if all(selector.tokens["train:" + lang] >= GOAL and selector.tokens["val:" + lang] >= GOAL // 19 for lang in ("ko", "en")):
                break
            item = selector.consider(row)
            if item:
                writers[item[0]].append(item[1])
        print("[PUBLIC_SOURCE] " + json.dumps({"family": spec["family"], **selector.report()}, ensure_ascii=False), flush=True)
    report = {"schema": "P106B_MIXED_PUBLIC_C_V1", "status": "PUBLIC_C_PREPARED_WITH_DEFICIT",
              "sources": specs, "tokenizer_sha256": TOK_SHA, "goal_train_tokens_per_language": GOAL,
              "student_micro": 8, "student_accum": 16, "checkpoint_on": True, "epochs": 4,
              "target_processed_tokens": 300_000_000, "split": "global normalized first user question hash modulo20",
              "excluded_source_families": sorted(COLLECTION_EXCLUDED), **selector.report(),
              "whole_wall_sec": time.perf_counter() - began, "student_training": "NOT_RUN"}
    for split, writer in writers.items():
        if writer._total_rows:
            spec = writer.close(lineage={"sources": specs, "tokenizer_sha256": TOK_SHA})
            verify(OUTPUT, spec)
            report[split + "_concat_sha256"] = spec["concat_sha256"]
    report["status"] = "PUBLIC_C_TOKEN_TARGET_READY" if report["token_target_ready"] else "PUBLIC_C_PREPARED_WITH_DEFICIT"
    with (OUTPUT / "report.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("[PUBLIC_SCALE_SUMMARY] " + json.dumps(report, ensure_ascii=False), flush=True)
    # Success is durable preparation and an honest shortfall report, not SFT approval.
    return 0 if sum(selector.rows.values()) else 8


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    args = ap.parse_args()
    safe_repo_path(TOKENIZER)
    safe_repo_path(OUTPUT)
    if digest(TOKENIZER) != TOK_SHA:
        raise ValueError("chat32 tokenizer differs")
    specs = source_specs()
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError("public output already exists; originals preserved")
    if args.check_only:
        print(json.dumps({"schema": "P106B_MIXED_PUBLIC_PREFLIGHT_V1", "sources": specs,
                          "output": str(OUTPUT.relative_to(ROOT)), "goal_train_tokens_per_language": GOAL,
                          "student_training": "NOT_RUN", "source_quality": "NOT_REVIEWED"}, ensure_ascii=False))
        return 0
    return prepare(specs)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, FileExistsError, FileNotFoundError) as exc:
        print(f"[STOP] {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(9)
