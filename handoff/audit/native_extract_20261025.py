import json, hashlib
from pathlib import Path
import sys, time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
started=time.monotonic()
from collections import Counter
from scripts import p106b_admission as a, p106b_text_batches as b, p106b_publish_text_draft as pub
base=Path("data_cache/p106b_text_work_20261022")
old,oldart=a.checked_bundle(base/"root_closed_full/native_full_ko_000052_20261025/bundle")
packet_raw=(base/"packets/native_full_ko_000052.json").read_bytes();packet=json.loads(packet_raw)
proposal=json.loads(r"""{"pairs":{"36445":[["1975년 출생","21세기 성소수자 사람"]],"36453":[["1953년 출생","네덜란드에 거주한 대한민국인"]],"36527":[["대한민국의 텔레비전 감독","문화방송"]],"36589":[["같이 보기","같이 보기"]],"36739":[["1815년 출생","19세기 한국 사람"]],"36959":[["윤웅렬을 연기한 배우들","2001년 강만희 - 《명성황후》(KBS2 드라마)"],["1840년 출생","대한제국의 부장"]],"37347":[["조봉암을 연기한 배우들","한춘일 - 2003년 (야인시대) SBS 드라마"],["1898년 출생","20세기 대한민국 사람"]],"37623":[["자강도의 산","1000미터 봉우리"]],"37698":[["화학 원소 목록","화학 원소"]],"37746":[["같이 보기","같이 보기"]],"37754":[["같이 보기","같이 보기"]],"37863":[["가공의 남자","가공의 남자"]],"37864":[["설기현 시대 (2020년 ~ )","설기현 시대 (2020년 ~ )"],["FC","2006년 설립된 축구단"]],"37884":[["출연","미술: 타이조 카와시마"],["1970년 영화","아카데미 시각효과상 수상작"]],"38076":[["경력 목록","2021년 ~ 2022년 라이언 시티 세일러스 FC 감독"],["1970년 출생","싱가포르에 거주한 대한민국인"]],"38088":[["1933년 출생","폐암으로 죽은 사람"]],"38157":[["1990년 도입","일본의 거품 경제"]],"38389":[],"38579":[["언어별 점자","한국어의 표기법"]],"38637":[],"38648":[["외부 링크","조동화 - 스탯티즈"],["1981년 출생","한양 조씨"]],"38665":[["일본의 소설","밀리터리 SF 소설"]],"38753":[["이 문서는 우비흐어를 북서캅카스어족으로 분류하고, 아시아의 사어·러시아의 언어·튀르키예의 언어·교착어·포합어 항목에도 포함한다.","이 문서는 우비흐어를 북서캅카스어족으로 분류하고, 아시아의 사어·러시아의 언어·튀르키예의 언어·교착어·포합어 항목에도 포함한다."]],"39254":[["규격과 색상","역대 루마니아의 국기"]],"40020":[["외부 링크","외부 링크"],["1989년 영화","미국의 노예제를 소재로 한 영화"]],"40247":[["참조","참조"],["SBS의 예능 프로그램","2000년대 대한민국의 텔레비전 프로그램"]],"40257":[["1955년 출생","이탈리아에 거주한 대한민국인"]],"40296":[["각주","각주"],["1888년 출생","20세기 수필가"]],"40352":[["통산 기록","통산 기록"],["2023-24 코칭 스태프","코치 : 박종영 여오현"],["선수 명단","선수 명단"],["각주","각주"],["외부 링크","공식 페이스북"],["대한민국의 배구단","1983년 설립된 스포츠 클럽"]],"40492":[["인명","인명"],["같이 보기","같이 보기"]],"40508":[["학교 동문","학교 동문"],["역대 역임 교수","역대 역임 교수"],["서울특별시의 대학교","열린대학 교육협의회"]],"40590":[["같이 보기","같이 보기"]],"40742":[["연도별 타격 성적","굵은 글씨는 시즌 최고 성적.는 역대 최고성적."],["연도별 투수 성적","굵은 글씨는 시즌 최고 성적."],["각주","각주"],["외부 링크","Babe Ruth: Totally Random Trivia - slideshow by Life magazine"],["1895년 출생","아메리칸 리그 올스타"]],"40746":[],"40895":[["학교 동문","학교 동문"],["각주","각주"],["1948년 개교","중구역"]],"40897":[["1930년 출생","대한민국의 침례교도"]],"40900":[["1870년 출생","20세기 한국 사람"]],"40940":[["역대 선거 결과","역대 선거 결과"],["건국훈장 대통령장 수훈자","20세기 대한민국 사람"]],"40953":[["통산 기록","시즌 기록 중 굵은 글씨는 해당 시즌 최고 기록"],["각주","각주"],["외부 링크","김병현 사랑 모임"],["1979년 출생","21세기 대한민국 사람"]],"40983":[["각주","각주"],["무공훈장","대한민국의 군사훈장"]],"41020":[["외부 링크","외부 링크"],["전쟁 드라마 영화","체코슬로바키아를 배경으로 한 영화"]],"41021":[["각주","각주"],["1854년 출생","20세기 한국 사람"]],"41027":[["같이 보기","같이 보기"]],"41034":[["연도별 투수 성적","1998년, 2007년 ~ 2010년은 1군 출장 없음."],["각주","각주"],["외부 링크","외부 링크"],["1977년 출생","21세기 일본 사람"]],"41065":[["참고 자료","참고 자료"],["각주","각주"],["1854년 출생","당뇨병으로 죽은 사람"]],"41066":[["각주","각주"],["1881년 사망","19세기 한국 사람"]],"41097":[["생몰년 미상","창업군주"]],"41163":[["외부 링크","공식 웹사이트"],["미국의 SF 드라마","비디오 게임 등장인물"]],"41233":[["역대 선거 결과","역대 선거 결과"],["각주","각주"],["외부 링크","외부 링크"],["1896년 출생","20세기 대한민국 사람"]],"41235":[["각주","각주"],["1927년 출생","북미 사커 리그 (1968년)의 축구 감독"]],"41238":[["소식지","소식지"],["출신 인물","출신 인물"],["각주","각주"],["외부 링크","네이버 캐스트 : 신택리지 - 창원시"],["경상남도의 도시","대한민국의 항구 도시"]],"41414":[["857년 출생","10세기 사망"]],"41579":[["기본정보","제작년도 : 2002년"],["외부 링크","외부 링크"],["2002년 영화","영국의 공포 영화"]],"41722":[],"41728":[["같이 보기","같이 보기"]],"41760":[["대표팀","CAF"],["각주","각주"],["외부 링크","외부 링크"],["스포츠 의류 브랜드","2020년대 패션"]],"41876":[["1950년","1953년"],["한국 전쟁의 전투와 작전","전투 목록"]],"41920":[["1950년 한국 전쟁의 전투와 작전","1950년 6월"]],"41933":[["각주","각주"],["외부 링크","외부 링크"],["1970년 출생","21세기 대한민국 사람"]],"41947":[["각주","각주"],["외부 링크","외부 링크"],["1984년 출생","21세기 대한민국 사람"]],"41985":[["1972년 출생","대한민국의 불교도"]],"42092":[["출연 작품","국군교육방송 DEBS 열린세상 열린국군 진행"],["각주","각주"],["외부 링크","강희선 - 다음영화"],["1960년 출생","21세기 대한민국의 여자 성우"]],"42361":[["외부 링크","외부 링크"],["1972년 출생","21세기 대한민국 사람"]],"42400":[["AE","모음자"]],"42701":[["플레이 스타일","플레이 스타일"],["외부 링크","미하엘 발라크 - 프리미어리그 공식 홈페이지"],["1976년 출생","오버리가의 축구 선수"]],"42703":[["외부 링크","외부 링크"],["2002년 영화","CJ 엔터테인먼트 영화"]],"42721":[["각주","각주"],["1536년 출생","우의정"]],"42722":[["각주","각주"],["참고 문헌","참고 문헌"]],"42799":[["각주","각주"],["참고 문헌","참고 문헌"],["외부 링크","감자의 효능과 섭취방법"],["가지속","북아일랜드 요리"]],"42896":[["1919년 한국","1919년 시위"]],"43178":[],"43189":[["음률","음률"]],"43255":[["같이 보기","같이 보기"]],"43279":[["각주","각주"],["2006년 비디오 게임","2007년 비디오 게임"]],"43362":[["닌자 애니메이션","닌자를 소재로 한 애니메이션 영화"]],"43381":[["황후","황후"],["후궁","후궁"],["황자","황자"],["황녀","황녀"],["기년과 연호","기년과 연호"],["어여의 난","어여의 난"],["각주","각주"],["1360년 출생","15세기 중국의 군주"]]},"new_holds":[37460,40519,41495,41599,42368,42443,42723],"notes":"루나의 자연어 후보를 총괄이 실제 문맥과 대조해 범위를 좁혔다. 유용한 정의·명단·본문은 보존한다. 기존 보류45건과 별도 보류7건은 원문 유지하며 학습에 편입하지 않는다. 기존 후보와 새 정제 후보는 분리한다.","special_table_id":43279,"special_link_id":41920,"special_literal_edits":{"37698":[["바나듐 (Va, 23)","바나듐 (V, 23)","NIST 원자번호23과 기호V 개별 확인"]],"38579":[["(ᄡᅡ: )","","내용이 비어 있는 예시 괄호만 제거"]],"41920":[["[대한민국 7보병사단|[제7사단]]","제7사단","표시 문자열을 보존해 깨진 위키 링크 표시 제거"]],"43178":[["많이 사용되는 픽업의 조합은 다음과 같다.","","바로 뒤 조합 표가 누락된 문장만 제거"]]},"special_line_ranges":{"39254":[[20,21]],"43279":[[12,53],[59,82],[88,105],[112,129],[135,180]]}}""")
sources={x["id"]:x for x in packet["documents"]};candidates={x["source_id"]:x for x in old["candidates"]};holds={x["source_id"] for x in old["sources"] if x["author_hold"]}
assert len(sources)==len(candidates)==128 and len(holds)==45
assert set(map(int,proposal["pairs"]))|set(proposal["new_holds"])==set(sources)-holds
assert not(set(map(int,proposal["pairs"]))&set(proposal["new_holds"]))
rows=[];trace=[];counts=Counter();errors=[]
for sid,source in sources.items():
    original=source["text"];prior=candidates[sid]["payload"]["text"];cuts=[];literals=[]
    if sid in holds or sid in proposal["new_holds"]:
        after=original;decision="HOLD";reason="기존 원문 보류 유지" if sid in holds else "총괄이 불완전 문맥·깨진 구간·설명 없는 단편의 재구성이 필요하다고 보류했다. 내용을 추정하지 않고 원문을 유지한다."
    else:
        lines=b.lf_lines(prior);positions=[0]
        for line in lines:positions.append(positions[-1]+len(line))
        ranges=[]
        for first,last in proposal["pairs"][str(sid)]:
            aa=[i for i,x in enumerate(lines) if x.strip()==first];zz=[i for i,x in enumerate(lines) if x.strip()==last]
            assert len(aa)==len(zz)==1 and aa[0]<=zz[0],(sid,first,last,aa,zz)
            ranges.append((aa[0]+1,zz[0]+1,"문맥을 확인한 분류 꼬리·비어 있는 제목·단편 목록 제거"))
        for first,last in proposal.get("special_line_ranges",{}).get(str(sid),[]):
            if sid==43279:assert lines[first-1].strip()=="스탠스" and lines[first].lstrip().startswith("{|") and lines[last-1].strip()=="|}"
            if sid==39254:assert all(x.strip()=="국기" for x in lines[first-1:last])
            ranges.append((first,last,"개별 표와 제목 또는 분류 꼬리의 정확 위치 확인"))
        ranges.sort();assert all(x[1]<y[0] for x,y in zip(ranges,ranges[1:])),(sid,ranges)
        after=prior
        for first,last,note in reversed(ranges):
            i,j=positions[first-1],positions[last];removed=prior[i:j]
            cuts.append(dict(candidate_lines=[first,last],candidate_codepoints=[i,j],removed_sha256=b.sha(removed),removed_characters=len(removed),start=removed[:160],end=removed[-160:],reason=note))
            after=after[:i]+after[j:]
        for before,replacement,note in proposal.get("special_literal_edits",{}).get(str(sid),[]):
            assert after.count(before)==1,(sid,before,after.count(before))
            iterator=iter(before);assert all(any(c==x for c in iterator) for x in replacement),"literal edit must only remove characters"
            after=after.replace(before,replacement,1);literals.append(dict(before=before,after=replacement,reason=note))
        iterator=iter(prior);assert all(any(c==x for c in iterator) for x in after),"new extraction must be a subsequence of previous candidate"
        assert after.strip(),sid
        decision="KEEP" if after==original else "REWRITE"
        reason="총괄이 원문과 기존 후보·루나 판독을 대조했다. 유용한 본문·정의는 보존하고 실제로 내용이 비어 있는 제목, 문서 분류 꼬리, 원형 표/명단 단편을 문서별로 제거한다. 기존 문장 정제 이력은 아래 이전 후보 SHA로 연결한다. 의미 정답성 전수 검증이나 학습 편입을 뜻하지 않는다."
    lines=b.lf_lines(original)
    changes=[] if decision in ("HOLD","KEEP") else [dict(source_lines=[1,len(lines)],source_start=lines[0].strip()[:160],source_end=lines[-1].strip()[-160:],action="MOVE_TO_PROSE",replacement=after,reason=reason)]
    row=dict(id=sid,decision=decision,reason=reason,source_sha256=source["sha256"],changes=changes,training_admission="NOT_ADMITTED",root_revision="20261025_extract_v2",previous_bundle_sha256=oldart["sha256"],previous_candidate_sha256=candidates[sid]["candidate_sha256"])
    proof=pub.validate(packet,row,"native");assert proof["reconstructed_text_sha256"]==b.sha(after)
    rows.append(row);counts[decision]+=1
    trace.append(dict(source_id=sid,previous_candidate_sha256=candidates[sid]["candidate_sha256"],previous_payload_sha256=candidates[sid]["payload_sha256"],previous_characters=len(prior),new_text_sha256=b.sha(after),new_characters=len(after),decision=decision,old_author_hold=sid in holds,new_hold=sid in proposal["new_holds"],deleted_candidate_ranges=sorted(cuts,key=lambda x:x["candidate_lines"]),literal_edits=literals))
