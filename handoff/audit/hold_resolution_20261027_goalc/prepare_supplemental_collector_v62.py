"""Resnapshot the entire current cohort with new mediation pins and exact byte limit."""
from pathlib import Path

AUDIT=Path(__file__).resolve().parent
target=AUDIT/'collect_supplemental_candidates_v62.py'
assert not target.exists()
text=(AUDIT/'collect_supplemental_candidates_v61.py').read_text(encoding='utf-8')
before='OUT = AUDIT / "supplemental_candidates_snapshot_v61.json"'
assert text.count(before)==1
text=text.replace(before,'OUT = AUDIT / "supplemental_candidates_snapshot_v62.json"')
before='''for guidance_name in ["ROOT_MEDIATION_V1.md", "ROOT_EVIDENCE_1403490_CREDIT_V1.md"]:
    guidance_path=BASE / "repeat_named_roles_counter_v2" / guidance_name'''
after='''for guidance_path in sorted((BASE / "repeat_named_roles_counter_v2").glob("ROOT_*.md")):
    inv.require(guidance_path.is_file() and not guidance_path.is_symlink(), "owned root guidance must be a regular file")'''
assert text.count(before)==1
text=text.replace(before,after)
before='inv.write_json(OUT, result)'
after='''payload=(json.dumps(result,ensure_ascii=False,indent=2)+chr(10)).encode("utf-8")
inv.require(len(payload)<20_000_000,"exact serialized snapshot requires a new sharded namespace")
with OUT.open("xb") as stream:
    stream.write(payload)'''
assert text.count(before)==1
text=text.replace(before,after)
with target.open('x',encoding='utf-8') as stream:
    stream.write(text)
print('새수집62 준비: 전량732·모든소유ROOT근거핀·실제직렬화20MB미만검사')
