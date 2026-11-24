#!/usr/bin/env python3
"""Reopen an original/frozen edited model without repeating any edit fitting.

--check-only is CPU-only. --verify uses the existing evaluation environment,
exactly replays68 saved answers, optionally answers supplied questions, then
rolls back RAM weights. It never writes a model checkpoint or trains a model.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p108_frozen_edit_official as driver


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check-only', action='store_true')
    group.add_argument('--verify', action='store_true')
    parser.add_argument('--arm', choices=driver.ARMS, required=True)
    parser.add_argument('--source-sha256')
    parser.add_argument('--receipt-dir')
    parser.add_argument('--question', action='append', default=[])
    args = parser.parse_args()
    signature = driver.identity()
    frozen, packets, expected = driver.bundle()
    if args.check_only:
        print(json.dumps(dict(status='FROZEN_CPU_CHECK_NO_MODEL', arm=args.arm,
            source_sha256=signature['sha256'], packet_count=len(packets), model_load=False, gpu=False)))
        return
    if args.source_sha256 != signature['sha256'] or not args.receipt_dir:
        parser.error('explicit current source SHA and fresh handoff/audit receipt directory required')
    target = (ROOT/args.receipt_dir).resolve()
    if not target.is_relative_to(ROOT/'handoff/audit') or target.exists():
        parser.error('fresh receipt directory must be under handoff/audit; no overwrite')
    target.mkdir(parents=True)
    result = dict(arm=args.arm, source_identity=signature, cli_sha256=driver.official.digest(__file__),
        frozen_files=driver.FROZEN, optimizer_updates=0, checkpoint_writes=0,
        started_at=datetime.now(timezone.utc).isoformat(), status='STARTED', answers=[])
    os.environ.update(driver.official.OFFLINE, HF_EVALUATE_OFFLINE='1')
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    configure_hf_cache()
    import torch
    from torch.nn.attention import sdpa_kernel, SDPBackend
    from scripts import interactive_research_infer as manual
    try:
        with sdpa_kernel(SDPBackend.MATH), torch.no_grad(), \
             driver.model_runtime(args.arm, frozen, packets, expected, target) as (lm, proof):
            result['model_proof'] = proof
            for question in args.question:
                answer, generation = manual.emit(lm.core.score_batch.runtime, question, max_new=64)
                result['answers'].append(dict(question=question, answer=answer, generation=generation))
                print('질문> '+question+'\n답변> '+answer+'\n종료> '+generation['finish_reason'],flush=True)
        result['status'] = 'FROZEN_EDIT_REPLAY_VERIFIED_AND_ORIGINAL_RESTORED'
    except BaseException as exc:
        result.update(status='REPLAY_ERROR', error_type=type(exc).__name__, error=str(exc)[:1600])
        raise
    finally:
        result['sources_unchanged'] = driver.identity()==signature
        driver.suite.write(target/'replay_receipt.json',result)


if __name__ == '__main__':
    main()
