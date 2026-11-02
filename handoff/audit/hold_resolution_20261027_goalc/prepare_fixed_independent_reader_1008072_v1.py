"""Adapt the audited small-view reader to one newly reported path incident."""
from pathlib import Path

AUDIT=Path(__file__).resolve().parent
text=(AUDIT/'prepare_fixed_reader_832056_v1.py').read_text(encoding='utf-8')
text=text.replace('832056','1008072').replace('context_latin','context_hangul')
text=text.replace('repeat_named_roles_counter_v2','repeat_named_full_independent_v1')
text=text.replace('path_error_note_v4.md','path_error_note_v1.md')
lo=text.index("wrong=BASE/")
hi=text.index("for label in ['original','candidate']:",lo)
replacement='''wrong=BASE/'agents/context_hangul/repeat_named_full_independent_v1/inputs'
observed=[]
for label in ('original','candidate'):
    path=wrong/('expanded_train_1008072_'+label+'.txt')
    try:
        value=path.lstat()
        observed.append(dict(path=str(path.relative_to(ROOT)),exists_now=True,
            symlink=stat.S_ISLNK(value.st_mode),regular_file=stat.S_ISREG(value.st_mode)))
    except FileNotFoundError:
        observed.append(dict(path=str(path.relative_to(ROOT)),exists_now=False))

'''
text=text[:lo]+replacement+text[hi:]
before="framed.startswith('=== BEGIN expanded_train:1008072 original characters=44313 ===')"
assert text.count(before)==1
text=text.replace(before,"framed.startswith('=== BEGIN expanded_train:1008072 original characters=')")
text=text.replace('six reported paths','two reported paths').replace('shared6000자 패킷15개','지정 shared6000자 전체 패킷')
text=text.replace("(ROOT[p['path']] if False else ROOT/p['path'])","(ROOT/p['path'])")
target=AUDIT/'export_fixed_independent_reader_1008072_v1.py'
with target.open('x',encoding='utf-8') as stream:stream.write(text)
print('1008072 원문만 정확 고정뷰로 재판독할 준비기 생성')
