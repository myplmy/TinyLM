"""Reuse cache8 engines with guard6, unchanged safe rows and exact filter aliases."""
from contextlib import contextmanager,ExitStack
from pathlib import Path
from unittest.mock import patch
import hashlib
import json
import sys

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import guarded_reviewed_cache_v8 as previous
import active_guard_v6_preflight_v1 as guard
import guarded_reviewed_cache_v1 as inner_runtime
from selection_metadata_store_v1 import SelectionStore,bound_selection_loads

assert hashlib.sha256((AUDIT/'guarded_reviewed_cache_v8.py').read_bytes()).hexdigest().upper()=='D4CAE978A3CAF42DC08053D86DCA726FE3DC1913D8DC3047BCDD47955B8389AA'
ROOT,inv,first=previous.ROOT,previous.inv,previous.first
CONTRACT,EXPECTED=guard.CONTRACT,guard.EXPECTED
backend=previous.previous
opaque_runtime=previous.guard4_runtime
opaque_contract=previous.opaque_contract
SAFE_IDS=previous.SAFE_IDS
BASE_RUNTIME=previous.BASE_RUNTIME
BASE_INPUTS=previous.GuardedInputs
_old_validate_selection=previous.validate_selection
_old_validate_aliases=previous.validate_new_aliases
ACTIVE_CONTRACT=None
PRIOR_SAFE_REGISTRY=AUDIT/'PRIOR_THREE_APPROVED_DERIVATIVES_METADATA_RUNTIME_V1.json'
PRIOR_SAFE_REGISTRY_SHA='A4B4A347C5E42C02DEAC11B68A71DC325EECCC0771E224CC440EADC7ACCCD1EB'
BASE_SAFE_CODE_GUARD=inner_runtime.GuardedResolutionEngine.code_guard


def prior_safe_registry():
    inv.require(inv.file_sha(PRIOR_SAFE_REGISTRY)==PRIOR_SAFE_REGISTRY_SHA,'prior exact derivative metadata changed')
    registry=inv.cache.read(PRIOR_SAFE_REGISTRY)
    inv.require({row['id'] for row in registry['rows']}==SAFE_IDS and len(registry['rows'])==3,
                'only exact three prior approved derivatives are reusable')
    inv.require(registry['source_or_compare_view_opens']==0 and registry['global_code_or_unicode_waiver'] is False,
                'source reopening or global guard waiver is not allowed')
    for name,sha in registry['input_pins'].items():
        path=ROOT/name
        inv.require(path.suffix!='.txt' and not path.is_symlink() and inv.file_sha(path)==sha,
                    'prior metadata evidence differs or requests a TXT')
    return registry


def initialize_prior_body_inputs(self,selection):
    """Keep original views absent; load only exact already approved derivatives."""
    self.selection_path=Path(selection)
    self.document=checked_contract()
    self.contract_sha=EXPECTED
    for name,sha in self.document['input_pins'].items():
        path=ROOT/name
        inv.require(path.suffix!='.txt' and inv.file_sha(path)==sha,'guard6 metadata evidence changed')
    self.metadata=self.document['trusted_metadata']
    self.restricted_ids=set(self.document['restricted_ids'])
    self.restricted_hashes=set(self.document['restricted_hashes'])
    self.safe={};self.safe_texts={};self.safe_clean_texts={}
    self.prior_safe_registry_pin=dict(path=str(PRIOR_SAFE_REGISTRY.relative_to(ROOT)),sha256=PRIOR_SAFE_REGISTRY_SHA)
    registry=prior_safe_registry();cases={row['id']:row for row in registry['rows']}
    self.pins=[str(CONTRACT.relative_to(ROOT)),str(self.selection_path.relative_to(ROOT)),
        str(Path(__file__).relative_to(ROOT)),str(PRIOR_SAFE_REGISTRY.relative_to(ROOT)),
        *registry['input_pins']]
    selections=inv.cache.read(self.selection_path)
    inv.require(selections['unresolved_sources']==0,'exact prior choices need a closed selection')
    for row in selections['rows']:
        if row['id'] not in SAFE_IDS:
            continue
        case=cases[row['id']];choice=row['selected'];key=row['original_text_sha256']
        row_sha=hashlib.sha256((json.dumps(row,ensure_ascii=False,separators=(',',':'))+chr(10)).encode()).hexdigest().upper()
        inv.require(row_sha==case['exact_selection_row_sha256'] and row.get('root_approved') is True
            and choice['decision']=='EDIT' and key==case['original_text_sha256']
            and choice['compare_source']==case['compare_source_metadata_only']
            and choice['body']==case['body']['path'] and choice['clean_text_sha256']==case['body']['sha256'],
            'prior exact source/view/body approval tuple changed')
        body=ROOT/choice['body']
        inv.require(not body.is_symlink() and body.resolve().is_relative_to(inv.BASE/'supplemental_rendered_v1')
            and body.name==choice['clean_text_sha256']+'.txt'
            and choice['clean_text_sha256'] not in self.restricted_hashes,
            'only the exact approved separate derivative can be opened')
        raw=body.read_bytes()
        inv.require(0<len(raw)<20_000_000 and hashlib.sha256(raw).hexdigest().upper()==choice['clean_text_sha256'],
                    'prior approved derivative body changed')
        clean=raw.decode('utf-8')
        self.safe[key]=dict(id=row['id'],view=choice['compare_source'],body=choice['body'],
            clean_text_sha256=choice['clean_text_sha256'],prior_source_preservation_evidence=self.prior_safe_registry_pin)
        self.safe_clean_texts[key]=clean
        self.pins.append(choice['body'])
    inv.require({row['id'] for row in self.safe.values()}==SAFE_IDS,'exactly three approved separate bodies required')
    self.pins=list(dict.fromkeys(self.pins))
    forbidden={case['compare_source_metadata_only']['path'] for case in cases.values()}
    inv.require(not forbidden&set(self.pins),'a prior source view entered current runtime hashes')
    self.pin_values={name:inv.file_sha(ROOT/name) for name in self.pins}


