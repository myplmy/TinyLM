"""Exclude the already root-reviewed literal record from the prior pending copy."""
from pathlib import Path

source = Path(__file__).with_name('prepare_hangul_literal_reopen_copies_v1.py')
code = source.read_text(encoding='utf-8')
old = "if row.get('role') == 'context_hangul' and row.get('status') == 'TEXT_ADJUDICATION_NOT_ADMISSION')"
new = "if row.get('role') == 'context_hangul' and row.get('status') == 'TEXT_ADJUDICATION_NOT_ADMISSION' and row['id'] != 'expanded_train:1046282')"
assert code.count(old) == 1
exec(compile(code.replace(old, new), str(source), 'exec'), {'__file__': __file__, '__name__': __name__})
