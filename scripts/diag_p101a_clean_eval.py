#!/usr/bin/env python3
"""First-answer readback for the new explicit-context MTP and verified trace arms.

No training, feedback, reranking, answer repair or checkpoint writes. Code-owned
TEST scoring is distinct from annotation string match on the MTP DEV corpus.
The complete question/reference/output is exported as readable review text.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
SCHEMA = "P101A_CLEAN_FIRST_ANSWER_EVAL_V1"


def score(row, answer, extraction_ok=True):
    meta = row["meta"]
    if not extraction_ok:
        return dict(primary_correct=False, extraction_ok=False, reason="prompt_prefix_not_recovered")
    if "task" in meta and meta.get("source") == "CODE_OWNED_PROCEDURAL":
        from scripts.p106b_verified_trace_data import score_response
        result = score_response(meta["task"], answer, meta["language"], meta["policy"])
        return dict(result, primary_correct=result["final_correct"], extraction_ok=True,
                    primary="CODE_CHECKED_FINAL_VALUE_NOT_TRACE_FORMAT")
    expected = row["messages"][-1]["content"]
    if not isinstance(expected, str):
        expected = "".join(block["text"] for block in expected)
    return dict(primary_correct=answer.strip() == expected.strip(), extraction_ok=True,
                primary="ANNOTATION_EXACT_MATCH_NOT_SEMANTIC_TRUTH", reason=None,
                semantic_truth="NOT_REVIEWED")


def prompt_messages(row):
    messages = row["messages"][:-1]
    if not messages or messages[-1]["role"] != "user":
        raise ValueError("final assistant target after a user prompt is required")
    return messages


def readable_case(index, row, answer, grading, generation):
    def text(body):
        return body if isinstance(body, str) else "".join(b["text"] for b in body)
    lines = [f"## 문항 {index + 1}", "", "### 입력 대화", ""]
    for message in prompt_messages(row):
        lines.extend([f"[{message['role']}]", text(message["content"]), ""])
    lines.extend(["### 자료의 기준 답", "", text(row["messages"][-1]["content"]), "",
                  "### 모델의 첫 실제 답 (재시도 없음)", "", answer or "[빈 답]", "",
                  "### 자동 판독 범위", "",
                  f"종료: {generation['finish_reason']} / 생성 토큰: {generation['generated_tokens']}",
                  f"주지표: {grading.get('primary', '입력 복구 실패')} / 일치: {grading['primary_correct']}",
                  "내용 의미 검수: 미완료. 자동 일치와 일반 지능은 별개입니다.", ""])
    return "\n".join(lines)


def prerequisites(family, arm):
    from scripts import diag_p101a_clean_bilingual as course
    from scripts import diag_p101a_sft_mtp as engine
    corpus, evidence = engine.paths(course.TAGS[family])
    report = engine.corpus_report(corpus)
    if (report.get("preparation_schema") != course.VERSION
            or report.get("code_sha256", {}).get("scripts/diag_p101a_clean_bilingual.py") != course.digest(course.__file__)):
        raise ValueError("current frozen course controller is required")
    split = "val" if family == "mtp" else "test"
    output = evidence / ("first_answer_" + arm)
    if output.exists() or output.is_symlink():
        raise FileExistsError("preserve previous evaluation; use a new stage/version")
    if arm == "parent_baseline":
        checkpoint, checkpoint_sha = engine.PARENT, engine.PARENT_SHA
        trained_report_sha = None
    else:
        trained_path = engine.report_path(evidence, arm)
        trained = json.loads(trained_path.read_text(encoding="utf-8"))
        if (trained.get("status") != "SFT_MTP_TRAINED_EVAL_PENDING"
                or not trained.get("checkpoint_saved")
                or trained.get("corpus_sha256") != course.digest(corpus / "report.json")
                or trained.get("preparation_schema") != course.VERSION):
            raise FileNotFoundError("completed same-course trained arm is required")
        checkpoint, checkpoint_sha = engine.checkpoint(course.TAGS[family], arm), trained["checkpoint_sha256"]
        trained_report_sha = course.digest(trained_path)
    if course.digest(checkpoint) != checkpoint_sha:
        raise ValueError("saved checkpoint identity differs")
    if course.digest(engine.data.TOKENIZER) != engine.data.TOK_SHA:
        raise ValueError("tokenizer identity differs")
    return corpus, report, split, checkpoint, output, dict(schema=SCHEMA, family=family, arm=arm,
        corpus_sha256=course.digest(corpus / "report.json"), checkpoint_sha256=checkpoint_sha,
        trained_report_sha256=trained_report_sha, tokenizer_sha256=engine.data.TOK_SHA,
        source_sha256={p: course.digest(ROOT / p) for p in (
            "scripts/diag_p101a_clean_eval.py", "scripts/test_p101a_clean_eval.py",
            "scripts/p106b_verified_trace_data.py", "tinylm/infer/generate.py")},
        split=split, expected_rows=report["manifests"][split]["rows"],
        precision="FP32_MATH_TF32_OFF", cache=True, mtp_inference=False,
        temperature=0, top_k=1, max_new=128, retries=0, learning_updates=0,
        test_independence="DEV_USED_BY_TRAINING_VALIDATION" if split == "val" else "ROOT_DISJOINT_CODE_TEST",
        semantic_quality="NOT_FULLY_REVIEWED")


def execute(args):
    corpus, course_report, split, checkpoint, output, info = prerequisites(args.family, args.arm)
    from scripts.p101a_sft_mtp_data import stream_rows
    from scripts.p106b_shards import ShardWriter, verify
    from scripts import diag_p101a_sft_mtp as engine
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    from scripts.diag_p101a_mtp_parity import PrecisionForward
    from tinylm.chat.serialize import serialize
    from tinylm.infer.generate import load_model, sample
    from tokenizers import Tokenizer
    import torch
    idle_before_gpu(); began = time.perf_counter()
    target_review = ROOT / "review_request" / ("20261021_" + args.family + "_" + args.arm + "_실제첫답.md")
    if target_review.exists(): raise FileExistsError("readable review already exists")
    output.mkdir(parents=True, exist_ok=False)
    writer = ShardWriter(output, "first_answers", limit=19_999_999)
    counts = Counter(); groups = {}; texts = []; status = "EXECUTION_ERROR"; rc = 9
    try:
        with wall_limit(args.max_wall_sec), torch.no_grad():
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
            base, cfg, _ = load_model(ckpt_path=checkpoint, device="cuda", mtp_heads="off")
            model = PrecisionForward(base, "fp32_math")
            tok = Tokenizer.from_file(str(engine.data.TOKENIZER))
            for i, row in enumerate(stream_rows(corpus, course_report["manifests"][split])):
                prompt = serialize({"messages": prompt_messages(row)}, "chatml", add_generation_prompt=True)
                prefix = tok.decode(tok.encode(prompt).ids)
                decoded, generation = sample(model, cfg, tok, prompt, max_new=128, temperature=0,
                    top_k=1, use_cache=True, device="cuda", logits_last_only=True, return_metadata=True,
                    stop_token_sequences=[tok.encode("<|im_end|>").ids], mtp_tokens=1)
                extraction_ok = decoded.startswith(prefix)
                answer = decoded[len(prefix):].split("<|im_end|>", 1)[0] if extraction_ok else ""
                grading = score(row, answer, extraction_ok)
                key = row["meta"].get("family", "natural_qa") + ":" + row["meta"].get("language", "UNKNOWN")
                group = groups.setdefault(key, Counter())
                for counter in (counts, group):
                    counter.update(total=1, primary_correct=int(grading["primary_correct"]),
                                   extraction_failed=int(not extraction_ok),
                                   ended=int(generation["finish_reason"] in ("STOP_SEQUENCE", "EOS")))
                writer.append(dict(index=i, source=row, answer=answer, raw_full_text=decoded,
                    generation=generation, grading=grading))
                texts.append(readable_case(i, row, answer, grading, generation))
                if (i + 1) % 64 == 0:
                    print("[FIRST_ANSWER_PROGRESS] " + json.dumps(dict(counts), ensure_ascii=False), flush=True)
            if counts["total"] != info["expected_rows"]: raise ValueError("incomplete evaluation count")
            status, rc = "FIRST_ANSWER_COLLECTION_COMPLETE", 0
    except BaseException as exc:
        info.update(error_type=type(exc).__name__, error=str(exc)[:1500])
        rc = 130 if isinstance(exc, KeyboardInterrupt) else 9
    finally:
        manifest = writer.close(lineage=info) if writer._total_rows else None
        if manifest: verify(output, manifest)
        body = "# 실제 질문·답 원문 검수 요청\n\n자동 점수는 아래 명시된 좁은 기준만 뜻합니다.\n\n" + "\n".join(texts)
        if len(body.encode("utf-8")) >= 20_000_000: raise ValueError("review must be split before20MB")
        target_review.parent.mkdir(parents=True, exist_ok=True)
        with target_review.open("x", encoding="utf-8") as stream: stream.write(body)
        result = dict(info, status=status, returncode=rc, counts=dict(counts),
            groups={k: dict(v) for k, v in groups.items()}, raw_manifest=manifest,
            whole_sec=time.perf_counter() - began, readable_review=str(target_review.relative_to(ROOT)),
            first_answer_only=True, checkpoint_writes=0, training_feedback=0,
            general_intelligence="NOT_ESTABLISHED")
        engine.write(output / "report.json", result)
    print("[FIRST_ANSWER_FINAL] " + json.dumps(dict(status=status, returncode=rc, counts=dict(counts))), flush=True)
    return rc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", choices=("mtp", "direct", "trace"), required=True)
    parser.add_argument("--arm", choices=("parent_baseline", "scratch_ntp", "scratch_mtp", "parent_ntp", "parent_mtp"), required=True)
    parser.add_argument("--max-wall-sec", type=int, default=1800)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--execute", action="store_true"); group.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if not 60 <= args.max_wall_sec <= 21600: parser.error("window60..21600 required")
    if args.family != "mtp" and args.arm not in ("parent_baseline", "parent_ntp"):
        parser.error("direct/trace use the same parent and NTP-only arms")
    if args.check_only:
        print(json.dumps(dict(schema=SCHEMA, model_loading=False, source_loading=False,
            official_eval_correction=False, student_training=False, family=args.family, arm=args.arm)))
        return 0
    return execute(args)


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (FileNotFoundError, FileExistsError) as exc:
        print("[HOLD] " + str(exc)); raise SystemExit(8)
