"""Reuse every actual-cache guard check for one exact versioned metadata delta."""
from pathlib import Path
import argparse
import hashlib
import json

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    path = args.config.resolve()
    assert path.parent == AUDIT and not path.is_symlink()
    case = json.loads(path.read_bytes())
    for name, sha in case['input_pins'].items():
        target = ROOT / name
        assert not target.is_symlink() and hashlib.sha256(target.read_bytes()).hexdigest().upper() == sha
    frozen = AUDIT / 'preflight_root39_actual_cache_guards_v1.py'
    raw = frozen.read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == 'D04EC62F9260088BCB2D412E7ADAAF4852EAF6F8B0EA9CFCC1276DCF5780045D'
    code = raw.decode('utf-8')
    replacements = [
        ("output=AUDIT/'CACHE17_ROOT39_ACTUAL_DELTA_GUARDS_PREFLIGHT_V1.json'", 'output=AUDIT/' + repr(case['output'])),
        ("prior_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V29.json'", 'prior_path=ROOT/' + repr(case['prior_selection']['path'])),
        ("current_path=AUDIT/'ROOT_AUTHORED_SELECTIONS_V39.json'", 'current_path=ROOT/' + repr(case['selection']['path'])),
        ("prior=store.read(prior_path,'CD799C190B8BAED74DC210A441FB64420E311AA836771521B309808A12461B7B')",
         'prior=store.read(prior_path,' + repr(case['prior_selection']['sha256']) + ')'),
        ("current=store.read(current_path,'C4BA3D979C76082D9E59EA1BE6357C2AF6EAFB342C2EC1E06C2A25336FA01F84')",
         'current=store.read(current_path,' + repr(case['selection']['sha256']) + ')'),
        ('len(delta)==2551', 'len(delta)==' + str(case['expected_unique'])),
        ("roster_path=inv.BASE/'roster_reviewed_partial_v29/complete.json'", 'roster_path=ROOT/' + repr(case['roster']['path'])),
        ("inv.file_sha(roster_path)=='7A12C8FA95C9F241EFEFF479260A53679B1FF30A6368978D4482D49437A16B4C'",
         'inv.file_sha(roster_path)==' + repr(case['roster']['sha256'])),
        ("config=inv.cache.read(AUDIT/'CACHE16_ROOT39_ROSTER29_CONFIG_V1.json')", 'config=CASE'),
        ("old_fail==['expanded_train:12122'] and not new_fail", "old_fail==CASE['expected_prior_guard_rejections'] and not new_fail"),
    ]
    for before, after in replacements:
        assert code.count(before) == 1, before
        code = code.replace(before, after)
    exec(compile(code, str(frozen), 'exec'), dict(__name__='__main__', __file__=str(Path(__file__)), CASE=case))
    output = AUDIT / case['output']
    proof = json.loads(output.read_bytes())
    assert proof['status'] == 'ACTUAL_CACHE_DELTA_GUARDS_PASS'
    assert proof['compared_unique_sources'] == case['expected_unique']
    binding = AUDIT / case['binding_output']
    assert not binding.exists()
    result = dict(status='EXACT_VERSIONED_ACTUAL_CACHE_GUARD_PREFLIGHT_BOUND',
        proof=dict(path=str(output.relative_to(ROOT)), sha256=hashlib.sha256(output.read_bytes()).hexdigest().upper()),
        input_pins={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest().upper()
                    for p in [path, Path(__file__), frozen]},
        additional_full_index_or_model_constructed=False, protected_payload_open_attempts=0,
        goal_complete=False, training_authorized=False)
    with binding.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
