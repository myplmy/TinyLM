"""Validate a pinned explicit code list, never a scripts-directory staging grant."""
from pathlib import Path
import hashlib
import json
import re

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]


def load(config_path):
    config_path=Path(config_path).resolve()
    assert config_path.parent==AUDIT and not config_path.is_symlink()
    config=json.loads(config_path.read_bytes())
    pin=config['owned_code_scope']
    path=ROOT/pin['path']
    assert path.parent==AUDIT and not path.is_symlink()
    assert hashlib.sha256(path.read_bytes()).hexdigest().upper()==pin['sha256']
    registry=json.loads(path.read_bytes())
    rows=registry['rows']
    assert len(rows)==len({row['path'] for row in rows})
    assert set(config['additional_owned_code_paths'])=={row['path'] for row in rows}
    for row in rows:
        name=row['path']
        assert re.fullmatch(r'scripts/(?:test_)?p106b_hold_resolution_[A-Za-z0-9_]+\.py',name)
        item=ROOT/name
        assert item.parent==ROOT/'scripts' and not item.is_symlink()
        raw=item.read_bytes()
        assert len(raw)==row['bytes']<20_000_000
        assert hashlib.sha256(raw).hexdigest().upper()==row['sha256']
    return tuple(sorted(row['path'] for row in rows))


def config_for_version(version):
    assert str(version).isdigit()
    return AUDIT/('EXACT_FOLLOWUP_PROGRESS_SAVE_V'+str(int(version))+'_CONFIG_V1.json')