def prior_body_code_guard(self,original,cleaned,manual=None):
    row,state=self.current
    if row.get('restricted_parent_body_not_decoded') is not True:
        return BASE_SAFE_CODE_GUARD(self,original,cleaned,manual)
    inv.require(state==3 and original=='','restricted original must remain absent')
    inner_runtime.validate_outcome(row,'EDIT',cleaned,self.guard.safe)
    key=row['original_text_sha256']
    trusted=self.guard.metadata.get(row['id'])
    inv.require(trusted and trusted['original_text_sha256']==key,'unrecognized prior derivative alias')
    inv.require(self.guard.prior_safe_registry_pin['sha256']==PRIOR_SAFE_REGISTRY_SHA,
                'exact prior source-preservation proof missing')
    return cleaned==self.guard.safe_clean_texts[key] and inv.sha(cleaned)==self.guard.safe[key]['clean_text_sha256']


def checked_contract():
    if ACTIVE_CONTRACT is None:
        return guard.checked_contract()
    inv.require(inv.file_sha(CONTRACT)==EXPECTED,'active guard6 metadata changed')
    return ACTIVE_CONTRACT


def validate_selection(document,prior,contract):
    _old_validate_selection(document,prior,contract)
    prior_rows={row['id']:row for row in prior['rows']}
    restricted_ids=set(contract['restricted_ids'])
    restricted_hashes=set(contract['restricted_hashes'])
    new_filter=contract['actual_filter_metadata_hold']
    filter_ids=set(new_filter['parent_alias_ids'])
    filter_hashes={new_filter['original']['sha256']}|{pin['sha256'] for pin in new_filter['reading_parts']}
    for row in document['rows']:
        choice=row['selected']
        if (row['id'] in filter_ids or row['original_text_sha256'] in filter_hashes
                or choice.get('clean_text_sha256') in filter_hashes):
            inv.require(choice['decision']=='HOLD' and not choice.get('body') and not choice.get('clean_text_sha256'),
                        'new actual filter body/alias must remain metadata-only HOLD')
            continue
        if row['id'] in SAFE_IDS:
            inv.require(row==prior_rows[row['id']],'prior exact safe derivative changed')
            continue
        trusted=contract['trusted_metadata'].get(row['id'])
        if (choice['decision']=='EXCLUDE' and row==prior_rows.get(row['id']) and trusted
                and row.get('root_approved') is True
                and row['original_text_sha256']==trusted['original_text_sha256']):
            inv.require(not choice.get('body') and not choice.get('clean_text_sha256'),
                        'prior metadata exclusion unexpectedly contains a body')
            continue
        if (row['id'] in restricted_ids or row['original_text_sha256'] in restricted_hashes
                or choice.get('clean_text_sha256') in restricted_hashes):
            inv.require(choice['decision']=='HOLD' and not choice.get('body') and not choice.get('clean_text_sha256'),
                        'guard6 restricted original/candidate/alias cannot be selected')


