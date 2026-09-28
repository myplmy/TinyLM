#!/usr/bin/env python3
"""P106B Stage2kW: provenance-first Aya/OASST2/dictionary source deck.

The default is a READ-ONLY census. Executing the combined deck is gated by a
user-owned exact-source rights/derivative-use attestation in ignored HF. The
deck stores public Aya/OASST2 text, but only LOCATORS for protected Korean
dictionary senses. `concept/word-*` and the two vocabulary TXT files are
selection/coverage evidence, not independent QA rows. No teacher/model/GPU is
invoked here and no answer is ever marked verified or TRAIN_READY.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_p106b_job_deck import digest, plain  # noqa: E402
from scripts.diag_p090b_oasst2_translation_candidates import (  # noqa: E402
    SOURCE as OASST2, SOURCE_SHA256 as OASST2_SHA,
)
from scripts.p106b_shards import ShardWriter, verify  # noqa: E402
from scripts.diag_p106_coload import _http_json  # noqa: E402
from scripts.p106b_teacher_format import teacher_prompt  # noqa: E402
from scripts.p106b_teacher_wrapper import wrap_turns  # noqa: E402
from tinylm.chat.canonical import normalize  # noqa: E402
from tinylm.data.sft import conversation_split_key, load_canonical  # noqa: E402

PUBLIC_DIR = ROOT / "HF/sft_ready"
PUBLIC_MANIFEST = PUBLIC_DIR / "p090_public_v3_manifest.json"
PUBLIC_SPLITS = {name: PUBLIC_DIR / f"p090_public_v3_{name}.canonical.jsonl"
                 for name in ("train", "val")}
PROTECTED_ROOT = Path("/mnt/z/TinyDataset")
DICT_DIR = PROTECTED_ROOT / "참고용외부데이터/국립국어원/한국어기초사전/한국어기초사전_json_20260819"
WORD_DIR = PROTECTED_ROOT / "concept"
LEXICON_DIR = DICT_DIR.parent
VOCAB_TXT = (LEXICON_DIR / "한국어 학습용 어휘 목록.txt",
             LEXICON_DIR / "한국어기초 어휘(4만개).txt")
OUTPUT_DIR = PUBLIC_DIR / "p106b_multisource_v1/jobs"
APPROVAL = PUBLIC_DIR / "p106b_multisource_rights_approval.json"
OASST2_REVISION = "179dd21fc55192153d94adb0e0ce8f69e222bf75"
DICT_REPO = "https://krdict.korean.go.kr"
DICT_RIGHTS = "LOCAL_RIGHTS_REVIEW"


def _regular(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _seq(value):
    return value if isinstance(value, list) else [value] if isinstance(value, dict) else []


def _feat(value, key: str) -> str:
    for entry in _seq(value):
        if isinstance(entry, dict) and entry.get("att") == key:
            return str(entry.get("val") or "")
    return ""


def _text(path: Path) -> str:
    if not _regular(path):
        raise FileNotFoundError(f"named protected reference absent/linked: {path}")
    data = path.read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp949")


def protected_inventory() -> tuple[list[Path], list[Path], dict, set[str]]:
    if DICT_DIR.is_symlink() or WORD_DIR.is_symlink() or not DICT_DIR.is_dir():
        raise FileNotFoundError("exact Korean dictionary/concept directories absent or linked")
    dictionary = sorted(DICT_DIR.glob("*.json"))
    words = sorted(WORD_DIR.glob("word-*.txt"))
    if len(dictionary) != 11 or len(words) != 27 or any(not _regular(p) for p in (*dictionary, *words, *VOCAB_TXT)):
        raise ValueError("expected exact 11 dictionary JSON, 27 concept word files and 2 TXT refs")
    if not all(re.fullmatch(r"(?:[1-9]|10)_5000_20260819\.json|11_3671_20260819\.json", p.name)
               for p in dictionary):
        raise ValueError("dictionary JSON filename/version differs")
    names: set[str] = set()
    for path in words:
        names.update(line.strip() for line in _text(path).splitlines() if line.strip())
    source = {"dictionary": {p.name: digest(p) for p in dictionary},
              "concept_word_files": {p.name: digest(p) for p in words},
              "vocabulary_txt": {p.name: digest(p) for p in VOCAB_TXT},
              "dictionary_rights": DICT_RIGHTS,
              "word_role": "priority/coverage only, not independent QA concepts"}
    return dictionary, words, source, names


def public_inventory() -> tuple[dict, set[bytes]]:
    if not _regular(PUBLIC_MANIFEST):
        raise FileNotFoundError("public v3 manifest absent/linked")
    manifest = json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
    sources = manifest.get("sources", {})
    if (sources.get("aya", {}).get("repo") != "CohereLabs/aya_dataset"
            or sources.get("oasst", {}).get("repo") != "OpenAssistant/oasst1"
            or manifest.get("schema") != "TINYLM_PUBLIC_SFT_V1"):
        raise ValueError("public v3 source repos differ; Aya Dataset != Aya Collection")
    for split, path in PUBLIC_SPLITS.items():
        if digest(path) != manifest.get("output_sha256", {}).get(split):
            raise ValueError("public v3 split SHA differs")
    if digest(OASST2) != OASST2_SHA:
        raise ValueError("pinned OASST2 source SHA differs")
    old_keys = {conversation_split_key(row)
                for path in PUBLIC_SPLITS.values() for row in load_canonical(path)}
    return manifest, old_keys


def _job(*, source_family: str, source_repo: str, source_revision: str,
         source_sha256: str, source_id: str, source_language: str,
         target_language: str, split: str, license_name: str, task: str,
         source_payload: dict | None, protected_locator: dict | None = None,
         priority_word: bool = False) -> dict:
    if source_language not in {"ko", "en"} or target_language not in {"ko", "en"}:
        raise ValueError("unknown source/target language")
    if split not in {"train", "val"}:
        raise ValueError("source split must be fixed before translation")
    if bool(source_payload) == bool(protected_locator):
        raise ValueError("exactly one public payload or protected locator is required")
    concept_id = _sha(f"{source_repo}:{source_revision}:{source_id}")
    job_id = _sha(f"{concept_id}:{target_language}:{task}")
    return {"schema": "P106B_STAGE2KW_SOURCE_JOB_V1",
            "job_id": job_id, "concept_id": concept_id,
            "parent_concept_id": concept_id,
            "source_family": source_family, "source_repo": source_repo,
            "source_revision": source_revision, "source_sha256": source_sha256,
            "source_id": source_id, "source_language": source_language,
            "target_language": target_language, "split": split,
            "source_license": license_name,
            "rights_status": "LOCAL_RIGHTS_REVIEW" if protected_locator else "CARD_ONLY",
            "teacher_task": task,
            "source_transform": ("dictionary_grounded_qa" if protected_locator else
                                 "teacher_translation" if source_language != target_language
                                 else "teacher_repair"),
            "source_payload": source_payload, "protected_locator": protected_locator,
            "priority_concept_word": priority_word,
            "original_and_translation_share_concept": True,
            "accepted_for_training": False}


def aya_jobs(manifest: dict):
    source = manifest["sources"]["aya"]
    for split, path in PUBLIC_SPLITS.items():
        for row in load_canonical(path):
            meta = row.get("meta", {})
            if meta.get("source") != "aya" or meta.get("language") != "en":
                continue
            messages = row.get("messages", [])
            if len(messages) != 2 or [m.get("role") for m in messages] != ["user", "assistant"]:
                continue
            turns = [{"user_text": plain(messages[0]),
                      "assistant_text": plain(messages[1])}]
            source_id = str(meta.get("source_id") or "")
            if not source_id:
                raise ValueError("Aya source ID absent")
            for target in ("en", "ko"):
                yield _job(source_family="aya_dataset", source_repo=source["repo"],
                           source_revision=source["revision"],
                           source_sha256=manifest["output_sha256"][split],
                           source_id=source_id, source_language="en",
                           target_language=target, split=split,
                           license_name="Apache-2.0_card",
                           task="repair" if target == "en" else "translate",
                           source_payload={"source_turns": turns})


def _reviewed(node: dict, role: str, language: str, parent: str | None = None) -> bool:
    return (isinstance(node, dict) and node.get("role") == role
            and node.get("lang") == language and node.get("review_result") is True
            and isinstance(node.get("review_count"), int) and node["review_count"] >= 1
            and not node.get("deleted") and node.get("synthetic") is False
            and isinstance(node.get("text"), str) and bool(node["text"].strip())
            and isinstance(node.get("message_id"), str)
            and (parent is None or node.get("parent_id") == parent))


def oasst2_jobs(old_keys: set[bytes], counts: Counter):
    seen: set[bytes] = set()
    with gzip.open(OASST2, "rt", encoding="utf-8") as stream:
        for tree in map(json.loads, stream):
            root = tree.get("prompt")
            language = root.get("lang") if isinstance(root, dict) else None
            if language not in ("en", "ko") or not _reviewed(root, "prompter", language):
                continue
            answers = [child for child in (root.get("replies") or [])
                       if _reviewed(child, "assistant", language, root["message_id"])]
            if not answers:
                continue
            answer = min(answers, key=lambda child: (child.get("rank") is None,
                         child["rank"] if isinstance(child.get("rank"), int) else 999,
                         child["message_id"]))
            counts[f"oasst2_{language}_reviewed_single"] += 1
            turns = [{"user_text": root["text"].strip(),
                      "assistant_text": answer["text"].strip()}]
            key = conversation_split_key(normalize({"messages": [
                {"role": "user", "content": turns[0]["user_text"]},
                {"role": "assistant", "content": turns[0]["assistant_text"]}],
                "meta": {"source": "oasst2", "source_id": str(tree.get("message_tree_id"))}}))
            if key in old_keys:
                counts[f"oasst2_{language}_overlap_public_v3"] += 1
                continue
            if key in seen:
                counts[f"oasst2_{language}_duplicate_internal"] += 1
                continue
            seen.add(key)
            source_id = str(tree.get("message_tree_id") or root["message_id"])
            concept_id = _sha(f"OpenAssistant/oasst2:{OASST2_REVISION}:{source_id}")
            split = "val" if int(_sha("p106b-v14-split:" + concept_id)[:8], 16) % 20 == 0 else "train"
            for target in ("en", "ko"):
                yield _job(source_family="oasst2", source_repo="OpenAssistant/oasst2",
                           source_revision=OASST2_REVISION, source_sha256=OASST2_SHA,
                           source_id=source_id, source_language=language,
                           target_language=target, split=split,
                           license_name="Apache-2.0_card",
                           task="repair" if target == language else "translate",
                           source_payload={"source_turns": turns})


def dictionary_refs(files: list[Path], word_priority: set[str],
                    source_shas: dict[str, str], counts: Counter):
    for path in files:
        resource = json.loads(path.read_text(encoding="utf-8"))["LexicalResource"]
        entries = resource["Lexicon"]["LexicalEntry"]
        for index, entry in enumerate(_seq(entries)):
            lemma = next((name for item in _seq(entry.get("Lemma"))
                          if isinstance(item, dict)
                          for name in [_feat(item.get("feat"), "writtenForm")]
                          if name), "")
            target_code = str(entry.get("val") or "")
            unit = _feat(entry.get("feat"), "lexicalUnit")
            if not lemma or not target_code:
                counts["dictionary_missing_lemma_or_code"] += 1
                continue
            for sense_index, sense in enumerate(_seq(entry.get("Sense"))):
                definition = _feat(sense.get("feat"), "definition")
                if not definition.strip():
                    counts["dictionary_missing_definition"] += 1
                    continue
                sense_id = str(sense.get("val") or sense_index)
                source_id = _sha(f"krdict:{path.name}:{target_code}:{unit}:{sense_id}:{index}")
                locator = {"source_namespace": "krdict/20260819",
                           "file": path.name, "entry_ordinal": index,
                           "sense_ordinal": sense_index,
                           "target_code": target_code,
                           "lexical_unit": unit,
                           "sense_id": sense_id,
                           "definition_sha256": _sha(definition),
                           "headword_sha256": _sha(lemma)}
                counts["dictionary_senses_with_definition"] += 1
                if lemma in word_priority:
                    counts["dictionary_priority_word_senses"] += 1
                split = "val" if int(_sha("p106b-v14-dict-split:" + source_id)[:8], 16) % 20 == 0 else "train"
                yield _job(source_family="krdict", source_repo=DICT_REPO,
                           source_revision="20260819", source_sha256=source_shas[path.name],
                           source_id=source_id, source_language="ko", target_language="ko",
                           split=split, license_name="CC-BY-SA-2.0-KR_site_policy_local_unverified",
                           task="grounded_qa", source_payload=None,
                           protected_locator=locator, priority_word=lemma in word_priority)
                # English is a CHILD job after an actual Korean teacher answer;
                # do not count a dictionary sense as an independent English QA.


def dictionary_english_child(parent_job: dict, korean_teacher_content: dict,
                             parent_generation_id: str) -> dict:
    """Create an English translation task, not a second independent fact source."""
    if (parent_job.get("source_family") != "krdict"
            or parent_job.get("target_language") != "ko"
            or parent_job.get("rights_status") not in {"LOCAL_RIGHTS_REVIEW", "APPROVED_PUBLIC"}
            or not parent_generation_id):
        raise ValueError("dictionary Korean QA parent/rights lineage invalid")
    question = korean_teacher_content.get("user_text")
    answer = korean_teacher_content.get("assistant_text")
    if not all(isinstance(value, str) and value.strip() for value in (question, answer)):
        raise ValueError("complete Korean teacher question/answer required")
    child = dict(parent_job)
    child.update({"job_id": _sha(parent_job["concept_id"] + ":en:teacher_translation:" + parent_generation_id),
                  "source_language": "ko", "target_language": "en",
                  "teacher_task": "translate", "source_transform": "teacher_translation",
                  "source_payload": {"source_turns": [{"user_text": question,
                                                      "assistant_text": answer}]},
                  "protected_locator": None,
                  "parent_generation_id": parent_generation_id,
                  "parent_concept_id": parent_job["parent_concept_id"],
                  "accepted_for_training": False})
    return child


def token_budget_decision(input_tokens: int | None, *, context: int,
                          max_output: int, reserve: int = 128) -> str:
    """Actual teacher tokenizer count, never a character-count proxy."""
    if input_tokens is None:
        return "TOKENIZER_NOT_RUN_HOLD"
    if min(context, max_output, reserve) < 1 or max_output + reserve >= context:
        return "INVALID_CONTEXT_CONFIG_HOLD"
    return "DIRECT" if input_tokens + max_output + reserve <= context else "COMPRESSION_REQUIRED"


def teacher_admission(port: int, key: str, job: dict, source_payload: dict,
                      *, context: int, max_output: int, effort: str) -> dict:
    """Count the *teacher* chat-template tokens before generation, not chars."""
    if effort not in {"none", "low", "medium"}:
        raise ValueError("unknown teacher reasoning effort")
    prompt = teacher_prompt(job["teacher_task"], job["target_language"], source_payload)
    formatted = _http_json(f"http://127.0.0.1:{port}/apply-template", key,
                           {"messages": prompt, "reasoning_effort": effort}, timeout=10)
    if not isinstance(formatted.get("prompt"), str):
        raise ValueError("teacher server did not return applied template")
    encoded = _http_json(f"http://127.0.0.1:{port}/tokenize", key,
                         {"content": formatted["prompt"],
                          "add_special": False, "parse_special": True}, timeout=10)
    if not isinstance(encoded.get("tokens"), list):
        raise ValueError("teacher server did not return token IDs")
    tokens = len(encoded["tokens"])
    return {"job_id": job["job_id"], "input_tokens": tokens,
            "max_output": max_output, "context": context,
            "reserve": 128,
            "decision": token_budget_decision(tokens, context=context,
                                               max_output=max_output)}


def compression_child(parent_job: dict) -> dict:
    """Compress in the SOURCE language before any bilingual translation."""
    if not isinstance(parent_job.get("source_payload"), dict):
        raise ValueError("protected locator must be resolved under rights gate before compression")
    child = dict(parent_job)
    child.update({"job_id": _sha(parent_job["job_id"] + ":compress_qa"),
                  "target_language": parent_job["source_language"],
                  "teacher_task": "compress_qa",
                  "source_transform": "teacher_source_compression",
                  "parent_job_id": parent_job["job_id"],
                  "parent_concept_id": parent_job["parent_concept_id"],
                  "accepted_for_training": False})
    return child


def translation_child_from_compression(parent_job: dict, compressed: dict,
                                       compression_generation_id: str) -> dict:
    """Re-enter the original target-language task with a versioned short source."""
    if not compression_generation_id or not all(
            isinstance(compressed.get(key), str) and compressed[key].strip()
            for key in ("user_text", "assistant_text")):
        raise ValueError("complete source-language compression and generation ID required")
    if parent_job.get("source_language") not in {"en", "ko"}:
        raise ValueError("source language missing")
    child = dict(parent_job)
    child.update({"job_id": _sha(parent_job["job_id"] + ":compressed:" + compression_generation_id),
                  "source_payload": {"source_turns": [{
                      "user_text": compressed["user_text"],
                      "assistant_text": compressed["assistant_text"]}]},
                  "protected_locator": None,
                  "parent_job_id": parent_job["job_id"],
                  "compression_generation_id": compression_generation_id,
                  "parent_concept_id": parent_job["parent_concept_id"],
                  "source_transform": "translation_after_source_compression"
                  if parent_job["target_language"] != parent_job["source_language"]
                  else "repair_after_source_compression",
                  "accepted_for_training": False})
    return child


def compression_literal_screen(source: dict, candidate: dict,
                               required_literals: list[str] = ()) -> list[str]:
    """Conservative screen only; never a semantic-faithfulness PASS."""
    old = json.dumps(source, ensure_ascii=False)
    new = str(candidate.get("user_text") or "") + " " + str(candidate.get("assistant_text") or "")
    numbers = set(re.findall(r"\d+(?:[.,]\d+)*", old))
    missing = [f"NUMBER:{number}" for number in sorted(numbers) if number not in new]
    missing.extend(f"LITERAL:{literal}" for literal in required_literals
                   if isinstance(literal, str) and literal and literal not in new)
    negation = re.search(r"\b(?:not|never|without|no)\b|않|없|아니|금지", old, re.I)
    if negation and not re.search(r"\b(?:not|never|without|no)\b|않|없|아니|금지", new, re.I):
        missing.append("NEGATION_POSSIBLY_DROPPED")
    return missing


def wrap_teacher_answer(job: dict, parsed: dict, generation_id: str,
                        *, reasoning_ref: str = "", reasoning_sha256: str = "") -> dict:
    """Manager-owned canonical row; raw teacher output stays in a sidecar."""
    content = parsed.get("parsed_content")
    if parsed.get("format_status") != "TAGGED_COMPLETE" or not isinstance(content, dict):
        raise ValueError("teacher final tagged content not complete")
    return wrap_turns([{"user_text": content["user_text"],
                        "assistant_text": content["assistant_text"]}],
                      source_id=job["source_id"], source_sha256=job["source_sha256"],
                      teacher_model_sha256=parsed["teacher_model_sha256"],
                      language=job["target_language"],
                      source_license=job["source_license"],
                      generation_id=generation_id,
                      correction_note=content.get("correction_note", ""),
                      reasoning_ref=reasoning_ref,
                      reasoning_sha256=reasoning_sha256,
                      source_repo=job["source_repo"],
                      source_revision=job["source_revision"],
                      source_object_id=job["source_id"],
                      source_transform=job["source_transform"],
                      parent_concept_id=job["parent_concept_id"],
                      source_rights_status=job["rights_status"])


def _attested(protected: dict) -> bool:
    if APPROVAL.is_symlink() or not APPROVAL.is_file():
        return False
    value = json.loads(APPROVAL.read_text(encoding="utf-8"))
    return (value.get("status") == "APPROVED_FOR_LOCAL_TEACHER_DERIVATION"
            and isinstance(value.get("approval_ref"), str)
            and len(value["approval_ref"].strip()) >= 8
            and value.get("source_sha256") == protected)


def census(*, write: bool) -> dict:
    if write and (OUTPUT_DIR.exists() or OUTPUT_DIR.is_symlink()):
        raise FileExistsError("multisource v1 output already exists; use a new stage")
    public, old_keys = public_inventory()
    files, words, protected, word_priority = protected_inventory()
    if write and not _attested(protected):
        raise PermissionError("exact protected-source rights/derivative-use attestation absent")
    counts: Counter[str] = Counter()
    IDs: set[str] = set()
    writers = ({"public": ShardWriter(OUTPUT_DIR, "public_jobs"),
                "dictionary": ShardWriter(OUTPUT_DIR, "dictionary_refs")} if write else {})
    sources = (("public", aya_jobs(public)),
               ("public", oasst2_jobs(old_keys, counts)),
               ("dictionary", dictionary_refs(files, word_priority,
                                               protected["dictionary"], counts)))
    for category, source in sources:
        for job in source:
            if job["job_id"] in IDs:
                raise ValueError("duplicate source/target job ID")
            IDs.add(job["job_id"])
            counts[f"{job['source_family']}:{job['target_language']}:{job['split']}"] += 1
            if write:
                writers[category].append(job)
    result = {"schema": "P106B_STAGE2KW_MULTISOURCE_DECK_V1",
              "jobs": len(IDs), "counts": dict(sorted(counts.items())),
              "public_v3_manifest_sha256": digest(PUBLIC_MANIFEST),
              "public_repos": {key: {"repo": value["repo"], "revision": value["revision"]}
                               for key, value in public["sources"].items()},
              "oasst2": {"repo": "OpenAssistant/oasst2", "revision": OASST2_REVISION,
                         "source_sha256": OASST2_SHA},
              "protected_source": protected,
              "protected_source_manifest_sha256": _sha(json.dumps(
                  protected, ensure_ascii=False, sort_keys=True)),
              "dictionary_english_child_status": "WAIT_KOREAN_TEACHER_QA_AND_LINEAGE",
              "rights_gate": "ATTESTED" if _attested(protected) else "HOLD",
              "length_policy": "No 1200-character cutoff: teacher server exact chat-template token budget checked before generation; overlong source gets separate compression child job, never silent truncation",
              "split_policy": "Aya original v3 split; OASST2/krdict concept-hash split before translation; all derived language variants retain parent_concept_id",
              "status": "JOBS_ONLY_NOT_TEACHER_ANSWERS_OR_TRAIN_READY"}
    if write:
        result["shards"] = {}
        for category, writer in writers.items():
            manifest = writer.close(lineage={"source_family": category,
                                            "public_manifest_sha256": result["public_v3_manifest_sha256"]})
            verify(OUTPUT_DIR, manifest)
            result["shards"][category] = {"manifest": writer.manifest_path.relative_to(ROOT).as_posix(),
                                           "rows": manifest["rows"],
                                           "concat_sha256": manifest["concat_sha256"]}
        with (OUTPUT_DIR / "source_deck_manifest.json").open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def self_test() -> None:
    source = _job(source_family="oasst2", source_repo="OpenAssistant/oasst2",
                  source_revision="rev", source_sha256="A" * 64, source_id="tree1",
                  source_language="en", target_language="ko", split="train",
                  license_name="Apache-2.0_card", task="translate",
                  source_payload={"source_turns": [{"user_text": "hello", "assistant_text": "hi"}]})
    twin = _job(source_family="oasst2", source_repo="OpenAssistant/oasst2",
                source_revision="rev", source_sha256="A" * 64, source_id="tree1",
                source_language="en", target_language="en", split="train",
                license_name="Apache-2.0_card", task="repair",
                source_payload={"source_turns": [{"user_text": "hello", "assistant_text": "hi"}]})
    assert source["parent_concept_id"] == twin["parent_concept_id"]
    assert source["job_id"] != twin["job_id"]
    assert source["accepted_for_training"] is False
    korean = _job(source_family="krdict", source_repo=DICT_REPO,
                  source_revision="20260819", source_sha256="B" * 64,
                  source_id="C" * 64, source_language="ko", target_language="ko",
                  split="train", license_name="CC-BY-SA-2.0-KR_site_policy_local_unverified",
                  task="grounded_qa", source_payload=None,
                  protected_locator={"file": "1_5000_20260819.json", "entry_ordinal": 1})
    english = dictionary_english_child(korean, {"user_text": "나무는?",
                                                 "assistant_text": "식물입니다."}, "teacher:g1")
    assert english["concept_id"] == korean["concept_id"]
    assert english["rights_status"] == korean["rights_status"]
    assert english["target_language"] == "en" and english["parent_generation_id"] == "teacher:g1"
    assert token_budget_decision(817, context=6144, max_output=4096) == "DIRECT"
    assert token_budget_decision(1200, context=3072, max_output=2048) == "COMPRESSION_REQUIRED"
    fixture = _job(source_family="fixture", source_repo="test/source", source_revision="r1",
                  source_sha256="A" * 64, source_id="1", source_language="en",
                  target_language="ko", split="train", license_name="TEST",
                  task="translate", source_payload={"source_turns": [{
                      "user_text": "What is 1,200 meters?", "assistant_text": "1.2 km."}]})
    short_request = compression_child(fixture)
    assert short_request["source_language"] == short_request["target_language"] == "en"
    translated = translation_child_from_compression(fixture, {
        "user_text": "What is 1,200 m?", "assistant_text": "1.2 km."}, "gen-1")
    assert translated["target_language"] == "ko" and translated["parent_job_id"] == fixture["job_id"]
    assert translated["parent_concept_id"] == fixture["parent_concept_id"]
    assert "NUMBER:1,200" not in compression_literal_screen(
        {"question": "What is 1,200 meters?"}, translated["source_payload"]["source_turns"][0])
    compressed = compression_child(source)
    assert compressed["parent_concept_id"] == source["parent_concept_id"]
    assert compressed["source_transform"] == "teacher_source_compression"
    assert compression_literal_screen({"q": "2+2"}, {"user_text": "2+2?", "assistant_text": "4"}) == []
    assert compression_literal_screen({"q": "2+2"}, {"user_text": "셈?", "assistant_text": "4"})
    assert "NEGATION_POSSIBLY_DROPPED" in compression_literal_screen(
        {"q": "Do not guess"}, {"user_text": "Guess?", "assistant_text": "Maybe"})
    wrapped = wrap_teacher_answer(source, {"format_status": "TAGGED_COMPLETE",
                                           "teacher_model_sha256": "D" * 64,
                                           "parsed_content": {"user_text": "질문은?",
                                                              "assistant_text": "답입니다.",
                                                              "correction_note": ""}}, "g1")
    assert wrapped["meta"]["source_repo"] == "OpenAssistant/oasst2"
    assert wrapped["meta"]["parent_concept_id"] == source["concept_id"]
    assert wrapped["meta"]["student_training"] == "NOT_RUN"
    assert not _attested({"dictionary": {}, "concept_word_files": {}, "vocabulary_txt": {}})
    print("[PASS] source/revision/sense lineage, split-before-translation, protected rights hold; source/model NOT_RUN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            self_test()
        else:
            report = census(write=args.execute)
            print(json.dumps({key: report[key] for key in (
                "schema", "jobs", "counts", "public_repos", "oasst2",
                "protected_source_manifest_sha256", "dictionary_english_child_status",
                "rights_gate", "status")}, ensure_ascii=False, sort_keys=True))
            print("[PASS] versioned source jobs only, teacher/student NOT_RUN" if args.execute
                  else "[CHECK_ONLY] exact named source census; no data copied or model run")
        return 0
    except PermissionError as exc:
        print(f"[HOLD] P106B Stage2kW {exc}; protected source not copied")
        return 8
    except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
        print(f"[FAIL] P106B Stage2kW {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())
