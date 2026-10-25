"""One-shot CPU execution record for the explicit legacy60 TRAIN approval."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_admission as admission

BASE = ROOT / "data_cache/p106b_text_work_20261022"
OLD = BASE / "root_closed_full/sft_legacy60_recovery_20261025"
NEW = BASE / "approved_train60_20261025_v2"
AUDIT = ROOT / "handoff/audit/train60_approval_20261025"
PACKET = BASE / "packets/sft_legacy60_recovery_20261025.json"
EXPOSURE = ROOT / "handoff/audit/WIP_20261025_SFT_EXPOSURE_ROOT_READBACK.json"
TOKENIZER = ROOT / "data_cache/tok-ko-en-32768-chat32.json"


def artifact(path):
    return admission.read_artifact(path)[1]


def write(path, data):
    return admission.exclusive_json(path, data)


def main():
    old, old_artifact = admission.read_json(OLD / "bundle")
    assert old_artifact["sha256"] == "337AC535120C9F06DF2D18F89F15FBBCD6D2B1DD2C97EBB0189FA77BE9A8DB19"
    prior, prior_artifact = admission.read_json(OLD / "root_semantic_review.json")
    exposure, exposure_artifact = admission.read_json(EXPOSURE)
    assert len(old["sources"]) == 60 and len(old["candidates"]) == 180
    assert prior["verdict_counts"] == {"HOLD": 22, "PROVISIONAL_ACCEPT": 158}
    assert exposure["actual_step_events"] == 704 and exposure["legacy60_found"] == 60
    assert artifact(TOKENIZER)["sha256"] == "9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E"
    inputs = [old_artifact, prior_artifact, exposure_artifact, artifact(PACKET),
              artifact(OLD / "root_semantic_review.md"), artifact(OLD / "original_and_candidates_readable.md"),
              artifact(OLD / "publications.json"), *old["artifacts"]]
    assert all(artifact(spec["path"]) == spec for spec in inputs)
    assert all(s["source_metadata"]["source_license"] == "Apache-2.0" for s in old["sources"])
    assert len({s["source_id"] for s in old["sources"]}) == 60
    if NEW.exists():
        raise FileExistsError("exclusive approved TRAIN namespace already exists")
    NEW.mkdir()
    approval = dict(schema="P106B_LEGACY60_TRAIN_APPROVAL_V1",
        user_reply_reference="call_a1a60686f7e64a5e8a41d23ba94cb90a item0",
        user_reply="A(권장): 의미·용어·지도할 답변·토큰 검토를 통과한 것만 원본과 함께 TRAIN에 유지합니다. 새 평가셋으로 쓰지 않고, 과거 문서 단위 누설은 미확인으로 명시합니다. 실용적으로 편입할 수 있지만 전역 누설 0을 보증하지 않습니다.",
        scope="ONLY_OLD_60_SOURCES_180_VARIANTS", prior_manual_review=prior_artifact,
        exposure_readback=exposure_artifact,
        original_policy="IMMUTABLE_ORIGINALS_RETAIN_HISTORICAL_TRAIN_LINEAGE; NO_EXTRA_ORIGINAL_COPY",
        global_document_overlap="UNVERIFIED", training_runs=0, gpu_calls=0)
    approval_artifact = write(NEW / "approval.json", approval)
    frozen = admission.freeze(PACKET, OLD / "imported", OLD / "publications.json", NEW / "bundle.json")
    bundle, bundle_artifact = admission.read_json(NEW / "bundle.json")
    assert bundle["sources"] == old["sources"] and bundle["candidates"] == old["candidates"]
    assert bundle["artifacts"] == old["artifacts"]
    reviewed = {d["candidate_id"]: d for d in prior["decisions"]}
    sources = {s["source_id"]: s for s in bundle["sources"]}
    assert set(reviewed) == {c["candidate_id"] for c in bundle["candidates"]}
    decisions = []
    for candidate in bundle["candidates"]:
        decision = reviewed[candidate["candidate_id"]]
        source = sources[candidate["source_id"]]
        assert decision["candidate_sha256"] == candidate["candidate_sha256"]
        assert decision["source_sha256"] == candidate["source_sha256"]
        verdict = "ACCEPT" if decision["verdict"] == "PROVISIONAL_ACCEPT" else "HOLD"
        assert decision["verdict"] in ("PROVISIONAL_ACCEPT", "HOLD")
        meta = source["source_metadata"]
        reasons = dict(meaning=decision["reason"], terminology=decision["reason"],
            provenance="원천 ID·메시지·license·revision과 실제 TRAIN 노출의 정확 대조를 재사용한다.",
            rights="고정 원천의 Apache-2.0 선언과 revision·출처를 보존해 승인된 TRAIN 용도로만 사용한다. 전체 권리의 독립 법률 검증을 주장하지 않는다.",
            supervision="기존 총괄 판독에서 지정한 assistant 턴만 지도한다. 다른 턴과 원문맥은 보존한다.")
        evidence = dict(source_sha256=source["source_sha256"],
            reference=str(OLD / "root_semantic_review.json") + " @ " + prior_artifact["sha256"]
                + "; packet=" + str(PACKET) + "; source=" + str(source["source_id"]),
            context=decision["reason"] + "; source=" + meta["source"] + "; revision="
                + meta["source_revision"] + "; license=" + meta["source_license"])
        row = dict(candidate_id=candidate["candidate_id"], candidate_sha256=candidate["candidate_sha256"],
            decision=verdict, supervised_assistant_turns=decision["proposed_supervised_assistant_turns"],
            prior_manual_review_sha256=prior_artifact["sha256"],
            reviews={dimension: dict(decision=verdict, reviewer="root Codex; immutable manual comparison reused",
                reason=reasons[dimension], evidence=evidence) for dimension in admission.DIMENSIONS})
        if source["author_hold"] and verdict == "ACCEPT":
            assert source["source_id"] == 198 and row["supervised_assistant_turns"] == [2]
            row["author_hold_resolution"] = "원천198의 원문과 세 변형을 다시 직접 대조했다. OpenAI 회사와 오픈소스 AI 모델의 구분 및 후속 정정 요구를 보존한다. 초기 오해 답은 문맥으로만 유지하고 교정 뒤 두 번째 assistant 답만 지도한다. 약어와 전문 용어를 다른 말로 대체하지 않았다. 원천192의 보류는 해제하지 않는다."
        decisions.append(row)
    reviews = dict(schema=admission.REVIEWS_SCHEMA, parent_packet_sha256=bundle["parent_packet_sha256"],
        bundle_sha256=bundle_artifact["sha256"], decisions=decisions,
        approval_sha256=approval_artifact["sha256"], automatic_semantic_reviews=0)
    write(NEW / "reviews.json", reviews)
    roots = [dict(root_id=s["root_id"], group_id="source-record:" + s["source_object_sha256"], split="train",
        source_history=[dict(source_id=s["source_id"], source_sha256=s["source_sha256"], source_split="train",
            source_document_id=None, source_record_sha256=s["source_object_sha256"],
            prior_exposure_splits=["train"], evidence=str(EXPOSURE) + " @ " + exposure_artifact["sha256"])])
        for s in bundle["sources"]]
    write(NEW / "root_splits.json", dict(schema=admission.TRAIN_REUSE_SCHEMA,
        parent_packet_sha256=bundle["parent_packet_sha256"],
        split_policy_reference=str(NEW / "approval.json") + " @ " + approval_artifact["sha256"],
        identity_scope="SOURCE_RECORD_TRAIN_ONLY", global_document_overlap="UNVERIFIED",
        source_document_identity="MISSING", train_exposure_readback=exposure_artifact, roots=roots))
    write(NEW / "encoding_contract.json", dict(schema=admission.ENCODING_SCHEMA,
        template="chatml", context=1024, tokenizer=dict(path=str(TOKENIZER), sha256=artifact(TOKENIZER)["sha256"])))
    result = admission.prepare(NEW / "bundle.json", NEW / "reviews.json", NEW / "root_splits.json",
                               NEW / "encoding_contract.json", NEW / "corpus")
    verified = admission.verify_admission(NEW / "corpus", result["manifest"]["sha256"])
    rows = []
    language = Counter()
    turns = Counter()
    kinds = Counter()
    mtp_targets = Counter()
    for row, record in admission.iter_sft_records(NEW / "corpus", result["manifest"]["sha256"], split="train"):
        candidate = next(c for c in bundle["candidates"] if c["candidate_id"] == row["candidate_id"])
        old_decision = reviewed[row["candidate_id"]]
        assert row["canonical"]["messages"] == candidate["payload"]["messages"]
        assert set(s for s in record.segments if s) == set(old_decision["proposed_supervised_assistant_turns"])
        assert all((s > 0) == (y != -100) for s, y in zip(record.segments, record.y))
        assert row["canonical"]["meta"]["source_language"] == "en"
        assert row["split"] == "train" and record.x_tokens <= 1024
        language[row["canonical"]["meta"]["language"]] += 1
        turns[str(old_decision["proposed_supervised_assistant_turns"])] += 1
        kinds[row["canonical"]["meta"]["variant_kind"]] += 1
        mtp_targets.update(row["mtp_target_tokens"])
        rows.append(row)
    assert len(rows) == 158 and result["excluded_rows"] == 22
    for split in ("val", "test"):
        try:
            list(admission.iter_sft_records(NEW / "corpus", result["manifest"]["sha256"], split=split))
        except ValueError as error:
            assert "no admitted SFT records" in str(error)
        else:
            raise AssertionError("TRAIN-only data became an evaluation corpus")
    assert all(artifact(spec["path"]) == spec for spec in inputs)
    outputs = [artifact(p) for p in NEW.rglob("*") if p.is_file()]
    assert all(spec["bytes"] < 20_000_000 for spec in outputs)
    report = dict(schema="P106B_APPROVED_TRAIN60_READBACK_V1", utc=datetime.now(timezone.utc).isoformat(),
        scope="USER_APPROVED_60_ONLY; CPU_PREPARATION_AND_CONSUMER_READBACK",
        result=result, verified=verified, approval=approval_artifact, inputs=inputs, outputs=outputs,
        original_sources=60, candidates=180, accepted_variants=len(rows), held_variants=22,
        accepted_source_roots=len({r["root_id"] for r in rows}), language=dict(language),
        variant_kinds=dict(kinds), supervised_assistant_turns=dict(turns), mtp_target_tokens=dict(mtp_targets),
        exact_distinct_payloads=len({admission.sha_value(r["canonical"]["messages"]) for r in rows}),
        maximum_input_tokens=max(r["input_tokens"] for r in rows),
        unchanged_source_and_candidate_identities=True, originals_and_prior_review_unchanged=True,
        global_document_overlap="UNVERIFIED", source_document_identity="MISSING",
        original_rows_copied_into_new_corpus=0, val_rows=0, test_rows=0,
        author_hold_resolution_source_ids=[198],
        earlier_incomplete_preparation=str(BASE / "approved_train60_20261025"),
        applied_to_existing_trainer=False, training_runs=0, model_weight_loads=0, gpu_calls=0,
        code_sha256=admission.source_code_hashes())
    summary = write(AUDIT / "readback.json", report)
    print(json.dumps(dict(report=summary, accepted=result["accepted_rows"], held=result["excluded_rows"],
        counts=result["counts"], language=dict(language), global_document_overlap="UNVERIFIED",
        training_runs=0, gpu_calls=0), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