def validate_new_aliases(opaque,contract):
    aliases=_old_validate_aliases(opaque,contract)
    entry=contract['actual_filter_metadata_hold']
    inv.require(entry['id']==guard.NEW_ID and entry['body_admission_approved'] is False,
                'actual filter metadata disposition differs')
    extra=set(entry['parent_alias_ids'])
    inv.require(extra=={guard.NEW_ID,guard.NEW_ALIAS} and not extra&aliases,
                'actual filter parent alias identity differs')
    for key in extra:
        expected=contract['trusted_metadata'][key]
        actual=opaque['trusted_hold_metadata'].get(key)
        inv.require(actual is not None and all(actual.get(name)==value for name,value in expected.items())
                    and actual.get('parent_decision')=='HOLD','actual filter opaque alias differs')
    inv.require(len(aliases|extra)==6,'expected exact six cumulative new parent aliases')
    return aliases|extra


@contextmanager
def active_contract():
    global ACTIVE_CONTRACT
    if ACTIVE_CONTRACT is not None:
        yield checked_contract()
        checked_contract()
        return
    guard.activate()
    contract=guard.checked_contract()
    ACTIVE_CONTRACT=contract
    try:
        with ExitStack() as stack:
            for module in [previous,opaque_runtime]:
                for name,value in [('CONTRACT',CONTRACT),('EXPECTED',EXPECTED),('checked_contract',checked_contract)]:
                    stack.enter_context(patch.object(module,name,value))
            stack.enter_context(patch.object(backend,'checked_contract',checked_contract))
            stack.enter_context(patch.object(previous,'validate_selection',validate_selection))
            stack.enter_context(patch.object(previous,'validate_new_aliases',validate_new_aliases))
            stack.enter_context(patch.object(inner_runtime.GuardedInputs,'__init__',initialize_prior_body_inputs))
            stack.enter_context(patch.object(inner_runtime.GuardedResolutionEngine,'code_guard',prior_body_code_guard))
            yield contract
            checked_contract()
    finally:
        ACTIVE_CONTRACT=None
        guard.assert_no_protected_opens()


class GuardedInputs(BASE_INPUTS):
    def __init__(self,selection):
        super().__init__(selection)
        contract=checked_contract()
        inv.require(self.contract_sha==EXPECTED and self.metadata==contract['trusted_metadata']
            and self.restricted_ids==set(contract['restricted_ids'])
            and self.restricted_hashes==set(contract['restricted_hashes']),
            'guard6 was not installed throughout reused runtime')
        paths=[Path(__file__),CONTRACT,AUDIT/'active_guard_v6_preflight_v1.py',
               AUDIT/'GUARDED_CACHE_V9_F3_F4_V1.md',AUDIT/'PRIOR_SAFE_DERIVATIVE_REUSE_F3_F4_V1.md',
               PRIOR_SAFE_REGISTRY]
        names=[str(path.relative_to(ROOT)) for path in paths]
        self.pins=list(dict.fromkeys(self.pins+names))
        self.pin_values.update({name:inv.file_sha(ROOT/name) for name in names})


@contextmanager
def runtime(selection):
    with active_contract() as contract:
        bindings=previous.selection_binding(selection,contract)
        with bound_selection_loads(bindings,directory=AUDIT),patch.object(backend,'GuardedInputs',GuardedInputs):
            with BASE_RUNTIME(selection) as inputs:
                yield inputs


def current_pins(selection,opaque_path,opaque_sha):
    with active_contract(),patch.object(backend,'runtime',runtime):
        return backend.current_pins(selection,opaque_path,opaque_sha)


def verify_configuration(config):
    with active_contract(),patch.object(backend,'runtime',runtime):
        return backend.verify_configuration(config)


def build(base,adoptions,roster,output_name,proposal_name,selection,opaque_path,opaque_sha):
    with active_contract(),patch.object(backend,'runtime',runtime):
        return backend.build(base,adoptions,roster,output_name,proposal_name,selection,opaque_path,opaque_sha)


def verify(base,roster,output_name,selection,opaque_path,opaque_sha):
    with active_contract(),patch.object(backend,'runtime',runtime):
        result=backend.verify(base,roster,output_name,selection,opaque_path,opaque_sha)
        registry=prior_safe_registry()
        proof=dict(status='EXACT_PRIOR_THREE_APPROVED_DERIVATIVES_REUSED_WITHOUT_SOURCE_VIEW_REOPEN',
            authority=dict(path=str(PRIOR_SAFE_REGISTRY.relative_to(ROOT)),sha256=PRIOR_SAFE_REGISTRY_SHA),
            source_view_payload_opens=0,source_view_hashes_recomputed=0,
            fresh_source_code_unicode_comparison_performed=False,past_source_preservation_proof_reused=True,
            current_exact_approved_body_identity_checked=True,
            bodies=[dict(id=row['id'],body=row['body']) for row in registry['rows']],
            global_code_guard_waiver=False,goal_complete=False,training_authorized=False)
        inv.write_json(base/output_name/'prior_safe_derivative_reuse_verified.json',proof)
        return dict(result,prior_safe_derivative_reuse=proof)
