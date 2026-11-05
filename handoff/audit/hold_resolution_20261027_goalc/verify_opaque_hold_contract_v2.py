"""Apply the separate parent-position verifier to an exact versioned config."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(AUDIT))
from active_guard_v4_preflight_v1 import activate, assert_no_protected_opens
activate()
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--config', type=Path, required=True)
p.add_argument('--expected-config-sha', required=True)
p.add_argument('--expected-contract-sha', required=True)
args = p.parse_args()
config_path = args.config.resolve()
assert config_path.is_relative_to(AUDIT) and not config_path.is_symlink()
raw = config_path.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == args.expected_config_sha
c = json.loads(raw)
for name, digest in c['input_pins'].items():
    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest().upper() == digest
frozen = AUDIT/'verify_opaque_hold_contract_v1.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '8A80190B44824A65767BC968F43BF59DCEF59876D0E8AE01DA5E6B5251B9779F'
code = raw.decode('utf-8')
changes = [
    ('OPAQUE_HOLD_ROOT28_ROSTER20_CONTRACT_V1.json', c['output']),
    ('3F0E1828F8637C34F0303149D409813F0929F3A848541C5C68BD1646294A7EBA', args.expected_contract_sha),
    ('len(hashes) == 68134', 'len(hashes) == '+str(c['expected_HOLD_unique'])),
    ("counts['positions'] == 106236", "counts['positions'] == "+str(c['expected_HOLD_positions'])),
    ("counts['input_ids'] == 189933477", "counts['input_ids'] == "+str(c['expected_HOLD_input_ids'])),
    ('OPAQUE_HOLD_ROOT28_ROSTER20_INDEPENDENT_VERIFIED_V1.json', c['output'].replace('CONTRACT', 'INDEPENDENT_VERIFIED'))]
for old, new in changes:
    assert code.count(old) == 1
    code = code.replace(old, new)
anchor = 'result = dict(status='
assert code.count(anchor) == 1
code = code.replace(anchor, 'assert_no_protected_opens()' + chr(10) + anchor)
anchor = '[contract_path, parent_path, AUDIT/'
assert code.count(anchor) == 1
code = code.replace(anchor, '[CONFIG_PATH,FROZEN_PATH,contract_path, parent_path, AUDIT/')
exec(compile(code, str(frozen), 'exec'), dict(__name__='versioned_opaque_independent_actual_run',
    __file__=str(Path(__file__)),CONFIG_PATH=config_path,FROZEN_PATH=frozen,
    assert_no_protected_opens=assert_no_protected_opens))
assert_no_protected_opens()
