"""Read back every new source/body pair and expose semantic guards for root review."""
from collections import Counter
from pathlib import Path
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v26 as policy
from scripts import p106b_hold_resolution_literal_guard_v2 as literal

snapshot_path = AUDIT / 'supplemental_candidates_snapshot_v56.json'
out = AUDIT / 'POST_SEMANTIC_BODY_AUDIT_V1.json'
inv.require(not out.exists(), 'new immutable body readback receipt required')
snapshot = inv.cache.read(snapshot_path)
groups = {'post_body_guard_counter_v1':14, 'semantic_field_counter_v1':12}
restricted = {'expanded_train:' + str(n) for n in [14760,756966,15695,1216576,1250821,20624,6030]}
numeric = re.compile(r'(?<![A-Za-z0-9_])[-+−]?[0-9]+(?:[.,][0-9]+)*(?:%|°[CF])?')
lexical = re.compile(r'[A-Za-z0-9_]+|[가-힣]+|[\u3400-\u9fff]+')
cases = literal.load_registry()
records, counts, pins = [], Counter(), {}
started = time.monotonic()


def pin(name, expected=None):
    digest = inv.file_sha(ROOT / name)
    inv.require(expected is None or digest == expected, 'pinned artifact changed: ' + name)
    if name in pins:
        inv.require(pins[name] == digest, 'artifact changed during readback')
    pins[name] = digest
    return digest


for row in snapshot['records']:
    if row['cohort'] not in groups:
        continue
    ident = row['id']
    inv.require(ident not in restricted, 'restricted parent must remain metadata-only')
    counts['review_rows'] += 1
    record = {key:row[key] for key in ['id','cohort','role','decision','status','original','review']}
    pin(row['review']['path'], row['review']['sha256'])
    if not row.get('body') or row['status'] == 'MECHANICAL_REJECTION_NOT_APPLIED':
        record['not_materialized_reason'] = row.get('error', row['decision'])
        counts['not_materialized'] += 1
        records.append(record)
        continue
    original_pin = row['original']
    pin(original_pin['path'], original_pin['sha256'])
    pin(row['body'], row['clean_text_sha256'])
    raw = (ROOT / original_pin['path']).read_text(encoding='utf-8')
    clean = (ROOT / row['body']).read_text(encoding='utf-8')
    inv.require(inv.sha(raw) == original_pin['sha256'] and inv.sha(clean) == row['clean_text_sha256'],
                'UTF-8 source or body identity changed')
    post = policy.propose(dict(id=ident, text=clean, complete_eos=True, valid_utf8=True), False)
    code = policy.code_preserved(raw, clean)
    exact_literal = not code and literal.exact_pair_preserved(raw, clean, ident, cases)
    introduced_numeric = dict(Counter(numeric.findall(clean)) - Counter(numeric.findall(raw)))
    introduced_lexical = dict(Counter(lexical.findall(clean)) - Counter(lexical.findall(raw)))
    memo_added = bool(inv.corpus.MEMOS.search(clean) and not inv.corpus.MEMOS.search(raw))
    checks = dict(code=code, unicode=policy.unicode_examples_preserved(raw, clean),
        style=policy.semantic_style_preserved(raw, clean), ordered=policy.ordered_deletion(raw, clean))
    record.update(body=row['body'], clean_text_sha256=row['clean_text_sha256'],
        source_characters=len(raw), clean_characters=len(clean), unchanged=raw == clean,
        guards=checks, exact_previously_reviewed_literal=exact_literal,
        introduced_numeric_occurrences=introduced_numeric, introduced_lexical_occurrences=introduced_lexical,
        newly_added_editor_memo=memo_added, post_policy_decision=post['decision'],
        post_policy_reasons=post['reasons'], post_policy_would_edit=post.get('candidate',post['text']) != clean,
        root_approved=False, cache_admitted=False)
    counts['bodies_read_back'] += 1
    counts['unchanged'] += raw == clean
    for label, passed in checks.items():
        counts[label + '_flag'] += not passed
    counts['numeric_flag'] += bool(introduced_numeric)
    counts['memo_flag'] += memo_added
    counts['post_pending'] += post['decision'] == 'PENDING'
    counts['post_would_edit'] += record['post_policy_would_edit']
    # Pin each actual sidecar named by this exact row, without following other
    # roles or paths mentioned only inside a quoted source document.
    directory = inv.BASE / 'agents' / row['role'] / row['cohort']
    refs = re.findall(r'(?<![A-Za-z0-9_])(?:hold_[A-Za-z0-9_]+|removal_basis_[A-Za-z0-9_]+|expanded_train_[0-9]+_(?:hold|original_note)_v[0-9]+)[.]md', row['review_text'])
    record['sidecar_pins'] = []
    for name in sorted(set(refs)):
        sidecar = directory / name
        inv.require(sidecar.is_file(), 'declared sidecar is missing: ' + str(sidecar))
        relative = str(sidecar.relative_to(ROOT))
        record['sidecar_pins'].append(dict(path=relative,sha256=pin(relative)))
    records.append(record)

for group, expected in groups.items():
    coverage = snapshot['coverage'][group]
    inv.require(coverage['expected'] == expected, 'new cohort source count changed')
    inv.require(sum(row['cohort'] == group for row in records) == coverage['saved'], 'saved row conservation differs')
for name, digest in list(pins.items()):
    pin(name, digest)
pin(str(snapshot_path.relative_to(ROOT)))
pin(str(Path(__file__).relative_to(ROOT)))
result = dict(status='NEW_COHORT_FULL_BODY_READBACK_FLAGS_REQUIRE_ROOT_NOT_ADMISSION',
    counts=dict(counts), records=records, coverage={group:snapshot['coverage'][group] for group in groups},
    input_pins=pins, source_files_stable=True, restricted_parent_content_opened=False,
    root_approved=False, cache_admitted=0, goal_complete=False, training_authorized=False,
    seconds=time.monotonic()-started)
inv.require(len(json.dumps(result,ensure_ascii=False).encode()) < 20_000_000, 'receipt needs explicit ordered shards')
inv.write_json(out,result)
print(json.dumps({key:result[key] for key in ['status','counts','coverage','seconds']},ensure_ascii=False))
