"""Keep frozen roster joins; bound generated version substitutions by digits."""
from pathlib import Path
from unittest.mock import patch
import builtins
import hashlib
import json
import runpy
import sys

AUDIT = Path(__file__).resolve().parent
sys.path[:0] = [str(AUDIT), str(AUDIT.parents[2])]
ANCHOR = 'assert before in code;code=code.replace(before,after)'
REPLACEMENT = "assert re.search(re.escape(before)+r'(?![0-9])',code);code=re.sub(re.escape(before)+r'(?![0-9])',lambda _match:after,code)"


def fixed_generator(source):
    assert source.count(ANCHOR) == 1
    assert source.count('import json') == 1
    return source.replace('import json', 'import json' + chr(10) + 'import re').replace(ANCHOR, REPLACEMENT)


def main():
    import active_guard_v6_preflight_v1 as guard
    guard.install_for_legacy()
    config_path = Path(sys.argv[sys.argv.index('--config') + 1]).resolve()
    config = json.loads(config_path.read_bytes())
    assert config_path.parent == AUDIT and not config_path.is_symlink()
    frozen = AUDIT / 'advance_reviewed_roster_v4.py'
    registry_path = AUDIT / 'GUARD6_FROZEN_CPU_ENTRYPOINTS_V1.json'
    registry = json.loads(registry_path.read_bytes())
    assert guard.inv.file_sha(frozen) == registry['entrypoints'][frozen.name]
    target = AUDIT / 'advance_reviewed_roster_v1.py'
    assert guard.inv.file_sha(target) == 'F20E288A65638A3E6011244B5223AF78D46961838E2ABEDF4E91B6BFA879F868'
    compile_original = builtins.compile
    rewritten = []

    def bounded_compile(source, filename, mode, *args, **kwargs):
        if str(filename) == str(target) and isinstance(source, str) and ANCHOR in source:
            source = fixed_generator(source)
            rewritten.append(hashlib.sha256(source.encode()).hexdigest().upper())
        return compile_original(source, filename, mode, *args, **kwargs)

    with patch.object(builtins, 'compile', bounded_compile):
        runpy.run_path(str(frozen), run_name='__main__')
    assert len(rewritten) == 1
    guard.assert_no_protected_opens()
    receipt = dict(status='FROZEN_ROSTER_JOIN_WITH_DIGIT_BOUNDED_VERSION_GENERATOR_COMPLETED',
        config=dict(path=str(config_path.relative_to(AUDIT.parents[2])), sha256=guard.inv.file_sha(config_path)),
        generated_prefix_sha256=rewritten[0], legacy_files_modified=False, guard_waivers=0,
        protected_payload_open_attempts=0, original_or_candidate_modified=False,
        input_pins={str(p.relative_to(AUDIT.parents[2])): guard.inv.file_sha(p) for p in [
            Path(__file__), frozen, target, registry_path, config_path, guard.CONTRACT,
            AUDIT/'ROSTER_VERSION30_BOUNDARY_FIX_F3_F4_V1.md', AUDIT/'ROSTER_VERSION_BOUNDARY_TESTS_V1.log']},
        goal_complete=False, training_authorized=False)
    out = AUDIT / ('GUARD6_ROOT' + str(config['next_selection']) + '_ROSTER_V' + str(config['next_roster']) + '_V5_BUILD_BINDING_V1.json')
    assert not out.exists()
    guard.inv.write_json(out, receipt)
    print(json.dumps(dict(status=receipt['status'], rewritten_prefixes=1)))


if __name__ == '__main__':
    main()
