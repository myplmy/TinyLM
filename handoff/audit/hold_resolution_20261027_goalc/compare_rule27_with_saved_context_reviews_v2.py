"""Recompare unchanged rule candidates with current, corrected source reviews."""
from pathlib import Path
import hashlib

frozen=Path(__file__).with_name('compare_rule27_with_saved_context_reviews_v1.py')
raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='DC93F076773257A28E72224C69958F2CC5A1AEE24AEEE0317662EF40679717CB'
code=raw.decode('utf-8')
before="overrides={12:'v12',14:'v7',16:'v2'}"
assert code.count(before)==1
code=code.replace(before,"overrides={12:'v13',14:'v8',15:'v4',16:'v3'}")
before="'RULE27_SAVED_CONTEXT_REVIEW_COMPARISON_V1.json'"
assert code.count(before)==1
code=code.replace(before,"'RULE27_SAVED_CONTEXT_REVIEW_COMPARISON_V2.json'")
exec(compile(code,str(frozen),'exec'),dict(__name__='current_saved_review_rule27_comparison',
    __file__=str(Path(__file__))))
