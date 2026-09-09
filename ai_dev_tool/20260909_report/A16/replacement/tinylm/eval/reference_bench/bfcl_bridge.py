"""Official BFCL v3 runner with a TinyLM model handler; never a JSON-validity scorer."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from .artifacts import (digest, fresh_dir, json_write, jsonl_write, read_jsonl,
                        sha256_file, source_tree, versions)
from .harness_run import model_arguments, make_engine


def fetch_identity(port):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/a16/identity", timeout=5) as response:
        return json.load(response)


def inventory(root):
    root = Path(root).resolve(strict=True)
    package = root / "bfcl_eval"
    if not (package / "model_handler/local_inference/base_oss_handler.py").is_file():
        raise ValueError("--upstream must be the official berkeley-function-call-leaderboard directory.")
    return source_tree(package)


def official_rows(path):
    """The BFCL release stores JSON objects one per line in .json files."""
    rows = read_jsonl(path)
    if not rows or any(not isinstance(r.get("id"), str) for r in rows):
        raise ValueError(f"Invalid BFCL task data: {path}")
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError(f"Duplicate official IDs: {path}")
    return rows


def register_model():
    from bfcl_eval.model_handler.local_inference.base_oss_handler import OSSHandler
    from bfcl_eval.constants.model_config import MODEL_CONFIG_MAPPING, ModelConfig
    from overrides import override

    class TinyLMHandler(OSSHandler):
        @override
        def _format_prompt(self, messages, function):
            # Official pre-processing already puts complete tool schemas into the system message.
            # Base TinyLM has no declared chat template. Record this explicit prompt-model format.
            chunks = []
            for message in messages:
                content = message.get("content", "")
                if not isinstance(content, str):
                    raise ValueError("Expected official textual prompting messages.")
                header = message["role"].capitalize()
                if message.get("name"):
                    header += " (" + str(message["name"]) + ")"
                chunks.append(header + ":\n" + content)
            return "\n\n".join(chunks) + "\n\nAssistant:\n"

    if "A16-TinyLM" in MODEL_CONFIG_MAPPING:
        raise ValueError("A16 model name is already registered.")
    MODEL_CONFIG_MAPPING["A16-TinyLM"] = ModelConfig(
        model_name="A16-TinyLM", display_name="A16 TinyLM (Prompt)",
        url="https://github.com/ShishirPatil/gorilla", org="Local research",
        license="Local checkpoint; no publication implied", model_handler=TinyLMHandler,
        input_price=None, output_price=None, is_fc_model=False, underscore_to_dot=False)
    return TinyLMHandler


def category_files(upstream, categories):
    from bfcl_eval.constants.category_mapping import TEST_COLLECTION_MAPPING
    leaves = []
    for category in categories:
        leaves.extend(TEST_COLLECTION_MAPPING.get(category, [category]))
    leaves = list(dict.fromkeys(leaves))
    result = {}
    for leaf in leaves:
        if not re.fullmatch(r"[a-z0-9_]+", leaf):
            raise ValueError(f"Unknown BFCL category shape: {leaf}")
        candidates = list((upstream / "bfcl_eval/data").glob(f"BFCL_v3_{leaf}.json"))
        if len(candidates) != 1:
            raise ValueError(f"Cannot resolve exact v3 data file for {leaf}.")
        result[leaf] = candidates[0]
    return result


def coverage(result_root, files):
    expected = {row["id"] for path in files.values() for row in official_rows(path)}
    found, duplicates = set(), set()
    for path in Path(result_root).rglob("*.json"):
        if path.name.endswith("_result.json"):
            for row in read_jsonl(path):
                if row["id"] in found:
                    duplicates.add(row["id"])
                found.add(row["id"])
    missing, extra = expected - found, found - expected
    return {"expected": len(expected), "found": len(found), "missing": sorted(missing),
            "extra": sorted(extra), "duplicates": sorted(duplicates),
            "complete": bool(expected) and not (missing or extra or duplicates)}


def call_cli(arguments):
    from bfcl_eval.__main__ import cli
    try:
        cli(args=arguments, standalone_mode=False)
    except SystemExit as error:
        if error.code not in (0, None):
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    lock = sub.add_parser("freeze")
    lock.add_argument("--upstream", type=Path, required=True)
    lock.add_argument("--release-label", required=True,
                      help="Use the reviewed Gorilla v1.3/BFCL v3 checkout, not current main.")
    lock.add_argument("--output", type=Path, required=True)
    for command in ("generate", "evaluate", "legacy-export"):
        item = sub.add_parser(command)
        item.add_argument("--lock", type=Path, required=True)
        item.add_argument("--upstream", type=Path, required=True)
        item.add_argument("--output", type=Path, required=True)
        if command != "evaluate":
            item.add_argument("--categories", nargs="+", required=True)
        if command == "generate":
            item.add_argument("--server-run", type=Path, required=True)
            item.add_argument("--temperature", type=float, default=0.001)
            item.add_argument("--execute-simulated-tools", action="store_true", required=True,
                              help="Official multi-turn generation may invoke benchmark tool simulators.")
        elif command == "evaluate":
            item.add_argument("--run", type=Path, required=True)
            item.add_argument("--execute-official-evaluation", action="store_true", required=True)
        else:
            model_arguments(item)
            item.add_argument("--cache", type=Path, required=True)
            item.add_argument("--legacy-max-new", type=int, default=96)
            item.add_argument("--legacy-seq-max", type=int, default=1024)
    args = parser.parse_args(argv)
    upstream = args.upstream.resolve(strict=True)
    current = inventory(upstream)
    if args.command == "freeze":
        out = fresh_dir(args.output)
        json_write(out / "source_lock.json", {
            "schema": 1, "upstream": str(upstream), "source": current,
            "release_label": args.release_label,
            "provenance_status": "user-reviewed release identity; source hash freezes content",
            "expected_protocol": "BFCL v3; select official Gorilla v1.3 snapshot"})
        return
    lock_data = json.loads(args.lock.read_text(encoding="utf-8"))
    if lock_data["source"]["sha256"] != current["sha256"]:
        raise ValueError("BFCL code/data changed since freeze.")
    out = fresh_dir(args.output)
    # Import only after pinning output location. No edits to upstream registry/source files.
    os.environ["BFCL_PROJECT_ROOT"] = str(out)
    sys.path.insert(0, str(upstream))
    import bfcl_eval
    if not Path(bfcl_eval.__file__).resolve().is_relative_to(upstream):
        raise ValueError("Imported BFCL package is not the reviewed checkout.")
    register_model()
    if args.command == "evaluate":
        run = args.run.resolve(strict=True)
        meta = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        if not (run / "completion.json").exists():
            raise ValueError("Generation run is incomplete.")
        if meta["source_sha256"] != current["sha256"]:
            raise ValueError("Generation/scoring BFCL versions differ.")
        if source_tree(run / "result")["sha256"] != meta["result_sha256"]:
            raise ValueError("Generation results changed.")
        categories = meta["categories"]
    else:
        categories = args.categories
    files = category_files(upstream, categories)
    manifest = {"source_sha256": current["sha256"], "release_label": lock_data["release_label"],
                "categories": categories, "official_data": {k: sha256_file(v) for k, v in files.items()},
                "protocol": "official BFCL Prompt-mode pipeline",
                "scope": "selected categories only; do not publish partial overall as full BFCL v3",
                "packages": versions("bfcl", "bfcl-eval", "openai", "transformers"),
                "handler": "plain role headers; official full function prompt + official parsers/scorers"}
    try:
        if args.command == "generate":
            server = json.loads((args.server_run / "server.json").read_text(encoding="utf-8"))
            before = fetch_identity(server["port"])
            if before["identity_digest"] != server["identity_digest"]:
                raise ValueError("Live server differs from recorded checkpoint/tokenizer.")
            os.environ["LOCAL_SERVER_ENDPOINT"] = "127.0.0.1"
            os.environ["LOCAL_SERVER_PORT"] = str(server["port"])
            os.environ["REMOTE_OPENAI_BASE_URL"] = server["endpoint"]
            os.environ["REMOTE_OPENAI_API_KEY"] = "EMPTY"
            os.environ.pop("REMOTE_OPENAI_TOKENIZER_PATH", None)
            manifest["server"] = server
            manifest["temperature"] = args.temperature
            call_cli(["generate", "--model", "A16-TinyLM", "--test-category", ",".join(categories),
                      "--temperature", str(args.temperature), "--num-threads", "1",
                      "--skip-server-setup", "--local-model-path", server["tokenizer_metadata"],
                      "--result-dir", str(out / "result"), "--include-input-log"])
            after = fetch_identity(server["port"])
            if after["counters"]["failed_requests"] != before["counters"]["failed_requests"]:
                raise RuntimeError("Transport/context failures occurred. This is an incomplete run, not score 0.")
            manifest["transport_before"] = before["counters"]
            manifest["transport_after"] = after["counters"]
            manifest["engine_stats_after"] = after["engine_stats"]
        elif args.command == "legacy-export":
            from .legacy_compare import frozen_module
            old = frozen_module("eval_bench_suite.py")
            cached = {}
            for row in read_jsonl(args.cache):
                if row["id"] in cached:
                    raise ValueError("Duplicate legacy BFCL cache ID.")
                cached[row["id"]] = row
            engine = make_engine(args)
            if args.legacy_seq_max > engine.cfg.max_seq_len:
                raise ValueError("Legacy sequence limit exceeds checkpoint maximum.")
            target = out / "result" / "A16-TinyLM"
            target.mkdir(parents=True)
            details = []
            for category, file in files.items():
                if "multi_turn" in category:
                    raise ValueError("Legacy code has no multi-turn protocol. Use single-turn categories only.")
                responses = []
                for row in official_rows(file):
                    legacy = cached.get(row["id"])
                    if legacy is None or any(legacy.get(k) != row.get(k) for k in ("question", "function")):
                        raise ValueError(f"{row['id']}: cache/source mismatch; no positional substitution.")
                    item = old.ADAPTERS["bfcl_v3"](legacy)
                    text = old.greedy(engine.model, engine.tokenizer, engine.device.type,
                                      item["ctx"], args.legacy_max_new, args.legacy_seq_max,
                                      engine.torch, stop=["\ndef ", "\nclass ", "\n#", "\n\n\n"])
                    responses.append({"id": row["id"], "result": text})
                    try:
                        json.loads(text.strip())
                        valid = True
                    except (ValueError, TypeError):
                        valid = False
                    details.append({"id": row["id"], "legacy_json_valid": valid})
                jsonl_write(target / f"BFCL_v3_{category}_result.json", responses)
            jsonl_write(out / "legacy_diagnostic.jsonl", details)
            manifest.update(model=engine.identity, legacy_max_new=args.legacy_max_new,
                            legacy_seq_max=args.legacy_seq_max,
                            legacy_cache_sha256=sha256_file(args.cache),
                            protocol="frozen legacy generation; official BFCL result schema/IDs restored")
        else:
            manifest["generation_run"] = str(run)
            call_cli(["evaluate", "--model", "A16-TinyLM", "--test-category", ",".join(categories),
                      "--result-dir", str(run / "result"), "--score-dir", str(out / "score")])
            score_files = list((out / "score").rglob("*.csv")) + list((out / "score").rglob("*.json"))
            if not score_files:
                raise RuntimeError("Official BFCL evaluator produced no score artifacts.")
        if args.command != "evaluate":
            check = coverage(out / "result", files)
            json_write(out / "coverage.json", check)
            if not check["complete"]:
                raise RuntimeError("Official task IDs are missing, duplicated, or unexpected.")
            manifest["result_sha256"] = source_tree(out / "result")["sha256"]
        json_write(out / "manifest.json", manifest)
        json_write(out / "completion.json", {"status": "completed", "stage": args.command})
    except BaseException as error:
        json_write(out / "failure.json", {"type": type(error).__name__, "message": str(error),
                                        "manifest": manifest})
        raise
