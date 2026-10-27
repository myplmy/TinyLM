"""Read this session's closed reports; create immutable, compact readbacks."""
from pathlib import Path
import hashlib
import json
import statistics

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / "handoff/audit/oct27_independent"


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def ref(path):
    p = ROOT / path
    return dict(path=str(path), bytes=p.stat().st_size,
                sha256=hashlib.sha256(p.read_bytes()).hexdigest().upper())


def write(name, value):
    p = AUDIT / name
    with p.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write(chr(10))


def resource():
    prefix = "test_result/evidence/p106b_resource_matrix_v2_20261027"
    profiles = load("handoff/audit/oct27_independent/resource_profile_v4.json")
    lanes, cases = [], []
    for spec in profiles["models"]:
        for device in ("cuda", "cpu"):
            path = prefix + "/" + spec["id"] + "_" + device + "/report.json"
            d = load(path)
            assert d["returncode"] == 0 and d["originals_unchanged"]
            assert d["model_object_released"] and d["model_proof"]["checkpoint_bytes_unchanged"]
            assert d["model_proof"]["final_core_verified"] and d["model_proof"]["gradients_absent"]
            assert len(d["records"]) == 16 and len(d["natural_answers"]) == 4
            assert all(r["actual_token_ids_equal"] for r in d["records"])
            assert all(r["generation"]["actual_token_ids_and_stop_equal"] for r in d["natural_answers"])
            cleanup = d.get("cuda_owned_cleanup")
            if device == "cuda":
                assert cleanup["allocated_bytes"] == cleanup["reserved_bytes"] == 0
            log = "test_result/101_log_20261027_P106B_Stage11bW_resource_" + spec["id"].replace("-", "_") + "_" + device + ".txt"
            assert "[runlog] 종료코드 0 " in (ROOT / log).read_text(encoding="utf-8")
            lane = dict(model=spec["id"], device=device, report=ref(path), log=ref(log),
                started_at=d["started_at"], ended_at=d["ended_at"], seconds=d["seconds"],
                parameters=d["parameters"], checkpoint=spec["checkpoint"],
                held_storage=d["held_after_generation"], rss_loaded=d["rss_loaded"],
                rss_closed=d["rss_closed"], model_object_released=True,
                cuda_peak_allocated_bytes=d.get("cuda_peak_allocated_bytes"),
                cuda_peak_reserved_bytes=d.get("cuda_peak_reserved_bytes"), cleanup=cleanup,
                primary_timing="UNOBSERVED_PRODUCT_SAMPLER; FIXED_32_TOKENS; TOKENIZATION_EXCLUDED",
                ttft_timing="OBSERVER_AFTER_PICK; SYNCHRONIZATION_AND_KV_AUDIT_OVERHEAD_INCLUDED",
                workloads=[])
            for workload in profiles["workloads"]:
                rows = [r for r in d["records"] if r["workload"] == workload["id"] and not r["warmup"]]
                assert len(rows) == 3
                lane["workloads"].append(dict(id=workload["id"], prompt_tokens=workload["prompt_tokens"],
                    new_tokens=32, measured_repeats=3,
                    median_unobserved_seconds=statistics.median(r["unobserved"]["seconds"] for r in rows),
                    median_unobserved_tokens_per_second=statistics.median(r["unobserved"]["end_to_end_tokens_per_second"] for r in rows),
                    median_unobserved_characters_per_second=statistics.median(len(r["answer"])/r["unobserved"]["seconds"] for r in rows),
                    median_unobserved_utf8_bytes_per_second=statistics.median(len(r["answer"].encode("utf-8"))/r["unobserved"]["seconds"] for r in rows),
                    median_observed_first_token_ms=statistics.median(r["timing"]["first_token_ms"] for r in rows),
                    median_unobserved_external_cpu_percent=statistics.median(r["unobserved"]["cpu_load"]["external_percent"] for r in rows),
                    max_returned_kv_bytes=max(r["max_returned_kv_storage_bytes"] for r in rows),
                    max_prior_plus_returned_kv_bytes=max(r["max_prior_plus_returned_kv_storage_bytes"] for r in rows),
                    actual_token_ids_equal=True))
            lane["natural_max_length_count"] = sum(r["generation"]["metadata"]["finish_reason"] == "MAX_NEW" for r in d["natural_answers"])
            for case in d["natural_answers"]:
                gen = case["generation"]
                cases.append(dict(model=spec["id"], device=device, **case["case"], answer=gen["answer"],
                    metadata=gen["metadata"], token_ids_equal=True))
            lanes.append(lane)
    write("resource_v2_readback_v1.json", dict(schema="ROOT_RESOURCE_READBACK_V1", lanes=lanes,
        source=ref("handoff/audit/oct27_independent/resource_profile_v4.json"),
        shell_parent_returncode=None, shell_parent_status="NOT_RECOVERED_AFTER_COMPACTION",
        child_runlog_exit_zero_count=10, child_report_exit_zero_count=10,
        no_extra_model_execution=True, permitted_claim="DESCRIPTIVE_ONLY"))
    write("resource_natural_answers_v1.json", dict(schema="ROOT_NATURAL_ANSWERS_V1", cases=cases,
        automated_correctness_score=None, not_a_benchmark=True))
    print("RESOURCE model/device heldMiB peakAllocatedMiB ko128/en128/ko512/en512 tokps")
    for lane in lanes:
        print(lane["model"], lane["device"], round(lane["held_storage"]["unique_storage_bytes"]/2**20, 3),
              None if lane["cuda_peak_allocated_bytes"] is None else round(lane["cuda_peak_allocated_bytes"]/2**20, 3),
              [round(r["median_unobserved_tokens_per_second"], 2) for r in lane["workloads"]],
              "natural_cap", lane["natural_max_length_count"])


