"""Validate a uniquely described closing quote without executing the call."""
from pathlib import Path
import ast
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

path=inv.BASE/'remaining_literal_full_counter_v1/inputs/expanded_train_523834_original.txt'
text=path.read_text(encoding='utf-8')
lines=[line for line in text.splitlines() if line.startswith('>>> import subprocess >>> subprocess.call(')]
assert len(lines)==1
assert 'a text string enclosed in double quotes, which is itself enclosed in single quotes' in text
before=lines[0].split('>>> ',2)[2]
assert before.startswith('subprocess.call(') and before.endswith(chr(34)+'])')
try:
    ast.parse(before)
except SyntaxError:
    failed=True
else:
    failed=False
assert failed
after=before[:-2]+chr(39)+before[-2:]
node=ast.parse(after).body[0].value
assert isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
assert node.func.value.id=='subprocess' and node.func.attr=='call'
args=ast.literal_eval(node.args[0])
assert args==['espeak',chr(34)+'Hello World!'+chr(34)]
assert len(after)==len(before)+1
output=AUDIT/'LOCAL_523834_QUOTE_RECOVERY_EVIDENCE_V1.json'
assert not output.exists()
inv.write_json(output,dict(status='EXACT_LOCAL_QUOTE_SYNTAX_EVIDENCE_NOT_EXECUTION',
    original=dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path)),
    original_call_static_syntax_valid=False,recovered_call_static_syntax_valid=True,
    sole_nonwhitespace_change='one closing single quote before the existing closing list bracket',
    exact_argument_values_preserved=args,independent_local_prose_describes_both_quote_layers=True,
    cleaned_corpus_file_written=False,subprocess_example_executed=False,
    producer_sha256=inv.file_sha(Path(__file__)),goal_complete=False,training_authorized=False))
print(json.dumps(dict(original_static_valid=False,recovered_static_valid=True,added_quote=1,example_executed=False)))
