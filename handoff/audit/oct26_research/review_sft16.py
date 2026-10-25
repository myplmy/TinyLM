#!/usr/bin/env python3
"""동결된 SFT16원천/48변형의 총괄 후행 판독과 실제 포장 길이 회수."""
from collections import Counter
import hashlib,json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tokenizers import Tokenizer
from tinylm.data.sft import encode_conversation, IGNORE
from tinylm.train.mtp_sft import encode_record
base=ROOT/'data_cache/p106b_text_work_20261022/root_semantic_followup_20261026/sft_000006'
source=ROOT/'data_cache/p106b_text_work_20261022/imported/sft_000006/authoring_000000.jsonl'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
assert sha(source)=='693B29EB41D56711325AF23B0DB75D6FA151E67B3EC86D950BE4D15087394772'
assert sha(base/'source_and_variants.md')=='A572500F4638154E2728809D9FABB2EA7D2D833682364A6290111292D2EAD5DA'
assert sha(base/'luna_semantic_notes.md')=='4DAB0F9094F2EAB32E4B87B49EBE073F6A9AA75D12AFB85032BF7B8F1BEA0471'
tp=ROOT/'data_cache/tok-ko-en-32768-chat32.json'
assert sha(tp)=='9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
tok=Tokenizer.from_file(str(tp))
rows=[json.loads(s) for s in source.read_text().splitlines()]
assert len(rows)==48 and sorted({r['source_index'] for r in rows})==list(range(236,252))
holds={
237:'PERT 표준 확장은 Program Evaluation and Review Technique이며 원천은 and를 빠뜨렸다. 원문은 보존하고 별도 수정본으로만 회복한다.',
238:'원천의 K 함수가 일반 내적보다 언제나 저렴하다는 단정과 2N 복잡도 및 복잡도 문제가 없다는 설명은 뒷받침되지 않는다. 번역 충실성과 원천 사실성을 분리해 보류한다.',
239:'원질문의 주기율표 족에 관한 추측을 답의 Yes가 확인하는 듯 읽힐 수 있다. 원천의 오개념 교정과 질문 정합성을 별도 수정 전 보류한다.',
240:'운동 허가 조건은 보존됐으나 실제 부상 단계와 단백질·열량의 구체적 권고는 전문 근거 미확인이다. 세 사용자/세 답의 원형을 보존하고 보류한다.',
241:'4x8 한 프레임의 판재 수와 두 단 구성의 전제가 설명되지 않았다. 당근은 깊이 조건에 따라 양쪽 설명이 가능하므로 단순 모순으로 판정하지 않는다. 구성 명확화 전 보류한다.',
247:'Koraweema를 유기 농법과 등치할 근거가 확인되지 않았다. 용어를 추정하거나 새 번역어로 바꿔 정답화하지 않는다.'
}
notes={
236:'다음 행동은 칼로 토마토 자르기이며 선택지·상태를 보존했다. 길이는 별도 검산한다.',
242:'Rajya Sabha 고유명과 상원 명칭 질문을 보존했다.',
243:'보전의 가치와 의학 지식 기여의 가능성을 보존했으며 가능성을 확정 사실로 바꾸지 않았다.',
244:'반사와 각도 법칙의 입문 설명을 보존했다. 생략된 고급 조건 자체를 번역 오류로 판정하지 않는다.',
245:'책임·편향·피해 완화의 일반 윤리 설명을 보존했다. 개별 정책 정답으로 확대하지 않는다.',
246:'주권 이전의 시민 집단이라는 뜻을 보존해야 한다. body를 새 제도 기관으로 좁혀 쓰지 않는다.',
248:'직장 발언권 침해의 피해를 설명한다. 성장 기회 자체가 해롭다는 뜻으로 바꾸면 안 된다.',
249:'2014년 평화상 공동 수상과 당시17세라는 사실은 공식 노벨상 기록을 대조했다. 최연소라는 현행 기록은 별도 시점 의존을 남긴다.',
250:'정십각형10변 곱하기5cm는50cm로 계산이 일치한다.',
251:'AI가 무엇을 원하는지에 기능·목적을 설명하는 답은 가능한 대화 해석이다. 질문의 모호성만으로 재질문을 강제하거나 오답으로 판정하지 않는다.'
}
items=[]
for r in rows:
 i=r['source_index'];kind=r['variant_kind']
 original_roles=Counter(m['role'] for m in r['original_messages'])
 variant_roles=Counter(m['role'] for m in r['messages'])
 assert original_roles==variant_roles
 d='HOLD_SOURCE' if i in holds else 'MEANING_REVIEW_ACCEPTED_NOT_ADMITTED'
 reason=holds.get(i,notes.get(i))
 if i==246 and kind=='ko_rephrase':
  d='HOLD_TRANSLATION';reason='시민 집단을 시민들로 이루어진 기구로 바꿔 특정 조직을 뜻하게 할 수 있다. Luna의 잠정 충실 의견을 총괄이 채택하지 않는다.'
 if i==248 and kind=='ko_translation':
  d='HOLD_TRANSLATION';reason='해로운 개인적·직업적 성장 기회라고 수식해 성장 기회의 제한이 해롭다는 원뜻을 왜곡한다. Luna가 놓친 수식 범위를 총괄이 보류한다.'
 canonical={'messages':r['messages'],'meta':{'language':r['language']}}
 ids,labels,_=encode_conversation(canonical,tok,'chatml')
 length=len(ids)-1;targets=sum(x!=IGNORE for x in labels[1:])
 eligible=length<=1024
 error=None
 if eligible:
  rec=encode_record(canonical,tok,context=1024)
  assert rec.x_tokens==length and rec.targets==targets
 else:error='OVER_CONTEXT_NO_TRUNCATION'
 items.append(dict(source_index=i,source_id=r['source_id'],root_id=r['root_id'],variant_kind=kind,
  candidate_object_sha256=hashlib.sha256(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest().upper(),
  original_roles=dict(original_roles),variant_roles=dict(variant_roles),meaning_decision=d,reason=reason,
  x_tokens=length,assistant_target_tokens=targets,context1024_eligible=eligible,context_error=error,
  actual_training_admission='NOT_ADMITTED',actual_training=0))
out=dict(schema='P106B_SFT16_ROOT_READBACK_V1',source_path=str(source.relative_to(ROOT)),
 source_sha256=sha(source),readable_packet_sha256=sha(base/'source_and_variants.md'),luna_memo_sha256=sha(base/'luna_semantic_notes.md'),
 source_count=16,variant_count=48,root_read_all_original_and_variants=True,
 source_role_correction='',decisions=items)
out['source_role_correction']='Luna는238~241을 모두2user/2assistant라고 썼으나 실제240은3user/3assistant다. 변형도 같은3턴을 보존한다.'
out.update(meaning_counts=dict(Counter(x['meaning_decision'] for x in items)),
 context_overflow_count=sum(not x['context1024_eligible'] for x in items),
 total_input_tokens=sum(x['x_tokens'] for x in items),
 total_assistant_target_tokens=sum(x['assistant_target_tokens'] for x in items),
 source_or_candidates_mutated=False,admitted=0,new_student_training=0,
 global_document_leakage='UNVERIFIED',root_split_and_rights_and_exposure='PENDING',
 primary_references=[
 'https://digital.ahrq.gov/health-it-tools-and-resources/evaluation-resources/workflow-assessment-health-it-toolkit/all-workflow-tools/pert-chart',
 'https://scikit-learn.org/stable/modules/svm.html',
 'https://www.nobelprize.org/prizes/lists/nobel-laureates-by-age/'],
 interpretation='뜻 판독과 포장 계측이며 의미 통과를 실제 TRAIN 편입이나 일반 품질 보증으로 승격하지 않는다.')
target=ROOT/'handoff/audit/oct26_research/sft16_root_readback.json'
with target.open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:out[k] for k in ['source_count','variant_count','meaning_counts','context_overflow_count','total_input_tokens','total_assistant_target_tokens','admitted']},ensure_ascii=False))

