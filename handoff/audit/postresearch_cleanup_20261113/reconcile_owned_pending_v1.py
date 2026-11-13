"""Compare independent Git pending names against owned research and foreign exclusions."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
OWN_PREFIXES = (
    'handoff/audit/postresearch_cleanup_20261113/',
    'handoff/audit/nov05_gsq_objective/', 'handoff/audit/nov05_native_scale/',
    'handoff/audit/nov13_gsq_coordinates/',
    'test_result/evidence/p106b_completeness_v1_20261105/',
    'test_result/evidence/p106b_gsq_objective_v1_20261105/',
    'test_result/evidence/p106b_qwen35_extra_official_v1_20261113/',
    'test_result/evidence/p108_native_v1_20261105/',
    'test_result/evidence/p108_wsp_attn_v1_20261105/',
    'test_result/evidence/p108_wsp_headscan_v1_20261105/',
    'test_result/evidence/p108_wsp_headscan_v2_20261105/',
    'test_result/evidence/p108_wsp_headscan_v3_20261105/',
    'test_result/evidence/p108_wsp_partial_v1_20261105/',
)
OWN_EXACT = {
    'scripts/diag_p106b_gsq_cost_readback.py',
    'test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md',
    'test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md',
    'handoff/audit/isolated_checkpoint_cleanup/nov13_postresearch_preview_v1.json',
    'handoff/audit/isolated_checkpoint_cleanup/nov13_postresearch_preview_v2.json',
}
OWN_EXACT.update(json.loads((OUT / 'COMMIT_INVENTORY_v1.json').read_text())['paths'])
OWN_EXACT.update(json.loads((OUT / 'COMMIT_METADATA_INVENTORY_v1.json').read_text())['paths'])
EXCLUDE = (
    'datasets/TinyDataset', 'HF', 'data_cache', 'runs', 'smoketest_logs',
    'handoff/audit/hold_resolution_20261027_goalc', 'handoff/audit/hold_recovery_20261026_goalc',
    'handoff/audit/source_cleanup_20261026_goalc', 'scripts/p106b_hold_resolution*',
    'handoff/WIP_20261027_작업원장.md',
)
raw = subprocess.check_output(['git','status','--porcelain=v1','-z','--untracked-files=all',
    '--no-renames','--','.']+[':(exclude)'+p for p in EXCLUDE], cwd=ROOT)
references = '\n'.join((ROOT / name).read_text() for name in (
    'handoff/audit/nov13_value_edit/RESULT_CLOSURE_v3.json',
    'handoff/audit/postresearch_cleanup_20261113/LAUNCHER_FULLTEXT_v1.json',
    'handoff/audit/postresearch_cleanup_20261113/OLD_QUEUE_LAUNCHER_PLAN_v2.json',
    'test_result/092_20260925_P100-정성한계-P101A-M0-이식문턱실패.md',
    'test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md',
    'test_result/108_20261104190525_P108-방향수리는-실행됐지만-정답은-늘지-않았다.md'))
owned, foreign, derived, locks, unknown = [], [], [], [], []
for entry in raw.split(b'\0'):
    if not entry:
        continue
    item = entry.decode()
    name = item[3:]
    if name == 'scripts/flag_whitelist.tsv' or name.startswith((
            'agents/', 'data/p106b_hold_resolution_v1_20261027_goalc/')) or name == (
            'review_request/20261113_HOLD_출생연도충돌과화학표기_원문확인요청.md'):
        foreign.append(name)
        continue
    if name.startswith(('handoff/audit/FRONTIER_QUEUE_', 'handoff/audit/FRONTIER_SEMANTIC_')):
        derived.append(name)
        continue
    raw_log = bool(re.fullmatch(r'test_result/(092|101|108)_log_202611(05|13)_.+\.txt', name))
    is_owned = name in OWN_EXACT or name.startswith(OWN_PREFIXES)
    if raw_log:
        assert Path(name).name in references, name
        is_owned = True
    if not is_owned:
        unknown.append(name)
        continue
    path = ROOT / name
    if path.suffix == '.lock':
        assert path.is_file() and path.stat().st_size == 0, name
        locks.append(name)
        continue
    assert path.is_file() and not path.is_symlink(), name
    data = path.read_bytes()
    assert len(data) < 20_000_000, name
    assert path.suffix not in ('.pt','.npy','.bin','.safetensors'), name
    owned.append(dict(path=name,status=item[:2],bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest().upper(),raw_log=raw_log))
assert not unknown, unknown
value = dict(schema='NOV13_INDEPENDENT_PENDING_RECONCILIATION_V1', owned_pending=owned,
    foreign_preserved_count=len(foreign), foreign_groups=dict(Counter('/'.join(x.split('/')[:2]) for x in foreign)),
    local_derived_preserved=derived, runtime_locks_preserved=locks, unclassified=unknown,
    note='Independent pending census, not reused static-input ownership. Raw logs require their basename in closed raw manifest, command archive, or owned results. Foreign text and runtime locks are not staged.')
with (OUT / 'OWN_PENDING_RECONCILIATION_v1.json').open('x',encoding='utf-8') as stream:
    json.dump(value,stream,ensure_ascii=False,indent=2)
    stream.write('\n')
print(json.dumps(dict(owned_pending=len(owned),raw_logs=sum(r['raw_log'] for r in owned),
    bytes=sum(r['bytes'] for r in owned),foreign_preserved=len(foreign),derived=len(derived),locks=len(locks),unclassified=0)))
