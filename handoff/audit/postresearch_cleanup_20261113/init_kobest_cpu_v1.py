"""Check official task initialization with local test assets and no model."""
from pathlib import Path
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import tinylm

OUT = Path(__file__).resolve().parent
result = dict(schema="NOV13_KOBEST_TASK_INIT_CPU_V3", model_loads=0, gpu=0, tasks=[])
try:
    from lm_eval.api.task import ConfigurableTask
    from lm_eval.tasks._yaml_loader import load_yaml
    source = ROOT / "data_cache/p106b_official_eval_tools/lm_eval_d6de81643928d653435c431bae19945d41d32520/source/lm_eval/tasks/kobest"
    manifest = json.loads((ROOT / "data_cache/p106b_kobest_official_assets_v2_20261101/manifest.json").read_text())
    for item in manifest["tests"]:
        row = dict(family=item["family"], expected=item["rows"])
        try:
            config = load_yaml(str(source / ("kobest_" + item["family"] + ".yaml")))
            config.update(item["storage_overrides"])
            task = ConfigurableTask(config=config)
            row["rows"] = len(task.test_docs())
            assert row["rows"] == row["expected"]
            pairs = []
            for gold, pred in ((0, 0), (1, 1), (1, 0), (0, 0)):
                doc = dict(label=gold, gold=gold, paragraph="검산 문맥", question="원인",
                           premise="검산 전제", alternative_1="보기 하나", alternative_2="보기 둘",
                           context_1="검산 문장 하나", context_2="검산 문장 둘", word="검산",
                           sentence="검산 문장", query="검산 문장", choices=["하나", "둘", "셋", "넷"])
                size = 4 if item["family"] == "hellaswag" else 2
                scores = [(0.0 if i == pred else -10.0, True) for i in range(size)]
                processed = task.process_results(doc, scores)
                assert tuple(processed["f1"]) == (gold, pred)
                pairs.append(processed["f1"])
            score = float(task.aggregation()["f1"](pairs))
            assert abs(score - 11 / 15) < 1e-12
            row["synthetic_macro_f1"] = score
            row["synthetic_choices_checked"] = len(pairs)
            row["note"] = "공식 MC process_results와 YAML 지정 macro 집계. 합성 검산이며 실제 모델 점수가 아님."
            row["status"] = "TASK_INIT_PASS_NO_MODEL"
        except Exception as error:
            row.update(status="TASK_INIT_NOT_READY", error=type(error).__name__ + ": " + str(error))
        result["tasks"].append(row)
except Exception as error:
    result["import_error"] = type(error).__name__ + ": " + str(error)
result["status"] = "PASS" if len(result["tasks"]) == 5 and all(
    row["status"] == "TASK_INIT_PASS_NO_MODEL" for row in result["tasks"]) else "NOT_READY"
with (OUT / "KOBEST_TASK_INIT_CPU_v3.json").open("x", encoding="utf-8") as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(0 if result["status"] == "PASS" else 8)
