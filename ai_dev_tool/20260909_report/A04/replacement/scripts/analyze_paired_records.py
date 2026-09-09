"""A04: 문항/가족 단위 재분석. 학습 seed를 문항으로 pooling하지 않는다."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tinylm.eval.audit_io import read_records, write_json_new
from tinylm.eval.paired_records import summarize_paired, cluster_bootstrap, paired_bpb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--model-a", required=True)
    ap.add_argument("--model-b", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--metric", default="correct")
    ap.add_argument("--cluster-key", default=None)
    ap.add_argument("--family-map", help="JSON: item id -> 독립 감사한 family id")
    ap.add_argument("--draws", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=99)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    left = [r for r in read_records(a.a) if r.get("model") == a.model_a and r.get("task") == a.task]
    right = [r for r in read_records(a.b) if r.get("model") == a.model_b and r.get("task") == a.task]
    if not left or not right:
        ap.error("요청 task/model의 결과가 없음")
    # 한 파일에 반복 학습 seed가 섞여 있으면 중복 id 검사가 거절한다.
    if a.family_map:
        families = json.loads(Path(a.family_map).read_text(encoding="utf-8"))
        for r in left + right:
            if r["id"] not in families:
                raise ValueError(f"family map에 없는 id: {r['id']}")
            r[a.cluster_key or "family"] = str(families[r["id"]])
    result = (paired_bpb(left, right, cluster_key=(a.cluster_key or "family") if a.family_map
                         else a.cluster_key, draws=a.draws, seed=a.seed)
              if a.metric == "bpb" else summarize_paired(left, right, a.metric))
    if a.metric != "bpb" and (a.cluster_key or a.family_map):
        result["cluster_bootstrap"] = cluster_bootstrap(
            left, right, a.metric, cluster_key=a.cluster_key or "family",
            draws=a.draws, seed=a.seed)
    result["training_seed_scope"] = "one checkpoint per side; evaluate seeds separately"
    write_json_new(a.out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
