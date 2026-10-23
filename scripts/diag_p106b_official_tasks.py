#!/usr/bin/env python3
"""CPU official task/prompt/metric contract; no model/backend or installation."""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))


def main():
    for name in ('HF_HUB_OFFLINE','HF_DATASETS_OFFLINE','TRANSFORMERS_OFFLINE'):
        os.environ[name]='1'
    from scripts.p106b_official_tasks import contract_report
    from scripts.prepare_p106b_official_eval import write_report
    output=ROOT/'test_result/evidence/p106b_official_task_cpu_v1'
    if output.exists():raise FileExistsError('previous CPU contract preserved')
    output.mkdir(parents=True,exist_ok=False)
    started=datetime.now(timezone.utc).isoformat();tick=time.monotonic()
    report=dict(status='STARTED',model_loads=0,installs=0)
    try:
        report=contract_report()
    except BaseException as exc:
        report.update(status='OFFICIAL_TASK_CONTRACT_ERROR',error_type=type(exc).__name__,error=str(exc)[:2000])
        raise
    finally:
        report.update(started_at=started,ended_at=datetime.now(timezone.utc).isoformat(),wall_seconds=time.monotonic()-tick)
        write_report(output/'report.json',report)
    print(json.dumps(dict(status=report['status'],tasks=len(report['tasks']),
                         rows=sum(x['rows'] for x in report['tasks']),models=0,
                         report=str(output/'report.json')),ensure_ascii=False))


if __name__=='__main__':main()
