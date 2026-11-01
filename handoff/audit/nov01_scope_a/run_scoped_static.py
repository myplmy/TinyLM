"""Run only the six explicitly registered original CPU collectors."""
from pathlib import Path
import hashlib
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
version = sys.argv[1] if len(sys.argv) == 2 else 'v1'
if re.fullmatch('v[1-9][0-9]*', version) is None:
    raise ValueError('one explicit receipt version required')
manifest = BASE / ('OWNED_INPUTS_' + version + '.json')
env = dict(os.environ, TL_VALIDATION_SCOPE=str(manifest),
           TL_VALIDATION_SCOPE_SHA256=hashlib.sha256(manifest.read_bytes()).hexdigest().upper())
command = [sys.executable, '-B', '-X', 'utf8', 'scripts/check_static_all.py',
           '--profile', 'codex-safe', '--quiet', '--wip', 'handoff/WIP_20261022_작업원장.md',
           '--json', 'handoff/audit/nov01_scope_a/OWNED_STATIC_' + version + '.json']
with (BASE / ('OWNED_STATIC_' + version + '.log')).open('x', encoding='utf-8') as stream:
    result = subprocess.run(command, cwd=ROOT, env=env, stdout=stream,
                            stderr=subprocess.STDOUT, timeout=180)
print('OWN_SCOPED actual returncode:', result.returncode)
raise SystemExit(result.returncode)
