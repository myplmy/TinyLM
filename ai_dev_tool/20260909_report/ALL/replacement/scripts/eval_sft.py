"""A05 자동 생성 평가. 학생의 정답은 prompt에 넣지 않는다."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tinylm.chat.canonical import normalize, validate
from tinylm.chat.serialize import serialize, SPECS
from tinylm.eval.audit_io import read_records, sha256_file, digest_json, write_json_new
from tinylm.eval.model_adapter import load_local_model, greedy_completion
from tinylm.eval.sft_grading import grade_response


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", required=True)
    ap.add_argument("--checkpoint")
    ap.add_argument("--tokenizer")
    ap.add_argument("--grading-overrides", help="JSON id -> {source_item_sha256, grading}; 검수한 별도 규칙")
    ap.add_argument("--reference-only", action="store_true",
                    help="모델 없이 정본 assistant 답이 자기 grading 계약을 만족하는지 검사")
    ap.add_argument("--serializer", choices=tuple(SPECS), default="chatml")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--seq-max", type=int, default=1024)
    ap.add_argument("--max-new", type=int, default=128)
    ap.add_argument("--out-jsonl", required=True)
    a = ap.parse_args()
    if not a.reference_only and (not a.checkpoint or not a.tokenizer):
        ap.error("--checkpoint/--tokenizer 필요")
    rows = read_records(a.eval)
    overrides = (json.loads(Path(a.grading_overrides).read_text(encoding="utf-8"))
                 if a.grading_overrides else {})
    if not isinstance(overrides, dict):
        raise ValueError("grading-overrides는 ID 사전")
    known_ids = {str(r.get("meta", {}).get("id") or r.get("id") or i)
                 for i, r in enumerate(rows)}
    if set(overrides) - known_ids:
        raise ValueError("현재 평가에 없는 override ID")
    override_sha = sha256_file(a.grading_overrides) if a.grading_overrides else None
    out = Path(a.out_jsonl)
    if out.exists() or out.with_suffix(".summary.json").exists():
        ap.error("새 출력 경로 필요")
    model = tok = provenance = None
    if not a.reference_only:
        model, tok, provenance = load_local_model("sft", checkpoint=a.checkpoint,
                                                  tokenizer_path=a.tokenizer, device=a.device)
    out.parent.mkdir(parents=True, exist_ok=True)
    scored, hits, skipped, diagnostic, truncated = 0, 0, 0, 0, 0
    seen = set()
    dataset_sha = sha256_file(a.eval)
    with out.open("x", encoding="utf-8", newline="\n") as f:
        for i, raw in enumerate(rows):
            conv = validate(normalize(raw))
            if not conv["messages"] or conv["messages"][-1]["role"] != "assistant":
                raise ValueError("평가 샘플은 reference assistant 답으로 끝나야 함")
            ident = str(raw.get("meta", {}).get("id") or raw.get("id") or i)
            if ident in seen:
                raise ValueError("중복 평가 id")
            seen.add(ident)
            reference = conv["messages"][-1]
            if a.reference_only:
                text = "".join(b.get("text", "") for b in reference["content"] if b["type"] == "text")
                generation = {"status": "ok", "text": text, "finish": "reference", "truncated": False}
            else:
                prompt_conv = dict(conv, messages=conv["messages"][:-1])
                prompt = serialize(prompt_conv, a.serializer, add_generation_prompt=True)
                generation = greedy_completion(
                    model, tok, prompt, device=a.device,
                    seq_max=min(a.seq_max, provenance["max_seq_len"]), max_new=a.max_new,
                    stop_strings=(SPECS[a.serializer]["end"],))
            graded_record = raw
            if ident in overrides:
                patch = overrides[ident]
                if patch.get("source_item_sha256") != digest_json(raw):
                    raise ValueError(f"{ident}: override 원본 문항 SHA 불일치")
                if not isinstance(patch.get("grading"), dict):
                    raise ValueError("override grading 사전 필요")
                graded_record = dict(raw, meta=dict(raw.get("meta", {}), grading=patch["grading"]))
            grade = grade_response(graded_record, generation["text"])
            eligible = grade.get("ranking_eligible", False)
            if generation["status"] != "ok" or grade["status"] != "scored":
                skipped += 1
            elif eligible:
                scored += 1
                hits += grade["correct"]
            else:
                diagnostic += 1
            truncated += bool(generation.get("truncated"))
            rec = {"id": ident, "model": "reference" if a.reference_only else "sft",
                   "task": "fresh_sft", "dataset_sha256": dataset_sha,
                   "item_sha256": digest_json(graded_record),
                   "source_item_sha256": digest_json(raw), "grading_overrides_sha256": override_sha, "family": raw.get("meta", {}).get("source_family"),
                   "status": "ok" if generation["status"] == "ok" and grade["status"] == "scored" else "skipped",
                   "correct": grade.get("correct") if eligible else None,
                   "gold": graded_record.get("meta", {}).get("grading", {}).get("accepted_answers"),
                   "generation": generation, "grade": grade, "model_provenance": provenance,
                   "scoring_profile": "fresh.metadata_lexical_format.v1"}
            f.write(json.dumps(rec, ensure_ascii=False, allow_nan=False) + "\n")
            f.flush()
    result = {"asked": len(rows), "ranking_scored": scored, "ranking_correct": hits,
              "ranking_score": hits / scored if scored else None, "skipped": skipped,
              "diagnostic_only": diagnostic, "truncated": truncated,
              "reference_only": a.reference_only, "dataset_sha256": dataset_sha,
              "grading_overrides_sha256": override_sha,
              "records_sha256": sha256_file(out),
              "scope": "metadata lexical grade; semantic contradictions outside explicit rules can escape"}
    write_json_new(out.with_suffix(".summary.json"), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if scored and (not a.reference_only or (hits == scored and skipped == 0)) else 2


if __name__ == "__main__":
    raise SystemExit(main())
