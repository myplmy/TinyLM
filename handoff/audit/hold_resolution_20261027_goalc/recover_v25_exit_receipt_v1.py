"""Recover an actual tool response, never infer process exit from artifacts."""
from pathlib import Path
import datetime
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

AUDIT = Path(__file__).resolve().parent
SESSION = Path('/mnt/c/Users/Uranus/.codex/sessions/2026/10/26/rollout-2026-10-26T17-08-28-01a17740-f435-7243-874c-2b5d58181c4c.jsonl')
CALL = 'call_bbb152dd05c64700b926e9e9d01c5147'
evidence_path = AUDIT / 'DRAFT_V25_ACTUAL_TOOL_RESULT_V1.json'
receipt_path = AUDIT / 'DRAFT_V25_PROCESS_EXIT_V1.json'
inv.require(not evidence_path.exists() and not receipt_path.exists(), 'preserve prior receipts')
matching = []
with SESSION.open(encoding='utf-8') as stream:
    for line in stream:
        item = json.loads(line)
        payload = item.get('payload', {})
        if (item.get('type') == 'response_item' and payload.get('call_id') == CALL
                and payload.get('type') in {'custom_tool_call', 'custom_tool_call_output'}):
            matching.append(item)
inv.require(len(matching) == 2, 'actual call/response pair is not unique')
call, response = matching
inv.require(call['payload']['type'] == 'custom_tool_call'
            and response['payload']['type'] == 'custom_tool_call_output', 'wrong response order')
first_statement = 'text(await tools.write_stdin({session_id:46878,chars:"",yield_time_ms:1000,max_output_tokens:1200}));'
inv.require(call['payload']['name'] == 'exec'
            and call['payload']['input'].startswith(first_statement), 'actual producer poll does not match')
blocks = response['payload']['output']
inv.require(blocks[0]['text'].startswith('Script completed'), 'outer tool did not complete')
actual = json.loads(blocks[1]['text'])
inv.require(actual['chunk_id'] == '2fcca8' and actual['exit_code'] == 0
            and 'session_id' not in actual and actual['output'] == '', 'actual terminal producer result differs')
evidence = dict(status='RECOVERED_ACTUAL_WRITE_STDIN_RESPONSE_AFTER_COMPACTION',
    source_session=str(SESSION), source_session_id='01a17740-f435-7243-874c-2b5d58181c4c',
    call_id=CALL, call_ordinal=call['ordinal'], response_ordinal=response['ordinal'],
    call_timestamp=call['timestamp'], response_timestamp=response['timestamp'],
    first_statement=first_statement,
    full_call_input_sha256=hashlib.sha256(call['payload']['input'].encode()).hexdigest().upper(),
    actual_write_stdin_result=actual,
    recovered_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    recovery_code_sha256=inv.file_sha(Path(__file__)),
    subsequent_unknown_session_is_not_a_producer_failure=True)
inv.write_json(evidence_path, evidence)
complete = inv.BASE / 'draft_proposals_v25/complete.json'
inv.require(complete.is_file(), 'the verified completed draft is absent')
receipt = dict(tool_session=46878, process_exit_code=0,
    observation_method='ACTUAL_EXIT_ZERO_FROM_WRITE_STDIN',
    observed_at=response['timestamp'], actual_tool_chunk_id=actual['chunk_id'],
    recovered_from_preserved_own_session_response=True,
    exact_response_evidence=dict(path=str(evidence_path.relative_to(ROOT)), sha256=inv.file_sha(evidence_path)),
    completed_artifact_sha256=inv.file_sha(complete),
    status='ACTUAL_PRODUCER_EXIT_OBSERVED_ARTIFACT_VERIFICATION_STILL_REQUIRED')
inv.write_json(receipt_path, receipt)
print(json.dumps(receipt, ensure_ascii=False))
