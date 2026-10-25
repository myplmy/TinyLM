#!/usr/bin/env python3
"""Native EN55의 닫힌128원문을 보존하며 후보 LF/UI만 별도 revision으로 기록한다."""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
import difflib,hashlib,json
from pathlib import Path
import sys,time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import p106b_text_batches as b
from scripts import p106b_publish_text_draft as pub
BASE=b.BASE
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def write(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 raw=(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode()
 assert len(raw)<20_000_000
 with path.open('xb') as stream:stream.write(raw)
parent=BASE/'packets/native_full_en_000055.json'
review=BASE/'imported/native_full_en_000055_published_FC618DBAC98F/review_000000.jsonl'
note=BASE/'native_en_followup_20261026/luna_exact_text_edits.md'
assert digest(parent)=='041A730AD3E08F27C4E1A2FA01EA7225C2E380740BE19236203F22EB34ED8DA7'
oldpins={str(p.relative_to(ROOT)):digest(p) for p in (parent,review,note)}
packet=json.loads(parent.read_text());rows=[json.loads(x) for x in review.read_text().splitlines()]
assert len(rows)==128 and Counter(x['draft']['decision'] for x in rows)=={'KEEP':38,'REWRITE':22,'HOLD':68}
originals={d['id']:d for d in packet['documents']}
assert len(originals)==128 and all(originals[r['source']['id']]==r['source'] for r in rows)
newpacket=deepcopy(packet)
newpacket['root_revision']={'parent_packet':str(parent.relative_to(ROOT)),'parent_sha256':digest(parent),
 'scope':'SAME128_SOURCE_CANDIDATE_BOUNDARY_UI_REVISION_ONLY','full_semantic_review':False}
packet_path=BASE/'packets/native_full_en_000055_root_boundary_20261026_v2.json'
revision=BASE/'root_native_en55_boundary_20261026_v2'
inputs=BASE/'author_scratch/native_full_en_000055_root_boundary_20261026_v2'
assert not inputs.exists()
assert not revision.exists() or not list(revision.iterdir())
pub.owned_path(str(packet_path.relative_to(ROOT)),'packet')
pub.owned_path(str((inputs/'26938.json').relative_to(ROOT)),'input')
events=[];source_metadata=[];audit=[];entries=[];prepared=[]
def replace(text,old,new,reason,ident):
 count=text.count(old)
 if count!=1:
  if new and old!=new and text.count(new)==1:
   events.append(dict(id=ident,operation='ALREADY_RESOLVED_BY_LF_RECONSTRUCTION',reason=reason,
                      old=old,new=new))
   return text
  raise ValueError(f'exact candidate anchor count {ident}: {count}: {old[:80]}')
 events.append(dict(id=ident,operation='EXACT_CANDIDATE_REPLACEMENT',reason=reason,old=old,new=new))
 return text.replace(old,new,1)
def remove(text,old,reason,ident,metadata=False):
 if metadata:source_metadata.append(dict(id=ident,text=old,kind=reason))
 return replace(text,old,'',reason,ident)
def anchored_edits(source,desired):
 before=b.lf_lines(source);after=b.lf_lines(desired);changes=[]
 for tag,a,z,c,d in difflib.SequenceMatcher(None,before,after,autojunk=False).get_opcodes():
  if tag=='equal':continue
  if a==z:raise ValueError('zero-width LF insertion requires a separately declared source range')
  replacement=''.join(after[c:d])
  changes.append(dict(action='REMOVE' if not replacement.strip() else 'MOVE_TO_PROSE',
   source_lines=[a+1,z],source_start=before[a].strip()[:120],
   source_end=before[z-1].strip()[-120:],replacement=replacement,
   reason='원형 LF 경계를 보존하고 명시 UI 잔재만 분리한 총괄 후보 revision'))
 text,ranges=b.apply_positioned_edits(source,changes)
 assert text==desired
 return changes,ranges
start=time.monotonic()
for item in rows:
 source=item['source'];draft=deepcopy(item['draft']);ident=source['id'];original=source['text']
 assert b.sha(original)==source['sha256']
 old=draft['proposed_text'];before=draft['proposed_text']
 assert b.apply_positioned_edits(original,draft['changes'])[0]==old
 if draft['decision']=='REWRITE':
  edits=deepcopy(draft['changes']);source_lines=b.lf_lines(original)
  for change in edits:
   a,z=change['source_lines'];span=''.join(source_lines[a-1:z])
   if change['replacement'] and span.endswith('\n') and not change['replacement'].endswith('\n'):
    change['replacement']+='\n'
    events.append(dict(id=ident,operation='RESTORE_CONSUMED_SOURCE_LF',source_lines=[a,z],
                       reason='정확 LF 범위 치환이 소비한 원문 구분자를 새 replacement에도 명시'))
  text,_=b.apply_positioned_edits(original,edits)
  if ident==26988:
   text=remove(text,'Direct download: SUFB_S760_WeNeedToProtectHorseshoeCrabsAndHereIsWhy.mp3','음원 다운로드 UI',ident,True)
   text=remove(text,'Category:Horseshoe Crabs -- posted at: 7:02pm EST','분류와 게시 시각 metadata',ident,True)
  if ident==27170:
   text=remove(text,"Click the play button to begin. If you don't see a video player, you need to download and install the free Realplayer G2, or ask your network administrator to do so--so that you can enjoy the full multimedia benefits of the Web.",'영상 player 설치와 조작 UI',ident)
  if ident==27375:
   text=replace(text,'What you should know about Borobudur — the world’s largest Buddhist monumentThe world’s largest Buddhist monument','What you should know about Borobudur — the world’s largest Buddhist monument\nThe world’s largest Buddhist monument','표제와 부표제 원문 경계',ident)
  if ident==27673:
   text=replace(text,'What are the effects of deforestation on society?Forest contains 70% of Earth’s animals and plants. It is essential for','What are the effects of deforestation on society?\nForest contains 70% of Earth’s animals and plants. It is essential for','질문형 표제와 본문 경계',ident)
  if ident==27758:
   text=remove(text,'Article Source: http://EzineArticles.com/expert/Dale_Phillip/1169732','필자 profile 출처 metadata',ident,True)
  if ident==28117:
   text=replace(text,'Author: Melanie DearringerBromeliads are excellent indoor plants.','Author: Melanie Dearringer\nBromeliads are excellent indoor plants.','필자와 본문 경계',ident)
  if ident==28304:
   for old,new in [
    ('swiftness.He further reasons that this action causes the glass to form a structure like threads that run the length of the drop:','swiftness.\nHe further reasons that this action causes the glass to form a structure like threads that run the length of the drop:'),
    ('called the grain.Finally, he concludes','called the grain.\nFinally, he concludes'),
    ('be shivered in pieces.A somewhat tortured connection','be shivered in pieces.\nA somewhat tortured connection'),
    ('Spring/Summer 2016.Video Credit:','Spring/Summer 2016.\nVideo Credit:')]:
    text=replace(text,old,new,'인용과 해설 또는 서지 경계',ident)
  if ident==28519:
   text=remove(text,'|Wikisource has the text of the 1905 New International Encyclopedia article Mimamsa.|','외부 자료 wrapper attribution metadata',ident,True)
  if ident==28814:
   text=remove(text,'Also read: The 5 Best TEFL Games For Adult Students','관련 게시물 navigation UI',ident)
  if ident==28859:
   for heading,anchor in [('Adding Through Hole Within DfM',"When critical components on an assembly can't be SMDs"),('Conclusion','When working with difficult or unusual designs')]:
    if heading not in text:
     assert original.count(heading)==1
     text=replace(text,anchor,heading+'\n'+anchor,'원문에 존재했던 절 표제 복원',ident)
   text=replace(text,'end product.Automated selective soldering','end product.\nAutomated selective soldering','문장 경계',ident)
   text=replace(text,'throughput.\nACKNOWLEDGEMENTS:Selective soldering equipment','throughput.\nACKNOWLEDGEMENTS: Selective soldering equipment','원문 LF 복원 뒤 감사정보 레이블 경계',ident)
  if ident==29086:
   text=remove(text,'Download citation file:','비어 있는 citation download UI',ident)
  if ident==29184:
   text=replace(text,'27 October, 2015There is a saying among early settlers in North America','27 October, 2015\nThere is a saying among early settlers in North America','게시일과 본문 경계',ident)
   text=remove(text,'This email has been checked for viruses by Avast antivirus software.','메일 검사기 footer',ident)
  assert '변경 근거: 변경별 사유 미기재' not in original and '변경 근거: 변경별 사유 미기재' not in text
  changes,ranges=anchored_edits(original,text)
  draft.update(changes=changes,proposed_text=text,root_resolved_source_ranges=ranges)
  draft['reason']+=' 총괄 후속은 소비된 원문 LF와 명시 UI/출처 metadata 경계만 수리하며 사실·용어·권리를 정답화하지 않는다.'
  draft['root_revision_reference']={'prior_import':str(review.relative_to(ROOT)),'prior_import_sha256':digest(review),
   'prior_candidate_sha256':b.sha(before),'new_candidate_sha256':b.sha(text)}
 draft['training_admission']='NOT_ADMITTED'
 proof=pub.validate(newpacket,draft,'native')
 assert proof['id']==ident
 audit.append(dict(id=ident,decision=draft['decision'],source_sha256=source['sha256'],
   old_candidate_sha256=b.sha(before),new_candidate_sha256=b.sha(draft['proposed_text']),
   candidate_changed=before!=draft['proposed_text'],semantic_truth='UNVERIFIED',training_admission='NOT_ADMITTED'))
 prepared.append((ident,draft))
# Complete every exact-anchor/position check before any new packet/publication write.
assert len(prepared)==128 and all(digest(ROOT/name)==value for name,value in oldpins.items())
if packet_path.exists():
 assert json.loads(packet_path.read_text())==newpacket
else:write(packet_path,newpacket)
inputs.mkdir(parents=True,exist_ok=False)
revision.mkdir(parents=True,exist_ok=True)
for ident,draft in prepared:
 input_path=inputs/(str(ident)+'.json');write(input_path,draft)
 # The publisher is the canonical write-once promotion path. Stop on any failed receipt.
 rc,receipt=pub.publish(str(packet_path.relative_to(ROOT)),str(input_path.relative_to(ROOT)),'native',
                        argv=['root_native_en55_boundary_v2',str(ident)])
 if rc!=0:raise RuntimeError('publication failed; preserved partial '+str(ident)+': '+json.dumps(receipt,ensure_ascii=False))
 entries.append(dict(id=ident,published=receipt['final'],receipt=receipt['attempt']+'/receipt.json'))
published=BASE/'published'/packet_path.stem
imported=BASE/'imported'/packet_path.stem
b.import_packet(packet_path,published,imported,'native')
newrows=[json.loads(x) for x in (imported/'review_000000.jsonl').read_text().splitlines()]
assert len(newrows)==128 and [x['source'] for x in newrows]==[x['source'] for x in rows]
assert Counter(x['draft']['decision'] for x in newrows)==Counter(x['draft']['decision'] for x in rows)
assert all(digest(ROOT/name)==value for name,value in oldpins.items())
report=dict(schema='P106B_NATIVE_EN55_ROOT_BOUNDARY_REVISION_V1',parent_packet=str(parent.relative_to(ROOT)),
 parent_packet_sha256=oldpins[str(parent.relative_to(ROOT))],new_packet=str(packet_path.relative_to(ROOT)),
 new_packet_sha256=digest(packet_path),prior_import=str(review.relative_to(ROOT)),
 prior_import_sha256=oldpins[str(review.relative_to(ROOT))],new_import=str(imported.relative_to(ROOT)),
 source_count=128,reviewed_rewrite_count=22,prior_keep_reused=38,prior_hold_preserved=68,
 candidates_changed=sum(x['candidate_changed'] for x in audit),candidate_ids_changed=[x['id'] for x in audit if x['candidate_changed']],
 events=events,source_metadata_separated=source_metadata,renderer_metadata_was_candidate=False,
 audit=audit,publications=entries,all_sources_identical=True,old_inputs_unchanged=True,
 new_import_report_sha256=digest(imported/'report.json'),elapsed_sec=time.monotonic()-start,
 training_admission='NOT_ADMITTED',admitted=0,full_semantic_review=False,rights_clearance='UNVERIFIED',
 whole_native_corpus_cleaned=False,new_model_training=0)
report['prior_failed_tool_attempts']=['101_log_20261026_P106B_Stage9pWm_native_en55_boundary_revision.txt','101_log_20261026_P106B_Stage9pWm_native_en55_boundary_retry.txt']
write(revision/'readback.json',report)
write(ROOT/'handoff/audit/oct26_research/native_en55_root_boundary_revision.json',report)
print(json.dumps({k:report[k] for k in ['source_count','reviewed_rewrite_count','prior_keep_reused','prior_hold_preserved','candidates_changed','candidate_ids_changed','elapsed_sec','admitted']},ensure_ascii=False))

