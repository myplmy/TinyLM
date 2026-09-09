#!/usr/bin/env python3
"""A13: 검증된 교사 응답과 N_REF를 같은 train ID 집합으로 포장한다. 교사를 호출하지 않는다."""
from __future__ import annotations
import argparse
import copy
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tinylm.chat.canonical import normalize, validate
from tinylm.chat.supervision import encode_sample, sample_totals
from tinylm.eval.audit_io import (read_records, digest_json, sha256_file,
                                  tokenizer_digest, write_json_new, write_jsonl_new)
from tinylm.eval.sft_grading import grade_response


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference-train", required=True)
    ap.add_argument("--teacher-responses", required=True, help="id/response/teacher JSONL")
    ap.add_argument("--verification", required=True,
                    help="id/response_sha256/reference_sha256/correct/verifier/rationale JSONL")
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--serializer", default="chatml", choices=("chatml", "plain", "minimal", "gemma"))
    ap.add_argument("--seq", type=int, default=1024)
    ap.add_argument("--max-response-tokens", type=int, default=128)
    ap.add_argument("--out-dir", required=True)
    a = ap.parse_args(argv)
    out = Path(a.out_dir)
    if out.exists():
        ap.error("새 out-dir 필요")
    if min(a.seq, a.max_response_tokens) < 1:
        ap.error("길이는 양수")
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(a.tokenizer)
    references, candidates, verification = {}, {}, {}
    for raw in read_records(a.reference_train):
        ident = str(raw.get("meta", {}).get("id") or raw.get("id") or "")
        if not ident or ident in references:
            raise ValueError("reference train 고유 ID 필요")
        split = str(raw.get("meta", {}).get("split", "")).lower()
        if split != "train":
            raise ValueError(f"{ident}: meta.split=train만 받음. eval/불명 split 사용 금지")
        conv = validate(normalize(raw))
        if conv["messages"][-1]["role"] != "assistant":
            raise ValueError("reference assistant 없음")
        references[ident] = (raw, conv)
    for row in read_records(a.verification):
        key = (str(row["id"]), row["response_sha256"])
        if key in verification:
            raise ValueError("중복 verification")
        if not isinstance(row.get("correct"), bool):
            raise ValueError("verification.correct는 bool")
        verification[key] = row
    for row in read_records(a.teacher_responses):
        ident = str(row["id"])
        if ident not in references or not isinstance(row.get("response"), str) or not row.get("teacher"):
            raise ValueError("미등록 ID/비문자 응답/teacher provenance 없음")
        candidates.setdefault(ident, []).append(row)
    ref_rows, teacher_rows, rejected, accepted_info = [], [], [], []
    ref_encoded, teacher_encoded = [], []
    for ident, (raw, conv) in references.items():
        good = []
        for candidate in candidates.get(ident, []):
            text = candidate["response"]
            response_sha = digest_json(text)
            v = verification.get((ident, response_sha))
            reason = None
            if not text.strip():
                reason = "empty_response"
            elif v is None or v.get("correct") is not True:
                reason = "not_independently_verified_correct"
            elif v.get("reference_sha256") != digest_json(raw):
                reason = "verification_reference_mismatch"
            elif not v.get("verifier") or not v.get("rationale"):
                reason = "missing_verification_provenance"
            n_tokens = len(tok.encode(text, add_special_tokens=False).ids)
            if reason is None and n_tokens > a.max_response_tokens:
                reason = "response_too_long"
            grade = grade_response(raw, text)
            if reason is None and grade["status"] == "scored" and grade.get("correct") == 0:
                reason = "local_metadata_grade_failed"
            trial = copy.deepcopy(conv)
            trial["messages"][-1]["content"] = [{"type": "text", "text": text}]
            try:
                encoded = encode_sample(trial, tok, kind=a.serializer, max_length=a.seq+1)
            except ValueError as exc:
                encoded = None
                reason = reason or "serialization_or_context: " + str(exc)
            if reason:
                rejected.append({"id": ident, "response_sha256": response_sha, "reason": reason})
            else:
                good.append((n_tokens, response_sha, trial, encoded, candidate, v, grade))
        if not good:
            rejected.append({"id": ident, "reason": "no_accepted_candidate_for_matched_pair"})
            continue
        # 여러 정답 중 짧은 응답 우선. 학생 NLL 기반 선택을 수행했다고 주장하지 않는다.
        _, response_sha, trial, encoded, candidate, v, grade = min(good, key=lambda x: (x[0], x[1]))
        base = copy.deepcopy(conv)
        reference_text = "".join(b.get("text", "") for b in base["messages"][-1]["content"]
                                 if b.get("type") == "text")
        ref_grade = grade_response(raw, reference_text)
        if ref_grade["status"] == "scored" and ref_grade.get("correct") == 0:
            raise ValueError(f"{ident}: 정본 답이 자체 grading에 실패; 먼저 reference 감사")
        base["meta"].update(id=ident, split="train", distillation_arm="N_REF")
        trial["meta"].update(id=ident, split="train", distillation_arm="T_VERIFIED",
                             teacher=candidate["teacher"], teacher_response_sha256=response_sha)
        ref_rows.append(base)
        teacher_rows.append(trial)
        ref_encoded.append(encode_sample(base, tok, kind=a.serializer, max_length=a.seq+1))
        teacher_encoded.append(encoded)
        accepted_info.append({"id": ident, "response_sha256": response_sha,
                              "reference_sha256": digest_json(raw),
                              "teacher": candidate["teacher"], "verification": v,
                              "local_grade": grade})
    if not ref_rows:
        raise ValueError("검증을 통과한 matched pair 0개")
    out.mkdir(parents=True, exist_ok=False)
    write_jsonl_new(out / "N_REF.jsonl", ref_rows)
    write_jsonl_new(out / "T_VERIFIED.jsonl", teacher_rows)
    write_json_new(out / "selection.json", {"accepted": accepted_info, "rejected": rejected})
    contract = {"schema": "tinylm.text-kd-pairs.v1", "command": vars(a),
                "source_hashes": {p: sha256_file(p) for p in
                                  (a.reference_train, a.teacher_responses, a.verification)},
                "tokenizer_sha256": tokenizer_digest(tok),
                "matched_ids": [r["meta"]["id"] for r in ref_rows],
                "N_REF": sample_totals(ref_encoded), "T_VERIFIED": sample_totals(teacher_encoded),
                "output_hashes": {n: sha256_file(out / n) for n in ("N_REF.jsonl", "T_VERIFIED.jsonl")},
                "scope": "동일 accepted ID 비교. token 수/학습 시간은 자동 동일하지 않음.",
                "verification_limit": "외부 verifier의 의미 정답 판정을 신뢰한다. manifest 존재 자체가 정답 증명은 아님."}
    write_json_new(out / "contract.json", contract)
    print(json.dumps({"matched_pairs": len(ref_rows), "rejected_events": len(rejected),
                      "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
