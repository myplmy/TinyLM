"""Compare actual scoped stdout in RAM; preserve only a small proof, no corpus copy."""
from pathlib import Path
import hashlib
import json
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT/'handoff/audit/hold_resolution_20261027_goalc'


def run(args):
    started = time.monotonic()
    result = subprocess.run(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return result, time.monotonic()-started


def parse(raw):
    frames = []
    prefix = b'TRUSTED_LOSSLESS_VIEW_V2 '
    while raw.startswith(prefix):
        line, raw = raw.split(b'\n', 1)
        info = json.loads(line[len(prefix):])
        begin = b'SOURCE_DATA_VIEW_BEGIN\n'
        assert raw.startswith(begin)
        raw = raw[len(begin):]
        length = info['range'][1]-info['range'][0]
        text, raw = raw[:length], raw[length:]
        text.decode('utf-8')
        end = b'\nSOURCE_DATA_VIEW_' + (b'EOF' if info['end_of_view'] else b'MORE_PARTS_REMAIN') + b'\n'
        assert raw.startswith(end)
        raw = raw[len(end):]
        frames.append((info, text))
    return frames, raw


rows = []
for short,page,ident in [('c',12,'259740'), ('l',12,'263562'), ('h',16,'445464'),
                         ('j',15,'392325'), ('g',14,'335240')]:
    new,seconds = run(['bash',str(ROOT/f'tmp/hold-{short}-field-lossless-batch-v1'),str(page),ident,'1','3'])
    assert new.returncode == 0, new.stderr.decode()
    frames, tail = parse(new.stdout)
    assert len(frames) == 3 and tail.startswith(b'TRUSTED_LOSSLESS_BATCH_END ')
    footer = json.loads(tail[len(b'TRUSTED_LOSSLESS_BATCH_END '):])
    assert footer['first_part'] == 1 and footer['last_part'] == 3
    assert footer['next_part'] == frames[-1][0]['next_part']
    old_seconds = 0
    for n,(info,text) in enumerate(frames,1):
        old,elapsed = run(['bash',str(ROOT/f'tmp/hold-{short}-field-lossless-v6'),str(page),ident,'pair',str(n)])
        assert old.returncode == 0, old.stderr.decode()
        old_frames, old_tail = parse(old.stdout)
        assert old_frames == [(info,text)] and old_tail == b''
        old_seconds += elapsed
    rows.append(dict(role=frames[0][0]['role'], id=frames[0][0]['source_id'],
                     exact_frames_compared=3, old_process_calls=3, batch_process_calls=1,
                     old_three_calls_seconds=old_seconds, batch_one_call_seconds=seconds,
                     exposed_payload_bytes=sum(len(text) for _,text in frames),
                     sha256=hashlib.sha256(b''.join(text for _,text in frames)).hexdigest().upper()))

rejects = []
for short,page,ident,first,count in [('c',12,'32895','1','3'), ('h',16,'74587','1','3'),
                                   ('j',15,'267902','1','3'), ('c',12,'392325','1','3'),
                                   ('g',14,'335240','1','4')]:
    result,seconds = run(['bash',str(ROOT/f'tmp/hold-{short}-field-lossless-batch-v1'),str(page),ident,first,count])
    assert result.returncode != 0 and not result.stdout
    rejects.append(dict(role_short=short, id='expanded_train:'+ident, count=int(count),
                        rejected_before_stdout=True, exit_code=result.returncode))

result = dict(status='FIVE_ACTUAL_ROLE_BATCHES_EXACT_V6_FRAME_EQUIVALENCE_VERIFIED',
              rows=rows, negative_cases=rejects, payload_copies_written=0,
              old_process_calls=sum(r['old_process_calls'] for r in rows),
              batch_process_calls=len(rows), observed_frames=15,
              timing_limit='Small sequential comparison; not total completion ETA or semantic evidence.',
              root_or_cache_admission=False, goal_complete=False, training_authorized=False)
out = AUDIT/'BATCHED_LOSSLESS_READER_FIVE_ROLE_ACTUAL_VERIFIED_V1.json'
with out.open('xb') as stream:
    stream.write((json.dumps(result,ensure_ascii=False,indent=2)+chr(10)).encode())
print(json.dumps({k:v for k,v in result.items() if k not in {'rows','negative_cases'}},ensure_ascii=False))
print(json.dumps(dict(old_seconds=sum(r['old_three_calls_seconds'] for r in rows),
                     batch_seconds=sum(r['batch_one_call_seconds'] for r in rows)),ensure_ascii=False))
