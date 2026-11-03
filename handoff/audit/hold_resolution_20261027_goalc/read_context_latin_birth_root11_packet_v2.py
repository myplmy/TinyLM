"""Fixed assigned packet emission and prospective delivery journal."""
from pathlib import Path
import hashlib, importlib.util
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MODULE = HERE / 'birth_input_delivery_guard_v1.py'
EXPECTED = '7C749CD9C89D28BCCD7210148F43BE95ECA54BFCB1306EF94C167D4F87096226'
assert not MODULE.is_symlink() and hashlib.sha256(MODULE.read_bytes()).hexdigest().upper() == EXPECTED
spec = importlib.util.spec_from_file_location('fixed_delivery_reader', MODULE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
guard.cli(ROOT, {'path': 'handoff/audit/hold_resolution_20261027_goalc/BIRTH_INPUT_DELIVERY_CONFIG_V1.json', 'sha256': 'F9D032DD2041EBC689E7326E19AF494DC87AECF89801E449D56AF0FFEFB38CE6'}, EXPECTED, 'context_latin')
