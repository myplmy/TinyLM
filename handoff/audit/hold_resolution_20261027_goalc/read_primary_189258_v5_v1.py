"""Reuse the pinned bounded reader for the next immutable paper revision."""
from pathlib import Path
import hashlib

A=Path(__file__).resolve().parent
frozen=A/'read_primary_189258_v4_v1.py';raw=frozen.read_bytes()
assert hashlib.sha256(raw).hexdigest().upper()=='ADD1B90A161B6F2B917209BAD180C2D1BA4E8E8C411961ABE7B602DD842E8981'
code=raw.decode('utf-8')
replacements={
    'remaining_field_title_page_010_counter_v1_snapshots/v11/complete.json':'remaining_field_title_page_010_counter_v1_snapshots/v13/complete.json',
    'D0DC8ED566680E7997588D8D5A761367E9375582506123ABF8D650D8907968F2':'39CE8254FDEDD953D2F6EAFAD1233E82864E73EA6CF048FC25AC4772EB87F4CB',
    "assert row['clean_text_sha256'] == 'F5AEBCD220AAB5F530337846439EB03992AC7EFA3A4344E9CD3CE14FBAABB50E'":"assert row['clean_text_sha256'] == '10829E26FB74757CC37774B62F9CCB36A0D29422FEF0D806CF35EEE5CA9C4925'",
    'exact_cohort_rendered_v1/BB/BB87351E3DF882E9089EADF383FFB335FD8F97ECA652692AD27D97B96A35223E.txt':'exact_cohort_rendered_v1/F5/F5AEBCD220AAB5F530337846439EB03992AC7EFA3A4344E9CD3CE14FBAABB50E.txt',
    "sha256='BB87351E3DF882E9089EADF383FFB335FD8F97ECA652692AD27D97B96A35223E'":"sha256='F5AEBCD220AAB5F530337846439EB03992AC7EFA3A4344E9CD3CE14FBAABB50E'",
    'v3_to_v4':'v4_to_v5',
    'CURRENT_V4_BODY':'CURRENT_V5_BODY',
}
for before,after in replacements.items():
    assert before in code,before
    code=code.replace(before,after)
exec(compile(code,str(frozen),'exec'),dict(__name__='primary_v5_bounded_read',__file__=str(Path(__file__))))
