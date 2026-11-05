"""Reuse current guard4 with an exact filename alias and first-cell declarations."""
from pathlib import Path
import hashlib

AUDIT = Path(__file__).resolve().parent
frozen = AUDIT/'collect_exact_reviews_guarded_v7.py'
raw = frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper() == 'FB2669FD94BFE68D04C64062E401E55DEB96B241502C5A8B1A0999BADF530C1A'
text = raw.decode('utf-8')
last = "exec(compile(code, str(frozen), 'exec'), dict(__name__=__name__, __file__=str(Path(__file__)), frozen=frozen))"
assert text.count(last) == 1
scope = dict(__name__='guard4_collector8_transform',__file__=str(Path(__file__)))
exec(compile(text.split(last)[0], str(frozen), 'exec'), scope)
code = scope['code']
anchor = "    code = frozen.read_text(encoding='utf-8')"
assert code.count(anchor) == 1
extra = """
    code = replace_once(code, 'EXACT_COHORT_LEGACY_REVIEW_RANK_ALIASES_V1.json',
        'EXACT_COHORT_LEGACY_REVIEW_RANK_ALIASES_V2.json')
    code = replace_once(code, 'p106b_hold_resolution_review_safeguards_v3',
        'p106b_hold_resolution_review_safeguards_v4')
"""
code = code.replace(anchor, anchor + extra)
anchor = '        for pin_path in (Path(__file__),'
assert code.count(anchor) == 1
code = code.replace(anchor,
    "        for pin_path in (ROOT/'scripts/p106b_hold_resolution_review_safeguards_v4.py'," + chr(10) +
    "                         AUDIT/'collect_exact_reviews_guarded_v7.py'," + chr(10) +
    "                         AUDIT/'EXACT_COHORT_LEGACY_REVIEW_RANK_ALIASES_V2.json',Path(__file__),")
exec(compile(code, str(scope['frozen']), 'exec'), dict(__name__=__name__,
    __file__=str(Path(__file__)),frozen=scope['frozen']))
