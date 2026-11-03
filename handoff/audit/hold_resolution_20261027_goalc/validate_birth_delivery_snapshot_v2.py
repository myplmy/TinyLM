"""Reuse the strict validator with immutable copies of the verified event prefixes."""
from pathlib import Path
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
from snapshot_birth_delivery_events_v1 import archive_event_prefixes

frozen = AUDIT / 'validate_birth_delivery_snapshot_v1.py'
code = frozen.read_text(encoding='utf-8')
anchor = '    target.mkdir(parents=True)'
assert code.count(anchor) == 1
code = code.replace(anchor, anchor + chr(10) +
    '    event_pins = archive_event_prefixes(ROOT, target, event_pins, guard)')
anchor = 'validator=pin(Path(__file__).resolve()), expected=len(sources),'
assert code.count(anchor) == 1
code = code.replace(anchor, 'validator=pin(Path(__file__).resolve()),' + chr(10) +
    "                  validator_base=pin(AUDIT / 'validate_birth_delivery_snapshot_v1.py')," + chr(10) +
    "                  event_archiver=pin(AUDIT / 'snapshot_birth_delivery_events_v1.py'), expected=len(sources),")
exec(compile(code, str(frozen), 'exec'), globals())
