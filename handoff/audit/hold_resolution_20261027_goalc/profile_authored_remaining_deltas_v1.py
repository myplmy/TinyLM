"""Classify existing authored deltas once; never generate, edit or admit text."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse
import difflib
import json
import re
import sys
import time

AUDIT=Path(__file__).resolve().parent
ROOT=AUDIT.parents[2]
sys.path[:0]=[str(AUDIT),str(ROOT)]
import active_guard_v6_preflight_v1 as guard
from selection_metadata_store_v1 import SelectionStore
from verify_rule27_literal_delta_v1 import literal_stream,empty_eof_appendix
from authored_literal_readiness_v1 import deferrals
from close_remaining_heading_context_v1 import remaining_headings
from scripts import p106b_hold_resolution_policy_v32 as policy

WORD=re.compile(r'\w+',re.UNICODE)
NUMBER=re.compile(r'(?<!\w)[+−-]?\d+(?:[.,]\d+)*(?:[%‰])?')
FORMAL_GAP=re.compile(r'(?:함수|군|공간|벡터|상수|변수|집합)[ \t]+(?:은|는|을|를|에|의)[ \t]+|(?:여기서|이때)[ \t]+(?:는|은|을|를|와|과)[ \t]+')
POINTER=re.compile(r'(?:다음과 같|다음과 같이|다음 식|아래의 식|위의 식|위 식|주어진다|나타낼 수 있다)')
PARTICLE_PAIRS=[('은','는'),('이','가'),('을','를'),('으로','로')]


def particle_only(a,b):
    return any(len(a)>len(x)+1 and len(b)>len(y)+1 and
        ((a.endswith(x) and b.endswith(y) and a[:-len(x)]==b[:-len(y)]) or
         (a.endswith(y) and b.endswith(x) and a[:-len(y)]==b[:-len(x)]))
        for x,y in PARTICLE_PAIRS)


def describe(original,body):
    source=[m for m in WORD.finditer(original)]
    target=[m for m in WORD.finditer(body)]
    a=[m[0] for m in source];b=[m[0] for m in target]
    scalar=dict(source_word_atoms=len(a),body_word_atoms=len(b),
        original_numeric_tokens=sum(Counter(NUMBER.findall(original)).values()),
        body_numeric_tokens=sum(Counter(NUMBER.findall(body)).values()),
        whole_numeric_atoms_removed=dict(Counter(NUMBER.findall(original))-Counter(NUMBER.findall(body))),
        whole_numeric_atoms_added=dict(Counter(NUMBER.findall(body))-Counter(NUMBER.findall(original))))
    if literal_stream(empty_eof_appendix(original)[0])==literal_stream(empty_eof_appendix(body)[0]):
        return dict(scalar,kind='EXISTING_LITERAL_EQUAL',deleted_chunks=[],line_roles={})
    if a==b:
        return dict(scalar,kind='WORD_ATOMS_IDENTICAL_ONLY_OTHER_CHARACTERS_DIFFER',deleted_chunks=[],line_roles={})
    if len(a)+len(b)>24000:
        return dict(scalar,kind='LARGE_WORD_DIFF_NOT_RUN',deleted_chunks=[],line_roles={})
    additions=particle_changes=0
    deleted=[]
    role_counts=Counter()
    lines_seen=set()
    for tag,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
        if tag=='equal':
            continue
        if tag=='replace' and j-i==l-k==1 and particle_only(a[i],b[k]):
            particle_changes+=1;continue
        if k<l:
            additions+=l-k
        if i==j:
            continue
        lo=source[i].start();hi=source[j-1].end()
        left=original.rfind(chr(10),0,lo)+1
        right=original.find(chr(10),hi)
        right=len(original) if right<0 else right
        value=original[left:right]
        roles=[]
        if FORMAL_GAP.search(value):
            roles.append('EXPLICIT_LOCAL_FORMAL_ROLE_GAP')
        if POINTER.search(value):
            roles.append('FORMULA_POINTER_REQUIRES_CONTEXT')
        if policy.v1.normalize_heading(value.strip()) in policy.v1.LABELS:
            roles.append('SINGLE_HEADING_LINE_ROLE_NOT_YET_PROVED')
        if re.search(r'(?i)\b(?:log in|sign in|subscribe|cookies|privacy|buy now|add to cart)\b',value):
            roles.append('POSSIBLE_UI_REQUIRES_CONTEXT')
        if not roles:
            roles=['OTHER_SOURCE_WORD_DELETION']
        if (left,right) not in lines_seen:
            role_counts.update(roles);lines_seen.add((left,right))
        deleted.append(dict(source_characters=[lo,hi],source_line_characters=[left,right],
            source_line_sha256=guard.inv.sha(value),source_line_length=len(value),
            deleted_word_atoms=j-i,added_word_atoms=l-k,roles=roles))
    kind=('SOURCE_WORD_DELETIONS_ONLY' if not additions and not particle_changes else
          'DELETIONS_WITH_ONLY_PARTICLE_CHANGES' if not additions else 'ADDED_OR_REPLACED_SOURCE_WORDS')
    return dict(scalar,kind=kind,added_word_atoms=additions,particle_changes=particle_changes,
        deleted_chunks=deleted,line_roles=dict(role_counts))


def run(config_path):
    guard.activate();started=time.monotonic();pins={}
    config=json.loads(config_path.read_bytes())

    def read(path,expected=None):
        assert not path.is_symlink()
        raw=path.read_bytes();sha=guard.inv.file_sha(path)
        assert expected is None or sha==expected,str(path)
        pins[str(path.relative_to(ROOT))]=sha
        return json.loads(raw)

    stage=read(ROOT/config['stage']['path'],config['stage']['sha256'])
    selection=SelectionStore(AUDIT).read(ROOT/config['selection']['path'],config['selection']['sha256'])
    selected={row['original_text_sha256'] for row in selection['rows']}
    contract=guard.checked_contract()
    blocked_ids=set(contract['restricted_ids'])
    blocked_hashes=set(contract['restricted_hashes'])
    all_reviews=defaultdict(list);sources={}
    specs=stage['coverage']+[dict(cohort='root12_independent_admission_counter_v1',version='v39')]
    seen_specs=set()
    for spec in specs:
        pair=(spec['cohort'],spec['version'])
        if pair in seen_specs:
            continue
        seen_specs.add(pair)
        summary=read(guard.inv.BASE/(spec['cohort']+'_snapshots')/spec['version']/'complete.json')
        assert not summary['errors']
        manifest=read(guard.inv.BASE/spec['cohort']/'manifest.json')
        if spec['cohort']!='root12_independent_admission_counter_v1':
            sources.update({row['id']:row for row in manifest['rows']})
        for shard in summary['shards']:
            for row in read(ROOT/shard['path'],shard['sha256']):
                if row.get('decision')=='NEEDS_ROOT':
                    blocked_ids.add(row['id'])
                    if row.get('original'):
                        blocked_hashes.add(row['original']['sha256'])
                if row.get('original') and row.get('review') and not row.get('metadata_only'):
                    all_reviews[row['original']['sha256']].append(row)
    output=guard.inv.BASE/config['metadata_directory_name']
    assert not output.exists()
    writer=guard.inv.cache.ShardWriter(output,'delta_metadata',limit=3_999_999)
    counts=Counter();weights=Counter();roles=Counter();samples=defaultdict(list)
    for digest,items in all_reviews.items():
        if digest in selected:
            continue
        primary=[row for row in items if row['cohort']!='root12_independent_admission_counter_v1'
            and row.get('decision') in {'EDIT_TEXT','EDIT_RECIPE','KEEP_SOURCE','ADOPT_CANDIDATE'}
            and row.get('body') and row.get('clean_text_sha256')]
        if not primary:
            counts['NO_COMPLETED_PRIMARY_BODY']+=1;continue
        row=primary[0];source=sources[row['id']]
        if row['id'] in blocked_ids or digest in blocked_hashes or any(
            source[key]['sha256'] in blocked_hashes for key in ['original','candidate']):
            counts['INDIVIDUAL_OR_PROTECTED_HOLD_NO_PAYLOAD_READ']+=1;continue
        if len({item['clean_text_sha256'] for item in items if item.get('body') and item.get('clean_text_sha256')})!=1:
            counts['DIFFERENT_SAVED_BODIES_REQUIRE_CONTEXT']+=1;continue
        if not re.search(r'EOF|전체|전문|전량|끝|full',row.get('read_scope',''),re.I):
            counts['FULL_READ_CLAIM_NOT_ESTABLISHED']+=1;continue
        body=dict(path=row['body'],sha256=row['clean_text_sha256'])
        guard.require_payload_context(dict(source_id=row['id'],original=row['original'],candidate=body))
        values=[]
        for pin in [row['original'],body]:
            path=ROOT/pin['path']
            assert not path.is_symlink() and path.resolve().is_relative_to(guard.inv.BASE)
            raw=path.read_bytes()
            value=raw.decode('utf-8')
            assert guard.inv.sha(value)==pin['sha256']
            values.append(value)
        delta=describe(*values)
        remaining=sorted(set(deferrals(values[1])+policy.literal_holes(values[1])))
        headings=remaining_headings(values[1])
        for review in items:
            assert guard.inv.file_sha(ROOT/review['review']['path'])==review['review']['sha256']
        key=delta['kind']+(':NO_SCANNER_GAPS' if not remaining and not headings else ':REMAINING_CONTEXT_FLAGS')
        counts[key]+=1;weights[key]+=source['occurrences'];roles.update(delta['line_roles'])
        record=dict(id=row['id'],original=row['original'],body=body,occurrences=source['occurrences'],
            primary_review=row['review'],primary_cohort=row['cohort'],all_reviews=[item['review'] for item in items],
            reason=row['reason'],delta=delta,remaining_deferrals=remaining,remaining_headings=headings,
            root_approved=False,cache_admitted=False,additional_human_full_read_credit=0)
        writer.append(record)
        if len(samples[key])<3:
            samples[key].append(dict(id=row['id'],original=row['original'],body=body,primary_review=row['review']))
    guard.assert_no_protected_opens()
    for path in [config_path,Path(__file__),guard.CONTRACT,AUDIT/'AUTHORED_DELTA_PROFILE_SCOPE_V1.md']:
        pins[str(path.relative_to(ROOT))]=guard.inv.file_sha(path)
    manifest=writer.close(lineage=dict(input_pins=pins,root_admissions=0))
    report=dict(status='EXISTING_AUTHORED_DELTAS_PROFILED_NOT_ADMISSION',counts=dict(counts),
        positions=dict(weights),deleted_source_line_roles=dict(roles),examples=dict(samples),
        metadata_directory=str(output.relative_to(ROOT)),metadata_manifest=manifest,input_pins=pins,
        protected_payload_open_attempts=0,payload_bytes_copied=0,automatic_root_admissions=0,
        additional_human_full_read_credit=0,elapsed_seconds=time.monotonic()-started,
        goal_complete=False,training_authorized=False)
    path=AUDIT/config['report_name']
    assert not path.exists();guard.inv.write_json(path,report)
    print(json.dumps({k:v for k,v in report.items() if k not in {'examples','metadata_manifest','input_pins'}},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);args=parser.parse_args()
    path=Path(args.config).resolve()
    assert path.parent==AUDIT and not path.is_symlink()
    run(path)
