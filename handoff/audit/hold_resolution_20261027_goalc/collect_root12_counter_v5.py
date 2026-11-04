"""Reuse strict counter4 with current guard4 before any cohort payload access."""
from pathlib import Path
import hashlib
import sys
from unittest.mock import patch

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
from active_guard_v4_preflight_v1 import activate, assert_no_protected_opens

activate()
frozen = AUDIT/'collect_root12_counter_v4.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == '09D1212DEE172B5E3DA6B9381E03793CA202157B6607B87CB652B99FFB101CDC'
original_read = Path.read_text
core = AUDIT/'collect_root12_counter_v1.py'


def current_core(path, *args, **kwargs):
    code = original_read(path, *args, **kwargs)
    if path.resolve() != core:
        return code
    replacements = {
        "guard_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json'":
            "from active_guard_v4_preflight_v1 import assert_no_protected_opens, attempted_payload_opens\nguard_path=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V4.json'",
        '7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306':
            '59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D',
        'assert not attempted_unreviewed': 'assert_no_protected_opens()\nassert not attempted_unreviewed',
        '    full_source_scope_is_owned_by_manifest=True,new_first_review_credit=0,':
            "    active_guard_sha256='59CA9419990CD1D6968EA9B1E7EF4416D418C8C460EDD8074E98DA9BF5FCEF7D',\n    protected_payload_open_attempts=attempted_payload_opens(),\n    full_source_scope_is_owned_by_manifest=True,new_first_review_credit=0,",
        'for path in [manifest_path,guard_path,reused,Path(__file__),':
            "for path in [AUDIT/'active_guard_v4_preflight_v1.py',AUDIT/'guarded_reviewed_cache_v6.py',manifest_path,guard_path,reused,Path(__file__),"}
    for before, after in replacements.items():
        assert code.count(before) == 1, before
        code = code.replace(before, after)
    return code


with patch.object(Path, 'read_text', current_core):
    exec(compile(raw, str(frozen), 'exec'), dict(__name__='current_guard4_counter_actual_run',
        __file__=str(Path(__file__))))
assert_no_protected_opens()
