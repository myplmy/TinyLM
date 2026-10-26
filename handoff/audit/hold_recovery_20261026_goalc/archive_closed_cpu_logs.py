"""Preserve a fixed set of closed CPU logs and exact result backlinks."""
import json
from pathlib import Path
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(ROOT))
from scripts.p106b_native_text_audit import file_sha, write_json


def read(name):
    return json.loads((AUDIT / name).read_text(encoding="utf-8"))


def main():
    final = read("cache_v5_verify_receipt.json")
    assert final["actual_exit_code"] == 0
    proof = ROOT / final["proof_path"]
    assert file_sha(proof) == final["proof_sha256"]
    assert json.loads(proof.read_text(encoding="utf-8"))["status"] == "CPU_FULL_RECOVERY_CACHE_VERIFIED"
    # This list is fixed independently of result-document contents. Names use
    # the archive date; individual execution times remain in original receipts.
    jobs = [
        ("inventory_v1.log", "a_hold_inventory", "inventory_receipt.json", "actual_outer_returncode"),
        ("proposals_v1.log", "b_proposals_v1", "proposals_v1_receipt.json", "exit_code"),
        ("proposals_v2.log", "c_proposals_v2", "proposals_v2_receipt.json", "exit_code"),
        ("proposals_v3.log", "d_proposals_v3", "proposals_v3_receipt.json", "actual_exit_code"),
        ("cache_v3_build.log", "e_cache_v3_build", "cache_v3_build_receipt.json", "actual_exit_code"),
        ("cache_v3_verify.log", "f_cache_v3_verify", "cache_v3_verify_receipt.json", "actual_exit_code"),
        ("cache_v4_build.log", "g_cache_v4_build", "cache_v4_build_receipt.json", "actual_exit_code"),
        ("cache_v5_build.log", "h_cache_v5_build", "cache_v5_build_receipt.json", "actual_exit_code"),
        ("cache_v5_verify.log", "i_cache_v5_verify", "cache_v5_verify_receipt.json", "actual_exit_code"),
    ]
    aliases = []
    for source_name, label, receipt_name, exit_key in jobs:
        receipt = read(receipt_name)
        assert receipt[exit_key] == 0, receipt_name
        source = AUDIT / source_name
        target = ROOT / "test_result" / ("101_log_20261027_P106B_Stage10jW" + label + "_cpu.txt")
        assert source.is_file() and not source.is_symlink() and not target.is_symlink()
        assert source.stat().st_size < 20_000_000
        if not target.exists():
            with target.open("xb") as stream:
                stream.write(source.read_bytes())
        assert file_sha(source) == file_sha(target)
        aliases.append(dict(original=str(source.relative_to(ROOT)),
            result_alias=str(target.relative_to(ROOT)), bytes=target.stat().st_size,
            sha256=file_sha(source), actual_exit_code=0,
            execution_receipt=str((AUDIT / receipt_name).relative_to(ROOT)),
            execution_receipt_sha256=file_sha(AUDIT / receipt_name)))
    write_json(AUDIT / "closed_raw_log_aliases_v1.json", dict(
        schema="P106B_CLOSED_CPU_RAW_LOG_ALIASES_V1", rows=aliases,
        original_logs_preserved=True, archive_date="2026-10-27",
        cache_v3_status="INTERMEDIATE_KNOWN_POSTBUILD_RESIDUALS",
        cache_v4_verification="NOT_RUN_KNOWN_INTERWIKI_RESIDUAL",
        final_cache="cache_v5", training_authorized=False))
    heading = "## 555. HOLD 전량 재검토와 의미 보존 복구 캐시"
    result = "test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md"
    manifest = dict(schema="TINYLM_RESULT_CLOSURE_V1",
        session_id="01a17740-f435-7243-874c-2b5d58181c4c",
        wip="handoff/WIP_20261026b_작업원장.md",
        input_logs=[r["result_alias"] for r in aliases],
        mappings=[dict(log=r["result_alias"], result=result, section=heading, status="RECORDED") for r in aliases])
    write_json(AUDIT / "HOLD_RECOVERY_RESULT_CLOSURE.json", manifest)
    print(dict(closed_logs=len(aliases), result_section=heading, originals_preserved=True))


if __name__ == "__main__":
    main()
