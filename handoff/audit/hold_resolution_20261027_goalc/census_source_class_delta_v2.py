"""Guard6 census of remaining HOLD sources, including previously terminal CPU rows."""
from pathlib import Path
import json
import sys

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import active_guard_v6_preflight_v1 as guard

guard.install_for_legacy()
config_path=Path(sys.argv[sys.argv.index('--config')+1]).resolve()
assert config_path.parent==AUDIT and not config_path.is_symlink()
config=json.loads(config_path.read_bytes())
assert config['allow_remaining_previously_terminal'] is True
frozen=AUDIT/'census_source_class_delta_v1.py'
assert guard.inv.file_sha(frozen)=='BC629B3A0E33FC0F5D2C4ABEA975984D3BC7BC0E0B7F93238788D4B666D4E30E'
code=frozen.read_text(encoding='utf-8')
before="eligible=before['decision']=='PENDING' and after['decision'] in {'KEEP','EDIT'} and all(guards.values())"
after="eligible=before['decision'] in {'PENDING','KEEP','EDIT'} and after['decision'] in {'KEEP','EDIT'} and all(guards.values())"
assert code.count(before)==1
code=code.replace(before,after)
before="pins[str(Path(__file__).relative_to(ROOT))]=inv.file_sha(Path(__file__))"
assert code.count(before)==1
code=code.replace(before,before+chr(10)+"    pins[str(FROZEN_PATH.relative_to(ROOT))]=inv.file_sha(FROZEN_PATH)")
exec(compile(code,str(frozen),'exec'),dict(__name__='__main__',__file__=str(Path(__file__)),FROZEN_PATH=frozen))
guard.assert_no_protected_opens()
