"""Keep exact supplement1 scope/frames and use the tested compact batch headers."""
from pathlib import Path
import hashlib
import sys

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
old=AUDIT/'exact_supplement_lossless_batch_v1.py'
compact=AUDIT/'batched_lossless_review_entry_v3.py'
assert hashlib.sha256(old.read_bytes()).hexdigest().upper()=='7A1B245027402C635553C8053BB0F9391D9736C4469A7EEFB7093FDADC66EF9A'
assert hashlib.sha256(compact.read_bytes()).hexdigest().upper()=='708CF07D415693F4457BF064D61F23AD4ABE702FC045346918A5D31E7E56277B'
from batched_lossless_review_entry_v3 import emit
code=old.read_text(encoding='utf-8')
before='    old.emit(root,context,views,pieces)'
assert code.count(before)==1
code=code.replace(before,'    COMPACT_EMIT(root,context,views,pieces)')
# Expose the loaded cli, whose globals retain the mechanical transport binding.
namespace=dict(__name__=__name__,__file__=str(Path(__file__)),COMPACT_EMIT=emit)
exec(compile(code,str(old),'exec'),namespace)
cli=namespace['cli']
