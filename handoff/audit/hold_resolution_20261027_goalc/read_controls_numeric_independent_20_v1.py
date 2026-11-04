from pathlib import Path
import hashlib, importlib.util
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
path = HERE / 'field_scoped_packet_entry_v1.py'
assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == '53C408863DCF2474BD9825DE23EA15D765DCC0F6EDC356CD5767E5C59A18F8CE'
spec = importlib.util.spec_from_file_location('pinned_independent_entry', path)
entry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(entry)
entry.cli(ROOT, 'context_controls', {'path': 'handoff/audit/hold_resolution_20261027_goalc/SCOPED_CONTROLS_NUMERIC_INDEPENDENT_20_CONFIG_V1.json', 'sha256': 'CA7DB5A9C36B60EE4526D7B5FC5315C584979F0536A8A374005B2E4049894181'})