def adamuon():
    path = "test_result/evidence/p005b_adamuon_gradient_cost_v1_20261027/report.json"
    d = load(path)
    assert d["returncode"] == 0 and all(r["close"] for r in d["numerical"])
    assert d["body_optimizer_steps"] == d["checkpoint_writes"] == 0
    assert d["cleanup"]["allocated_bytes"] == d["cleanup"]["reserved_bytes"] == 0
    assert d["capture"]["original_model"]["final_core_verified"]
    rows = []
    for obs in d["observations"]:
        assert len(obs["steps"]) == 6 and obs["gpu_gradients_unchanged"]
        steady = obs["steps"][1:]
        rows.append(dict(arm=obs["arm"], order=obs["order"],
            first_matrix_ms=1000*obs["steps"][0]["matrix_seconds"],
            first_total_ms=1000*obs["steps"][0]["total_optimizer_seconds"],
            steady_matrix_median_ms=1000*statistics.median(r["matrix_seconds"] for r in steady),
            steady_adamw_median_ms=1000*statistics.median(r["adamw_seconds"] for r in steady),
            steady_total_median_ms=1000*statistics.median(r["total_optimizer_seconds"] for r in steady),
            matrix_state_bytes=obs["matrix_state"]["unique_storage_bytes"],
            adamw_state_bytes=obs["adamw_state"]["unique_storage_bytes"],
            peak_allocated_bytes=obs["peak_allocated_bytes"],
            peak_reserved_bytes=obs["peak_reserved_bytes"]))
    write("adamuon_actual_readback_v1.json", dict(schema="ROOT_ADAMUON_COST_READBACK_V1", report=ref(path),
        actual_tool_session=22547, actual_parent_returncode=0, rows=rows,
        same_gradient_reused_not_training=True, common_lr=.001,
        quality_not_measured=True, permitted_claim="DESCRIPTIVE_ONLY"))
    print("ADAMUON", json.dumps(rows))


if __name__ == "__main__":
    resource()
    adamuon()