assert len(rows)==128 and counts["HOLD"]==52
print(json.dumps(dict(status="PREVIEW_VALIDATED_NOT_APPLIED",counts=counts,documents=len(rows),old_hold=len(holds),new_hold=len(proposal["new_holds"]),previous_bundle_sha256=oldart["sha256"],removed_characters_from_nonheld_candidates=sum(x["previous_characters"]-x["new_characters"] for x in trace if x["decision"]!="HOLD"),model_calls=0,gpu_calls=0,training_admission="NOT_ADMITTED"),ensure_ascii=False))
stem="native_full_ko_000052_extract_20261025"
packet_new=base/"packets"/(stem+".json")
closed=base/"root_closed_full"/(stem+"_v2")
scratch=base/"author_scratch/root_oct25"
assert not closed.exists() and not packet_new.exists()
assert all(not(scratch/(stem+"_"+str(x["id"])+".json")).exists() for x in rows)
assert not(base/"published"/stem).exists()
closed.mkdir(parents=True);scratch.mkdir(parents=True,exist_ok=True)
with packet_new.open("xb") as stream:stream.write(packet_raw)
b.write_json(closed/"root_proposal.json",dict(schema="P106B_ROOT_EXTRACT_PROPOSAL_20261025_V2",proposal=proposal,previous_bundle_sha256=oldart["sha256"],source_packet_sha256=hashlib.sha256(packet_raw).hexdigest().upper(),training_admission="NOT_ADMITTED",meaning_review="ROOT_CONTEXT_SELECTED_EXTRACTION_NOT_WHOLE_CORPUS_PASS",primary_symbol_reference="https://physics.nist.gov/PhysRefData/Handbook/Tables/vanadiumtable1.htm"))
b.write_json(closed/"extraction_trace.json",dict(schema="P106B_ROOT_NATIVE_EXTRACT_TRACE_20261025_V1",rows=trace))
entries=[]
for row in rows:
    inp=scratch/(stem+"_"+str(row["id"])+".json");b.write_json(inp,row)
    rc,receipt=pub.publish(str(packet_new),str(inp),"native",argv=["ROOT_NATIVE_EXTRACT_20261025",str(row["id"])])
    assert rc==0 and receipt["published_by_this_attempt"] is True,(row["id"],rc,receipt)
    entries.append(dict(source_id=row["id"],published=receipt["final"],receipt=str(Path(receipt["attempt"])/"receipt.json")))
