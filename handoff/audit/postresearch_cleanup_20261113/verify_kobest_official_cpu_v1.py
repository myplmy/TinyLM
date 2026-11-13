"""고정 공식 집계 함수의 CPU 계산만 확인한다. 문항/모델 평가는 하지 않는다."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import tinylm

source = ROOT / "data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source/lm_eval/tasks/kobest/utils.py"
spec = importlib.util.spec_from_file_location("kobest_pinned_utils", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
cases = [([(0, 0), (1, 1)], 1.0), ([(0, 1), (1, 0)], 0.0),
         ([(0, 0), (1, 1), (1, 0), (0, 0)], 11 / 15)]
values = []
for items, expected in cases:
    actual = float(module.macro_f1_score(items))
    assert abs(actual - expected) < 1e-12
    values.append(dict(items=items, expected=expected, actual=actual))
result = dict(schema="NOV13_KOBEST_OFFICIAL_MACRO_F1_CPU_V1", source=str(source.relative_to(ROOT)),
              source_sha256=hashlib.sha256(source.read_bytes()).hexdigest().upper(),
              tests=values, model_loads=0, gpu=0, benchmark_scores="NOT_RUN")
with Path(__file__).with_name("KOBEST_OFFICIAL_MACRO_F1_CPU_v1.json").open("x", encoding="utf-8") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print("공식 macro-F1 CPU3 통과; 모델 평가0")
