"""Give each exact TASK a short index of its existing, unchanged reading views."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
COHORT = 'root_selected_lexical_counter_v1'
OUT = BASE / COHORT / 'reading_indexes_v2'
inv.require(not OUT.exists(), 'task indexes are write-once')
manifest_path = BASE / COHORT / 'manifest.json'
views_path = BASE / COHORT / 'reading_views_manifest_v1.json'
manifest, views = inv.cache.read(manifest_path), inv.cache.read(views_path)
inv.require(views['source_manifest']['sha256'] == inv.file_sha(manifest_path), 'view assignment changed')
by_id = {row['id']: row for row in views['rows']}
inv.require(len(by_id) == len(views['rows']) == 579, 'view source conservation differs')
planned, role_counts, seen_views = [], {}, {}
for role, assignment in manifest['assignments'].items():
    ids = assignment['ids'] if isinstance(assignment, dict) else assignment
    directory = BASE / 'agents' / role / COHORT
    tasks = sorted(directory.glob('TASK_[0-9][0-9][0-9].md'))
    inv.require(len(tasks) == 32, 'all32 original TASKs must remain assigned')
    union = set()
    for task in tasks:
        assigned = re.findall(r'^## ((?:expanded_train|historical_train|validation):[0-9]+)[ \t]*$',
                              task.read_text(encoding='utf-8'), re.M)
        inv.require(assigned and not (union & set(assigned)) and set(assigned) <= set(ids), 'TASK ID scope differs')
        union.update(assigned)
        lines = ['# ' + task.stem + ' 지정 순서뷰 인덱스',
                 '이 파일은 기존 지정뷰의 경로/범위/SHA만 담는다. 실제 원문이나 새 학습 문서가 아니다.',
                 '지정한 모든 순서뷰와 raw EOF/전체 diff를 확인한다. 출력이 잘리면 완료로 세지 않는다.',
                 '실제 TXT/MD 출력 폴더는 기존 TASK 계약 그대로다. 이 인덱스 폴더는 읽기 전용이다.', '']
        for ident in assigned:
            row = by_id[ident]
            inv.require(row['role'] == role, 'view role differs from its TASK owner')
            lines.append('## ' + ident)
            for label, parts in row['views'].items():
                lines.append(label)
                for part in parts:
                    path = ROOT / part['path']
                    if part['path'] not in seen_views:
                        inv.require(inv.file_sha(path) == part['sha256'], 'existing canonical reading view changed')
                        seen_views[part['path']] = part['sha256']
                    lines.append('- ' + str(path) + ' chars ' + str(part['source_characters']) + ' SHA256 ' + part['sha256'])
            lines.append('')
        payload = (chr(10).join(lines) + chr(10)).encode('utf-8')
        inv.require(len(payload) < 20_000_000, 'index requires splitting')
        planned.append((OUT / role / task.name, payload, dict(role=role, ids=assigned,
            original_task=dict(path=str(task.relative_to(ROOT)), sha256=inv.file_sha(task)))))
    inv.require(union == set(ids), 'role TASKs omit an assigned source')
    role_counts[role] = len(union)
records = []
for path, payload, record in planned:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(payload)
    records.append(dict(record, index=dict(path=str(path.relative_to(ROOT)), sha256=inv.file_sha(path))))
inv.require(sum(role_counts.values()) == 579 and len(seen_views) == 2937, 'full index conservation differs')
result = dict(status='EXACT_TASK_METADATA_INDEXES_NOT_NEW_SOURCE_OR_ADMISSION',
    roles=role_counts, task_indexes=len(records), canonical_view_files_checked=len(seen_views), rows=records,
    source_manifest=dict(path=str(manifest_path.relative_to(ROOT)), sha256=inv.file_sha(manifest_path)),
    view_manifest=dict(path=str(views_path.relative_to(ROOT)), sha256=inv.file_sha(views_path)),
    original_or_candidate_body_changed=False, cache_admitted=0, training_authorized=False)
inv.write_json(OUT / 'manifest.json', result)
print(json.dumps({k: result[k] for k in ['status', 'roles', 'task_indexes', 'canonical_view_files_checked']}, ensure_ascii=False))
