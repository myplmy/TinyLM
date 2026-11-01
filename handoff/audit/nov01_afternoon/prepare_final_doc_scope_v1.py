"""Read-only file audit; write only the two named receipt/message outputs.

The WIP is an input to hashing and Git staging, never an output of this helper.
"""
from pathlib import Path
import hashlib
import json
import re
import subprocess
ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).parent


def main():
    outputs=[BASE/'COMMIT_MESSAGE_v3.txt',BASE/'FINAL_DOC_SCOPE_v1.json']
    assert all(not p.exists() and p.parent==BASE for p in outputs)
    text=(ROOT/'handoff/202611011123_HANDOFF.md').read_text()
    body=text.split('## 8. 커밋 메시지',1)[1].split('## 9.',1)[0]
    fence=chr(96)*3
    parts=re.findall(re.escape(fence)+'text'+chr(10)+'(.*?)'+chr(10)+re.escape(fence),body,re.S)
    assert len(parts)==2
    message=parts[0]+chr(10)*2+parts[1]+chr(10)
    with outputs[0].open('x',encoding='utf-8') as f:f.write(message)
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
    def names(x):return {z.decode() for z in x.split(bytes([0])) if z}
    assert not git('diff','--cached','--name-only','-z')
    tracked=names(git('diff','--name-only','-z'))
    allowed={'ai_dev_tool/Codex/08_AI-미보고-내역-자백원장.md','handoff/202611011123_HANDOFF.md',
             'handoff/WIP_20261022_작업원장.md'}
    assert tracked-allowed=={'scripts/flag_whitelist.tsv'}
    others=names(git('ls-files','--others','--exclude-standard','-z'))
    selected=sorted((tracked&allowed)|{x for x in others if x.startswith('handoff/audit/nov01_afternoon/')})
    assert all(not x.endswith(('.paths','.pt','.bin','.jsonl','.lock')) for x in selected)
    records=[]
    for name in selected:
        p=ROOT/name;assert p.is_file() and not p.is_symlink()
        data=p.read_bytes();assert len(data)<20_000_000
        if p.suffix=='.py':compile(data.decode(),name,'exec')
        records.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest().upper()))
    payload=dict(schema='AFTERNOON_FINAL_DOC_SCOPE_V1',authority='user105',paths=selected,bindings=records,
        foreign_tracked_preserved=['scripts/flag_whitelist.tsv'],other_untracked_count=len(others-set(selected)),
        other_paths_or_contents_recorded=False,source_or_model_changes_after_research_commit=False,
        original105_and_statuses_equal=True,handoff_three_checks_actual_exit=[0,0,0],capsule_actual_exit=0,
        expected_index_extra='handoff/audit/nov01_afternoon/FINAL_DOC_SCOPE_v1.json')
    with outputs[1].open('x',encoding='utf-8') as f:json.dump(payload,f,ensure_ascii=False,indent=2)
    print(json.dumps(dict(primary_paths=len(selected),extra_receipt=1,all_below20mb=True,
        foreign_flag_excluded=True,wip_writes=0)))


if __name__=='__main__':main()
