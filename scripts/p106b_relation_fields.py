"""Producer-known fictional field graphs, semantic paraphrases and masked repair."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
import hashlib
import json
import random
from tinylm.chat.canonical import normalize,validate
VERSION='P106B_RELATION_FIELDS_V1'
FIELDS=('real_name','pen_name','book_title','birth_year','death_year','publication_year')
MODES=('repeat','paraphrase','switch','correct')
NAMES={
 'ko':{'train':['서준','민서','윤호','수빈','지민','하린','민재','예린','연우','지안','준호','서연','지우','시윤','도윤','나은','지후','아린','윤서','현우'],
       'dev':['채원','태윤','유빈','건우','수아','정우','하윤','민규'],
       'test':['예준','다인','세아','동하','라온','유하','도경','서율']},
 'en':{'train':['Nora','Evan','Mila','Owen','Iris','Leo','Alice','Mason','Clara','Felix','Daisy','Milo','Grace','Henry','Hazel','Noah','Lily','Oscar','Ruby','Theo'],
       'dev':['Ada','Blake','Cora','Dylan','Elena','Finn','Gemma','Hugo'],
       'test':['Alma','Briar','Cleo','Damon','Esme','Flora','Gavin','Heidi']}}
PENS={
 'ko':{'train':['푸른솔','새벽별','은빛강','하얀달','가을빛','여름숲','고운별','작은샘'],
       'dev':['산들빛','노을새','흰구름','풀잎달','파란들','아침돌','초록꿈','바다솔'],
       'test':['봄물결','은빛섬','새벽숲','고요별','솔내음','작은노을','여름돌','맑은샘']},
 'en':{'train':['BlueOak','DawnStar','SilverRiver','WhiteMoon','AutumnLight','SummerWood','KindStar','SmallSpring'],
       'dev':['HillLight','DuskBird','WhiteCloud','LeafMoon','BlueField','MorningStone','GreenDream','SeaPine'],
       'test':['SpringWave','SilverIsland','DawnWood','QuietStar','PineAir','SmallDusk','SummerStone','ClearSpring']}}
BOOKS={
 'ko':{'train':['바람의길','고요한강','여름의집','별의지도','가을노래','먼하늘','시간의정원','숲의기억'],
       'dev':['비오는언덕','바다의편지','새벽항구','봄의노트','느린시계','숲속우체국','낮의약속','작은등불'],
       'test':['달의계절','겨울의창','푸른정거장','은빛다리','먼여행','아침열차','강가의집','바람상자']},
 'en':{'train':['WindRoad','QuietRiver','SummerHouse','StarMap','AutumnSong','DistantSky','TimeGarden','ForestMemory'],
       'dev':['RainHill','SeaLetter','DawnHarbor','SpringNotes','SlowClock','ForestPost','DayPromise','SmallLamp'],
       'test':['MoonSeason','WinterWindow','BlueStation','SilverBridge','FarJourney','MorningTrain','RiverHouse','WindBox']}}
LABELS={'ko':dict(real_name='본명',pen_name='필명',book_title='책 제목',birth_year='출생연도',death_year='사망연도',publication_year='출판연도'),
        'en':dict(real_name='real name',pen_name='pen name',book_title='book title',birth_year='birth year',death_year='death year',publication_year='publication year')}


def sha(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest().upper()


def graph(index,split='train'):
    if split not in ('train','dev','test') or type(index) is not int or index<0:raise ValueError('declared split/index required')
    rng=random.Random(int(sha([VERSION,split,index])[:16],16));n=len(NAMES['ko'][split])
    names=rng.sample(range(n),2);pens=rng.sample(range(8),2);books=rng.sample(range(8),2);dates=set();people=[]
    for p in range(2):
        while True:
            birth=rng.randrange(1720,1935);publication=birth+rng.randrange(18,49);death=birth+rng.randrange(55,91)
            if not ({birth,publication,death}&dates):break
        dates.update((birth,publication,death))
        people.append(dict(name_id=names[p],pen_id=pens[p],book_id=books[p],birth_year=birth,publication_year=publication,death_year=death))
    keys=[(p,f) for p in range(2) for f in FIELDS];rng.shuffle(keys);base=rng.choice(keys)
    category=lambda f:'year' if f.endswith('_year') else 'name'
    candidates=[k for k in keys if k!=base and category(k[1])==category(base[1])]
    other=rng.choice(candidates)
    g=dict(version=VERSION,split=split,index=index,people=people,order=[list(k) for k in keys],base=list(base),other=list(other))
    g['root']=sha(g);return g


def values(g,language,person):
    if language not in ('ko','en'):raise ValueError('declared language')
    p=g['people'][person];s=g['split']
    return dict(real_name=NAMES[language][s][p['name_id']],pen_name=PENS[language][s][p['pen_id']],book_title=BOOKS[language][s][p['book_id']],
        birth_year=str(p['birth_year']),death_year=str(p['death_year']),publication_year=str(p['publication_year']))


def answer(g,language,key):
    person,field=key
    if person not in (0,1) or field not in FIELDS:raise ValueError('typed producer key')
    return values(g,language,person)[field]


def statement(g,language,key):
    p,f=key;v=values(g,language,p);name,pen,book=v['real_name'],v['pen_name'],v['book_title']
    if language=='ko':
        return {'real_name':f"책 '{book}'을 쓴 작가의 본명은 {name}입니다.",
            'pen_name':f"{name}은 {pen}이라는 필명으로 활동합니다.",
            'book_title':f"필명 {pen}으로 활동하는 작가가 쓴 책의 제목은 '{book}'입니다.",
            'birth_year':f"{name}은 {v['birth_year']}년에 태어났습니다.",
            'death_year':f"{name}은 {v['death_year']}년에 사망했습니다.",
            'publication_year':f"책 '{book}'은 {v['publication_year']}년에 출판되었습니다."}[f]
    return {'real_name':f"The real name of the writer of '{book}' is {name}.",
        'pen_name':f"{name} writes under the pen name {pen}.",
        'book_title':f"The book written under the pen name {pen} is titled '{book}'.",
        'birth_year':f"{name} was born in {v['birth_year']}.",
        'death_year':f"{name} died in {v['death_year']}.",
        'publication_year':f"The book '{book}' was published in {v['publication_year']}."}[f]


def question(g,language,key,style=0):
    p,f=key;v=values(g,language,p);name,pen,book=v['real_name'],v['pen_name'],v['book_title'];style=style%3
    if language=='ko':
        table={
         'real_name':[f"책 '{book}'을 쓴 작가의 본명만 답하세요.",f"'{book}'의 작가가 원래 쓰는 이름은 무엇인가요? 본명만 쓰세요.",f"저서 '{book}'의 작가 본명을 적으세요."],
         'pen_name':[f"{name}의 필명만 답하세요.",f"{name}이 작가로 활동할 때 쓰는 이름은 무엇인가요? 필명만 쓰세요.",f"{name}은 어떤 필명으로 활동하나요? 이름만 적으세요."],
         'book_title':[f"필명 {pen}으로 활동하는 작가의 책 제목만 답하세요.",f"{pen}이라는 필명을 쓰는 작가가 펴낸 책은 무엇인가요? 제목만 쓰세요.",f"{pen}이 쓴 책의 이름만 적으세요."],
         'birth_year':[f"{name}의 출생연도를 숫자 네 자리로만 답하세요.",f"{name}은 어느 해에 태어났나요? 연도 네 자리만 쓰세요.",f"{name}이 태어난 해를 숫자 네 자리로 적으세요."],
         'death_year':[f"{name}의 사망연도를 숫자 네 자리로만 답하세요.",f"{name}은 어느 해에 사망했나요? 연도 네 자리만 쓰세요.",f"{name}이 생을 마친 해를 숫자 네 자리로 적으세요."],
         'publication_year':[f"책 '{book}'의 출판연도를 숫자 네 자리로만 답하세요.",f"'{book}'은 어느 해에 출간됐나요? 연도 네 자리만 쓰세요.",f"'{book}'이 출판된 해를 숫자 네 자리로 적으세요."]}
    else:
        table={
         'real_name':[f"What is the real name of the author of '{book}'? Give only the name.",f"Name the writer of '{book}' by their real name only.",f"Which real name belongs to the author of '{book}'? Answer only the name."],
         'pen_name':[f"What pen name does {name} use? Give only the pen name.",f"Under which name does {name} write? Give only the pen name.",f"State only the pen name used by {name}."],
         'book_title':[f"What book was written under the pen name {pen}? Give only its title.",f"Name only the book by the writer who uses the pen name {pen}.",f"State only the title of the book written as {pen}."],
         'birth_year':[f"In which year was {name} born? Give only four digits.",f"State the birth year of {name} using only four digits.",f"What is the year of {name}'s birth? Answer with four digits only."],
         'death_year':[f"In which year did {name} die? Give only four digits.",f"State the death year of {name} using only four digits.",f"What is the year of {name}'s death? Answer with four digits only."],
         'publication_year':[f"In which year was '{book}' published? Give only four digits.",f"State the publication year of '{book}' using four digits only.",f"When did the book '{book}' come out? Give only its four-digit publication year."]}
    return table[f][style]


def field_label(g,language,key):
    p,f=key;v=values(g,language,p)
    return (v['real_name']+'의 '+LABELS['ko'][f]) if language=='ko' else (LABELS['en'][f]+' for '+v['real_name'])


def make(g,language,view,tok=None):
    if view not in range(4):raise ValueError('four declared views')
    if g!=graph(g['index'],g['split']):raise ValueError('exact producer graph/root required')
    mode=MODES[view];base=g['base'];other=g['other'];keys=g['order']
    prefix=('다음은 가상 작가에 관한 자료입니다. 실제 인물의 전기가 아닙니다. 자료에서 질문이 요청한 값만 답하세요.\n자료:\n' if language=='ko' else
        'These are fictional writers, not real biographies. Give only the value requested by the question, using this reference.\nReference:\n')
    facts=[statement(g,language,k) for k in keys];reference='\n'.join(facts);source_ranges=[];cursor=len(prefix)
    for fact in facts:source_ranges.append([cursor,cursor+len(fact)]);cursor+=len(fact)+1
    q0=question(g,language,base,0);q1=question(g,language,other if mode=='switch' else base,0 if mode=='repeat' else 1 if mode!='correct' else 2)
    a0=answer(g,language,other if mode=='correct' else base);a1=answer(g,language,other if mode=='switch' else base)
    if mode=='correct':
        wrong=('다른 작가의 ' if other[1]==base[1] else '')+LABELS['ko'][other[1]]
        wrong_en=('another writer\'s ' if other[1]==base[1] else '')+LABELS['en'][other[1]]
        feedback=(f"방금 답은 {wrong} 항목의 값입니다. 제가 묻는 항목은 {LABELS['ko'][base[1]]}입니다. 질문을 다시 확인해 주세요.\n" if language=='ko' else
            f"That answer gives the {wrong_en}. I am asking for the {LABELS['en'][base[1]]}. Please check the question again.\n")
        q1=feedback+q1
    if a1 in q1 or answer(g,language,base) in q0:raise ValueError('requested value leaked into question/feedback')
    scope=('앞서 제시된 가상 자료를 기준으로 답하세요.\n' if language=='ko' else 'Use the fictional reference provided earlier.\n')
    messages=[dict(role='user',content=prefix+reference+('\n질문:\n' if language=='ko' else '\nQuestion:\n')+q0),
        dict(role='assistant',content=a0),dict(role='user',content=scope+q1),dict(role='assistant',content=a1)]
    lookup={tuple(k):i for i,k in enumerate(keys)}
    labels=[None if mode=='correct' else lookup[tuple(base)],lookup[tuple(other if mode=='switch' else base)]]
    meta=dict(kind='fictional_relation_fields',source='code_graph_factory',version=VERSION,language=language,source_split=g['split'],
        semantic_root_id=g['root'],neutral_root=g['root'],producer_graph=copy.deepcopy(g),view=view,scenario=mode,
        user_reference_range=[len(prefix),len(prefix)+len(reference)],source_fact_ranges=source_ranges,source_fact_keys=keys,
        query_fact_labels=labels,supervised_assistant_turns=[2] if mode=='correct' else [1,2],
        rubric='PRODUCER_ATOMIC_VALUE',gold_value=a1,known_output_contract='FACTORY_FICTIONAL_FIELD_QUERY',
        correctness_scope='given fictional graph/declared templates only; not world knowledge',
        intentional_duplicate_allowed=mode in ('repeat','paraphrase'),wrong_first_answer_context_only=mode=='correct',teacher_calls=0)
    row=validate(normalize(dict(messages=messages,meta=meta)))
    if tok is not None:encode(row,tok)
    return row


def token_spans(offsets,ranges):
    result=[[] for _ in ranges];cursor=0
    for i,(x,y) in enumerate(offsets):
        if y<=x:continue
        while cursor<len(ranges) and x>=ranges[cursor][1]:cursor+=1
        j=cursor
        while j<len(ranges) and ranges[j][0]<y:
            a,b=ranges[j]
            if x<b and y>a:result[j].append(i)
            j+=1
    if any(not p for p in result):raise ValueError('source fact token positions absent')
    return result


def encode(row,tok):
    from tinylm.train import mtp_sft as core
    from tinylm.chat.serialize import serialize
    rec=core.encode_record(row,tok)
    if row['meta'].get('kind')!='fictional_relation_fields':return rec,None
    m=row['meta']
    if m['version']!=VERSION:raise ValueError('declared exact producer version')
    g=m['producer_graph'];expected=make(g,m['language'],m['view'])
    if row!=expected:raise ValueError('only exact producer conversation/metadata receives oracle labels')
    first_user=''.join(b['text'] for b in row['messages'][0]['content']);prefix=serialize(dict(messages=row['messages'][:1]),'chatml',add_generation_prompt=True)
    origin=prefix.index(first_user);offsets=tok.encode(prefix).offsets
    spans=token_spans(offsets,[(origin+a,origin+b) for a,b in m['source_fact_ranges']])
    queries=[]
    for turn,label in enumerate(m['query_fact_labels'],1):
        if label is None:continue
        positions=[i for i,(y,s) in enumerate(zip(rec.y,rec.segments)) if y!=-100 and s==turn]
        if not positions:raise ValueError('expected assistant predictor absent')
        q=positions[0];prompt=serialize(dict(messages=row['messages'][:2*turn-1]),'chatml',add_generation_prompt=True)
        if q!=len(tok.encode(prompt).ids)-1:raise ValueError('answer predictor differs from causal complete prefix')
        if any(max(p)>=q for p in spans):raise ValueError('source candidates must precede the answer predictor')
        queries.append(dict(position=q,label=label,turn=turn))
    allowed=set(m['supervised_assistant_turns'])
    rec=core.Record(rec.x,[y if s in allowed else -100 for y,s in zip(rec.y,rec.segments)],rec.segments)
    if not rec.targets or len(queries)!=len(allowed):raise ValueError('masked targets/query contract')
    if m['scenario']=='correct' and any(y!=-100 and s==1 for y,s in zip(rec.y,rec.segments)):raise ValueError('old wrong answer received word supervision')
    return rec,dict(spans=spans,queries=queries,root=m['neutral_root'],scenario=m['scenario'])
