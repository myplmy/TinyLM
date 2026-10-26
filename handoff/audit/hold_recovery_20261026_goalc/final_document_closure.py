"""Check changed closure documents while retaining actual frozen-code evidence.

This producer writes only its own handoff/frontier/audit records. It does not
access any ledger file. Exact ledger-byte validation and rename remain owned by
the following direct scripts/wip.py CLI invocation.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

LOCAL = Path(__file__).resolve().parent
ROOT = LOCAL.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from scripts.p106b_native_text_audit import file_sha, write_json
import frontier_queue_gate as queue
import frontier_semantic_gate as semantic
import handoff_time
import check_result_closure
import check_static_all


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    audit = ROOT / "handoff/audit"
    handoff = ROOT / "handoff/202610270258_HANDOFF.md"
    old_semantic_path = audit / "FRONTIER_SEMANTIC_B779234C068A_1F6AE1FF0BE7.json"
    old_queue_path = audit / "FRONTIER_QUEUE_B779234C068A_D0B4B20B954A.json"
    old, old_queue = read(old_semantic_path), read(old_queue_path)
    queue_path, frontier, _ = queue.prepare(ROOT, handoff)
    semantic_path, state, _ = semantic.prepare(ROOT)
    current, current_queue = read(semantic_path), read(queue_path)
    assert {r["plan_id"] for r in old["plan_reviews"]} == {r["plan_id"] for r in current["plan_reviews"]}
    assert old["proposal_manifest"] == current["proposal_manifest"]
    for key in ("plan_reviews", "proposal_reviews", "none_buildable_approval_ref"):
        current[key] = copy.deepcopy(old[key])
    current.update(reused_prior_artifact=str(old_semantic_path.relative_to(ROOT)),
        reused_prior_artifact_sha256=file_sha(old_semantic_path))
    semantic_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    previous = {r["plan_id"]: r for r in old_queue["dispositions"]}
    for row in current_queue["dispositions"]:
        if row["review"] == "AUTO_NO_LAUNCHER":
            continue
        if row["plan_id"] == "P005b":
            row.update(decision="HOLD", review="MANUAL",
                reason="다른세션Stage16런처가등록됐다. 기술비용/수치증거는그소유세션에서회수하며이번자료goal의큐로실행하지않는다. 실행재고를미구현으로되돌리거나삭제하지않는다.",
                approval_ref="현재사용자CPU데이터goal은GPU/가중치/새실험실행을제외함;타세션Stage16권한은그소유범위로보존")
        else:
            assert previous[row["plan_id"]]["review"] == "MANUAL"
            row.update(copy.deepcopy(previous[row["plan_id"]]))
    queue_path.write_text(json.dumps(current_queue, ensure_ascii=False, indent=2) + chr(10), encoding="utf-8")
    text = handoff.read_text(encoding="utf-8")
    for prefix, marker in [("<!-- TINYLM_FRONTIER_QUEUE_V1 ", queue.marker(queue_path, frontier)),
                           ("<!-- TINYLM_FRONTIER_SEMANTIC_V1 ", semantic.marker(semantic_path, state))]:
        matches = [line for line in text.splitlines() if line.startswith(prefix)]
        assert len(matches) == 1
        text = text.replace(matches[0], marker)
    text = text.replace("HOLD_RECOVERY_FINAL_V2_STATIC_AUDIT.json", "HOLD_RECOVERY_DOCUMENT_CLOSURE_STATIC_AUDIT.json")
    text = text.replace("종결범위는68PASS/0ERROR/8NOT_RUN이다.", "동결코드감사는68PASS/0ERROR/8NOT_RUN이며현재문서종결은5PASS/0ERROR/8NOT_RUN으로별도검사한다. 합쳐서새글로벌PASS로부르지않는다.")
    handoff.write_text(text, encoding="utf-8")
    reservation = dict(schema="P106B_PENDING_AUDIT_OUTPUT_LINK_RESERVATION_V1", status="NOT_RUN",
        purpose="Reserve document-audit output self-link, not execution/PASS evidence.")
    write_json(LOCAL / "final_audit_link_reservation_v3.json", reservation)
    output = LOCAL / "HOLD_RECOVERY_DOCUMENT_CLOSURE_STATIC_AUDIT.json"
    write_json(output, reservation)
    write_json(LOCAL / "frontier_reconciliation_v3.json", dict(schema="P106B_FRONTIER_RECONCILIATION_V1",
        current_queue=str(queue_path.relative_to(ROOT)), current_semantic=str(semantic_path.relative_to(ROOT)),
        p005b_new_launcher_preserved=True, other_private_outputs_read=False, other_execution_not_relaunched=True))
    write_json(LOCAL / "close_retry_v2.json", dict(schema="P106B_CLOSE_RETRY_RECORD_V1",
        reason="A separately owned launcher changed frontier/source signatures after the previous audit.",
        close_attempted=False, ledger_changed=False))
    prior_path = LOCAL / "HOLD_RECOVERY_FINAL_V2_STATIC_AUDIT.json"
    prior = read(prior_path)
    built = read(ROOT / "data_cache/p106b_hold_recovery_v1_20261026_goalc/cache_v5/built.json")
    assert len(built["source_code_sha256"]) == 15
    for path, digest in built["source_code_sha256"].items():
        assert file_sha(ROOT / path) == digest, path
    source = ROOT / ".agents/skills/session-handoff/scripts/check_handoff_codex.py"
    spec = importlib.util.spec_from_file_location("hold_final_codex_handoff", source)
    checker = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = checker
    spec.loader.exec_module(checker)
    validation = checker.validate(handoff)
    assert not validation.errors and not validation.warnings, (validation.errors, validation.warnings)
    assert not queue.verify_handoff(ROOT, handoff)
    assert not semantic.verify_handoff(ROOT, handoff)
    manifest = read(LOCAL / "HOLD_RECOVERY_RESULT_CLOSURE.json")
    assert not check_result_closure.validate_manifest(manifest,
        read_result=lambda p: (ROOT / p).read_text(encoding="utf-8"), log_exists=lambda p: (ROOT / p).is_file())
    bad, ok, skipped = handoff_time.audit_all([handoff])
    assert not bad and len(ok) == 1 and not skipped
    assert semantic.snapshot(ROOT)["source_sha256"] == state["source_sha256"]
    checks = [dict(name=name, status="PASS", returncode=0, reason="Actual original validator in current exact document scope.", output_sha256=None)
        for name in ("check_handoff_codex", "frontier_queue_gate", "frontier_semantic_gate", "check_result_closure", "handoff_time")]
    checks += [dict(row) for row in prior["checks"] if row["status"] == "NOT_RUN"]
    assert len(checks) == 13
    paths = [handoff, queue_path, semantic_path, LOCAL / "HOLD_RECOVERY_RESULT_CLOSURE.json"] + [ROOT / p for p in built["source_code_sha256"]]
    records = [dict(status="EXACT_DOCUMENT_AND_FROZEN_CODE", path=str(p.relative_to(ROOT)), sha256=file_sha(p)) for p in paths]
    canonical = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    counts = {"pass": 5, "errors": 0, "actionable_warnings": 0, "accepted_info": 0, "not_run": 8}
    payload = dict(schema="TINYLM_STATIC_AUDIT_V1", profile="codex-safe",
        execution_mode="incremental_document_closure_with_explicit_inherited_frozen_code_evidence",
        wip=prior["wip"], worktree_scope="EXACT_DOCUMENTS_AND_FROZEN_CODE_NOT_WHOLE_PROJECT_CLEAN",
        worktree_manifest=records, worktree_sha256=hashlib.sha256(canonical.encode()).hexdigest().upper(),
        counts=counts, checks=checks,
        inherited_code_audit=dict(path=str(prior_path.relative_to(ROOT)), sha256=file_sha(prior_path),
            historical_counts=prior["counts"], frozen_production_sha_matches=15, not_current_whole_project_pass=True),
        reason="Only closure documents/frontier metadata changed; current exact documents rechecked and unchanged production SHAs verified. Global original failures remain unresolved.",
        ledger_bytes_must_be_revalidated_by_direct_close_cli=True, global_errors_not_repaired=True, training_authorized=False)
    check_static_all._write_evidence(output, payload)
    write_json(LOCAL / "closure_checks_v1.json", dict(schema="P106B_HOLD_RECOVERY_CLOSURE_CHECKS_V1",
        status="PRE_CLOSE_CHECKS_PASS", handoff=str(handoff.relative_to(ROOT)), handoff_sha256=file_sha(handoff),
        expected_ledger=prior["wip"], static_audit_sha256=file_sha(output), document_checks=5,
        current_queue=str(queue_path.relative_to(ROOT)), current_semantic=str(semantic_path.relative_to(ROOT)),
        source_signature_at_check=state["source_sha256"], private_other_session_data_read=False))
    print(json.dumps(dict(current_document_checks=5, errors=0, not_run=8,
        queue=str(queue_path.relative_to(ROOT)), semantic=str(semantic_path.relative_to(ROOT))), ensure_ascii=False))


if __name__ == "__main__":
    main()
