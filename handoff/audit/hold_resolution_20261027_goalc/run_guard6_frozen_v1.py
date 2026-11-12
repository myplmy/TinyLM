"""Run an exact registered CPU audit under the cumulative guard6 preflight."""
from pathlib import Path
import argparse
import hashlib
import json
import runpy
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path[:0] = [str(AUDIT), str(ROOT)]
import active_guard_v6_preflight_v1 as guard

parser = argparse.ArgumentParser()
parser.add_argument('--script', required=True)
parser.add_argument('--receipt-name', required=True)
parser.add_argument('script_args', nargs=argparse.REMAINDER)
args = parser.parse_args()
registry_path = AUDIT/'GUARD6_FROZEN_CPU_ENTRYPOINTS_V1.json'
registry = json.loads(registry_path.read_bytes())
assert args.script in registry['entrypoints']
assert Path(args.script).name == args.script
script = AUDIT/args.script
assert not script.is_symlink()
assert guard.inv.file_sha(script) == registry['entrypoints'][args.script]
out = AUDIT/args.receipt_name
assert out.parent == AUDIT and out.suffix == '.json' and not out.exists()
guard.install_for_legacy()
rest = args.script_args[1:] if args.script_args[:1] == ['--'] else args.script_args
pins = {str(p.relative_to(ROOT)):guard.inv.file_sha(p) for p in
    [script, registry_path, Path(__file__), guard.CONTRACT, AUDIT/'active_guard_v6_preflight_v1.py']}
if '--config' in rest:
    config = Path(rest[rest.index('--config')+1]).resolve()
    assert config.parent == AUDIT and not config.is_symlink()
    pins[str(config.relative_to(ROOT))] = guard.inv.file_sha(config)
sys.argv = [str(script)] + rest
runpy.run_path(str(script), run_name='__main__')
guard.assert_no_protected_opens()
receipt = dict(status='FROZEN_CPU_ENTRYPOINT_COMPLETED_UNDER_CUMULATIVE_GUARD6',
    entrypoint=args.script, arguments=rest, active_guard_sha256=guard.EXPECTED,
    protected_payload_open_attempts=0, inherited_guard_pins_are_preserved_provenance=True,
    input_pins=pins, goal_complete=False, training_authorized=False)
guard.inv.write_json(out, receipt)
print(json.dumps(dict(guard6_entrypoint=args.script, protected_payload_open_attempts=0)))