index=closed/"publications.json"
b.write_json(index,dict(schema=a.PUBLICATIONS_SCHEMA,kind="native",parent_packet_sha256=hashlib.sha256(packet_raw).hexdigest().upper(),entries=entries))
report=b.import_packet(packet_new,base/"published"/stem,closed/"imported","native")
frozen=a.freeze(packet_new,closed/"imported",index,closed/"bundle")
new,newart=a.checked_bundle(closed/"bundle")
assert len(new["sources"])==len(new["candidates"])==128
assert sum(x["author_hold"] for x in new["sources"])==52
assert {x["source_id"] for x in new["sources"] if x["author_hold"]}==holds|set(proposal["new_holds"])
assert a.checked_bundle(base/"root_closed_full/native_full_ko_000052_20261025/bundle")[1]==oldart
assert (base/"packets/native_full_ko_000052.json").read_bytes()==packet_raw
readable=b.render_review(closed/"imported",closed/"original_and_candidates_readable.md")
new_candidates={x["source_id"]:x for x in new["candidates"]}
for item in trace:assert new_candidates[item["source_id"]]["payload"]["text"]==b.apply_positioned_edits(sources[item["source_id"]]["text"],next(r for r in rows if r["id"]==item["source_id"])["changes"])[0]
closure=dict(schema="P106B_ROOT_NATIVE_EXTRACT_CLOSURE_20261025_V1",status="FROZEN_STRUCTURAL_DRAFTS_NOT_ADMITTED",counts=dict(counts),source_count=128,previous_bundle=oldart,new_bundle=newart,unchanged_original_packet=True,unchanged_previous_bundle_and_artifacts=True,old_hold_count=45,new_hold_count=7,removed_characters_from_nonheld_candidates=sum(x["previous_characters"]-x["new_characters"] for x in trace if x["decision"]!="HOLD"),review_scope="Two Luna agents read83 candidate full texts; root read selected removal contexts and specific hold cases. Not full fact review.",academic_terms="No synonym replacement. One source-specific Va to V symbol correction checked against NIST atomic23.",full_corpus_semantic_review="NOT_COMPLETE",training_admission="NOT_ADMITTED",new_training_rows=0,gpu_calls=0,model_calls=0,wall_seconds=time.monotonic()-started,readable=readable)
b.write_json(closed/"closure.json",closure)
print(json.dumps(closure,ensure_ascii=False,sort_keys=True))

