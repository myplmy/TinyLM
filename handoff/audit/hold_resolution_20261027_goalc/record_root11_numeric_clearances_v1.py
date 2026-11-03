"""Bind eight actual root context judgments to eighteen exact numerical flags."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE = inv.BASE / 'agents'
RULES = {
    '396589':dict(values=['11','10'],kind='SAME_EVENT_MONTH_DAY_RETAINED',
        reason='원문 리드 사망1967년11월10일과 사망분류1970년이 충돌한다. 두 연도는 비채택하고 실제 같은 사망의11월10일만 보존했다. 새 달력이나 생일을 만들지 않았다.',
        anchors=[('1967년 11월 10일','11월 10일 사망했다.')]),
    '688560':dict(values=['2','3','10','25','1940','1943','1889','1956'],kind='PUBLISHED_EXACT_DATE_AND_ELECTION_CORRECTION',
        reason='실제 SKS 출판 전기 PDF의1889년2월3일/1956년10월25일과 대통령실 선거표1940/1943의 좁은 정정이다.1937년 선거인단과 실제 선거 연도를 구분했고 다른 나이/기간을 역산하지 않았다.',
        evidence=BASE/'context_controls/remaining_birth_full_counter_v1/ROOT_EVIDENCE_688560_RYTI_DATES_AND_ELECTIONS_V1.md',
        anchors=[('1889년 12월 31일 ~ 1956년 12월 30일','1889년 2월 3일 ~ 1956년 10월 25일'),
            ('1937년 의회에서 열린 간접선거','1940년 간접선거'),('1937년 다시 수정헌법','1943년 다시 수정헌법'),
            ('1867년 출생','1889년 출생'),('1951년 사망','1956년 사망')]),
    '755020':dict(values=['2015','3'],kind='SAME_EVENT_COMMON_YEAR_MONTH_RETAINED',
        reason='같은 권영효 사망의2015년3월25일/26일 중 상충하는 일만 비채택하고 양쪽에 실제 명시된2015년3월을 보존했다.',
        anchors=[('2015년 3월 25일','2015년 3월'),('2015년 3월 26일에 숙환으로 별세했다.','2015년 3월에 숙환으로 별세했다.')]),
    '809431':dict(values=['1976'],kind='SAME_PARAGRAPH_EXPLICIT_YEAR_REUSED',
        reason='같은 이병호의1976년5월 입원과 그 뒤9월 사망이 한 문단에 명시되어 있다. 리드9월28일/본문9월15일의 일만 비채택하고 동일 사망의1976년9월을 명시했다. 나이/사건 연도를 계산하지 않았다.',
        anchors=[('1976년 5월 25일','1976년 5월 25일'),('재발하여 9월 15일 간암으로 사망했다.','재발하여 1976년 9월 간암으로 사망했다.')]),
    '809644':dict(values=['1821'],kind='PRIMARY_PUBLISHED_YEAR_CORRECTION',
        reason='그레고리오스5세 처형연도1926을 실제 총대주교청/동일 기관 출판 근거의1821로 좁게 정정했다. 원문4월22일을 유지하고 달력 환산이나 문 폐쇄 시작연도를 생성하지 않았다.',
        evidence=BASE/'historical_review/remaining_birth_full_counter_v1/ROOT_EVIDENCE_809644_GREGORY_YEAR_V1.md',
        anchors=[('1926년 4월 22일 부활 주일','1821년 4월 22일 부활 주일')]),
    '820819':dict(values=['1595','1632'],kind='PUBLISHED_BIOGRAPHICAL_DATE_CORRECTION',
        reason='동일 알베르 지라르의1595 출생/1632년12월8일 사망을 실제 MacTutor와 Jean Itard 전기 근거로 정정했다. 같은 계보 자료를 독립 두 출처로 세지 않고 레이든 사망지는 추정 한정을 보존했다.',
        evidence=BASE/'context_latin/remaining_birth_full_counter_v1/ROOT_EVIDENCE_820819_GIRARD_DATES_V1.md',
        anchors=[('1595년 출생','1595년 ~ 1632년 12월 8일'),('1532년 12월 8일','사망지는 레이든으로 추정된다.')]),
    '824834':dict(values=['1926'],kind='DATE_RANGE_HYPHEN_NOT_NEGATIVE_YEAR',
        reason='1891년-1926년9월11일의 하이픈은 생몰 범위 구분자다. 상충 생년1891/1890을 분리하며 같은 사망1926년9월11일을 보존했으며 음수1926을 양수로 바꾼 계산이 아니다.',
        anchors=[('1891년-1926년 9월 11일','1926년 9월 11일 사망')]),
    '961894':dict(values=['12.29'],kind='SAME_TYPED_BIRTH_MONTH_DAY_WITHOUT_CONFLICTING_YEAR',
        reason='원문1922.12.29 출생 필드와 리드의 같은 월일은 유지하고 출생분류1992와 상충하는 연도만 분리했다.12.29는 같은 출생 월일이며 소수나 새 버전값이 아니다.',
        anchors=[('1922.12.29 평남 진남포 억량기리 52에서 출생','12.29 평남 진남포 억량기리 52에서 출생')]),
}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--diagnostic',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    document=inv.cache.read(args.diagnostic)
    contract=inv.cache.read(AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json')
    rows,pins=[],{}
    for row in document['rows']:
        flags=row['unresolved_flags']
        if not flags:continue
        ident=row['id'];number=ident.split(':')[1];rule=RULES[number]
        assert ident not in contract['restricted_ids'] and row['original']['sha256'] not in contract['restricted_hashes']
        assert [f['body_token'] for f in flags]==rule['values'], 'different numerical change requires new judgment'
        for field in ['original','body','review']:
            pin=row[field]
            assert inv.file_sha(ROOT/pin['path'])==pin['sha256']
            pins[pin['path']]=pin['sha256']
        raw=(ROOT/row['original']['path']).read_text(encoding='utf-8')
        body=(ROOT/row['body']['path']).read_text(encoding='utf-8')
        anchors=[]
        for before,after in rule['anchors']:
            assert before in raw and after in body,(ident,before,after)
            anchors.append(dict(source=before,body=after,
                source_span=[raw.index(before),raw.index(before)+len(before)],
                body_span=[body.index(after),body.index(after)+len(after)]))
        for flag in flags:
            a,b=flag['body_span'];assert body[a:b]==flag['body_token']
        evidence=None
        if rule.get('evidence'):
            path=rule['evidence'];evidence=dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path))
            pins[evidence['path']]=evidence['sha256']
        rows.append(dict(id=ident,original=row['original'],body=row['body'],review=row['review'],
            approved_exact_flags=flags,kind=rule['kind'],reason=rule['reason'],anchors=anchors,
            evidence=evidence,root_numeric_context_approved=True,full_document_fact_approval=False,
            production_policy_waiver=False,cache_admitted=False))
    assert len(rows)==8 and sum(len(r['approved_exact_flags']) for r in rows)==18
    for name,sha in pins.items():assert inv.file_sha(ROOT/name)==sha
    for path in [args.diagnostic.resolve(),AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V1.json',Path(__file__)]:
        pins[str(path.relative_to(ROOT))]=inv.file_sha(path)
    result=dict(status='EXACT_ROOT11_EIGHT_SOURCE_EIGHTEEN_NUMERICAL_CONTEXTS_REVIEWED',rows=rows,
        counts=dict(unique_sources=8,individually_reviewed_flags=18,unresolved_numeric_flags=0),
        input_pins=pins,scope='Only flagged atoms of these exact pairs; independent whole meaning and deletion preservation remain separate.',
        original_bodies_restricted=False,goal_complete=False,training_authorized=False)
    assert not args.output.exists()
    inv.write_json(args.output,result)
    print(json.dumps(result['counts']))

if __name__=='__main__':main()
