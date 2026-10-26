"""Posthoc label-choice readback from closed BoolQ raw; never calibrate or train."""
from collections import Counter
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import math

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent

def sha(raw):
    return hashlib.sha256(raw).hexdigest().upper()

def main():
    output=BASE/"boolq_selection_readback_v1.json"
    assert not output.exists()
    rows_out=[]
    correspondence=None
    for arm in ["muon","normuon"]:
        directory=ROOT/("test_result/evidence/p106b_native_format_official_v1_20261026_format_"+arm+"_json_recovery_v3_full")
        closed=json.loads((directory/"root_closed_ref.json").read_text())
        assert closed["actual_supervisor_exit"]==0
        report_path=ROOT/closed["path"]
        assert sha(report_path.read_bytes())==closed["sha256"]
        worker_path=directory/"worker.json"
        worker=json.loads(worker_path.read_text())
        manifest=worker["sample_manifests"]["boolq"]
        assert manifest["rows"]==3270
        matrix=[[0,0],[0,0]]
        labels=Counter()
        identities=[]
        concatenated=hashlib.sha256()
        original_accuracy_sum=0
        ties=0
        for spec in manifest["shards"]:
            path=directory/spec["path"]
            raw=path.read_bytes()
            assert len(raw)==spec["bytes"] and sha(raw)==spec["sha256"]
            concatenated.update(raw)
            lines=raw.splitlines()
            assert len(lines)==spec["rows"]
            for line in lines:
                row=json.loads(line)
                contract=row["native_format_recount"]
                assert contract["choices"]==["no","yes"] and contract["task"]=="boolq"
                gold=contract["gold"]
                assert type(gold) is int and gold in [0,1]
                scores=[float(x[0]) for x in row["filtered_resps"]]
                assert len(scores)==2 and all(math.isfinite(x) for x in scores)
                predicted=max(range(2),key=lambda n:scores[n])
                ties+=int(scores[0]==scores[1])
                assert float(row["acc"])==int(predicted==gold)
                matrix[gold][predicted]+=1
                labels[gold]+=1
                original_accuracy_sum+=row["acc"]
                identities.append([row["doc_id"],row["doc_hash"],contract["gold"]])
        assert concatenated.hexdigest().upper()==manifest["concat_sha256"]
        assert len(identities)==3270 and len({x[0] for x in identities})==3270
        if correspondence is None:correspondence=identities
        else:assert correspondence==identities
        correct=sum(matrix[n][n] for n in range(2))
        official=worker["official_results"]["boolq"]["results"]["boolq"]["acc,none"]
        assert correct==original_accuracy_sum and math.isclose(correct/3270,official,abs_tol=1e-12)
        record=dict(arm=arm,worker_path=str(worker_path.relative_to(ROOT)),
            worker_sha256=sha(worker_path.read_bytes()),root_closed_ref=str((directory/"root_closed_ref.json").relative_to(ROOT)),
            root_closed_sha256=sha((directory/"root_closed_ref.json").read_bytes()),
            raw_manifest_concat_sha256=manifest["concat_sha256"],rows=3270,
            gold_labels={str(k):v for k,v in labels.items()},choices=["no","yes"],
            confusion_rows_gold_cols_prediction=matrix,
            no_predictions=matrix[0][0]+matrix[1][0],yes_predictions=matrix[0][1]+matrix[1][1],
            tie_rows=ties,correct=correct,official_accuracy=official,
            recall_gold_no=matrix[0][0]/labels[0],recall_gold_yes=matrix[1][1]/labels[1])
        rows_out.append(record)
    result=dict(schema="TINYLM_BOOLQ_POSTHOC_SELECTION_READBACK_V1",
        recorded_at=datetime.now(timezone.utc).isoformat(),models=rows_out,
        correspondence_identical=True,new_model_or_gpu_calls=0,checkpoint_or_train_writes=0,
        benchmark_answers_used_for_training=False,official_scores_changed=False,
        calibration_or_label_flips_applied=False,new_significance_tests=0,
        interpretation="Descriptive label asymmetry, not a causal diagnosis or a replacement benchmark score.")
    with output.open("x",encoding="utf-8") as f:
        json.dump(result,f,ensure_ascii=False,indent=2);f.write(chr(10))
    print(json.dumps(rows_out,ensure_ascii=False))

if __name__=="__main__":
    main()

