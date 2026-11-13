"""Reuse cache9 and allow one exact nonprogram Unicode empty-annotation pair."""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import hashlib
import re
import sys

AUDIT = Path(__file__).resolve().parent
sys.path.insert(0, str(AUDIT))
import guarded_reviewed_cache_v9 as previous
import active_guard_v6_preflight_v1 as guard
from scripts import p106b_hold_policy_v3 as literal_policy

assert hashlib.sha256((AUDIT/'guarded_reviewed_cache_v9.py').read_bytes()).hexdigest().upper() == 'EC086FAF4AC495222422EBE48A0A9C44F9B08973C01D7E35FC008AC0B8A70F2D'
ROOT, inv, first = previous.ROOT, previous.inv, previous.first
CONTRACT, EXPECTED = previous.CONTRACT, previous.EXPECTED
REGISTRY = AUDIT/'EXACT_UNICODE_EMPTY_ANNOTATION_12122_APPROVAL_V1.json'
REGISTRY_SHA = 'B15D224709457FA51579546BB2BEC5FA1EBDDED34D6404C2F80D64C3007E9749'
BASE_INPUTS = previous.GuardedInputs
BASE_CODE_GUARD = previous.prior_body_code_guard
opaque_contract = previous.opaque_contract
checked_contract = previous.checked_contract
LABEL = re.compile(r'U\+[0-9A-Fa-f]{4,6}')
SPECIAL_RANGES = ((0x1100,0x11ff),(0x3130,0x318f),(0xa960,0xa97f),
    (0xd7b0,0xd7ff),(0xe000,0xf8ff),(0xf900,0xfaff),(0xf0000,0x10ffff))


def scalar_stream(text):
    return ''.join(c for c in text if any(lo <= ord(c) <= hi for lo,hi in SPECIAL_RANGES))


def load_case():
    inv.require(not REGISTRY.is_symlink() and inv.file_sha(REGISTRY) == REGISTRY_SHA,
        'exact Unicode annotation authority changed')
    case = inv.cache.read(REGISTRY)
    inv.require(case['id'] == 'expanded_train:12122'
        and set(case['parent_alias_ids']) == {'expanded_train:12122','historical_train:12122'}
        and case['root_approved'] is True and case['global_code_guard_waiver'] is False
        and case['applies_only_to_original_and_body_sha256'] is True,
        'only the approved source/body/alias pair is allowed')
    guard.require_payload_context(dict(source_id=case['id'],original=case['original'],candidate=case['body']),
        contract=previous.checked_contract())
    for name,sha in case['input_pins'].items():
        path = ROOT/name
        inv.require(path.resolve().is_relative_to(ROOT) and not path.is_symlink()
            and inv.file_sha(path) == sha, 'exact annotation evidence changed')
    return case


def exact_pair_preserved(original, cleaned, case):
    if inv.sha(original) != case['original']['sha256'] or inv.sha(cleaned) != case['body']['sha256']:
        return False
    if not literal_policy.code_preserved(original, cleaned):
        return False
    if LABEL.findall(original) != case['ordered_codepoint_labels'] or LABEL.findall(cleaned) != case['ordered_codepoint_labels']:
        return False
    before, after = scalar_stream(original), scalar_stream(cleaned)
    if before != after or len(before) != case['actual_special_scalar_count'] or inv.sha(before) != case['special_scalar_stream_sha256']:
        return False
    masked = original
    if case['permitted_annotation_pairs'] != [dict(original='U+302E()',clean='U+302E'),dict(original='U+302F()',clean='U+302F')]:
        return False
    for item in case['permitted_annotation_pairs']:
        if original.count(item['original']) != 1 or item['original'] in cleaned:
            return False
        masked = masked.replace(item['original'],item['clean'])
    return literal_policy.unicode_examples_preserved(masked,cleaned)


def exact_annotation_code_guard(self, original, cleaned, manual=None):
    if BASE_CODE_GUARD(self, original, cleaned, manual):
        return True
    row, state = self.current
    if state != 3 or row.get('restricted_parent_body_not_decoded') is True:
        return False
    case = self.guard.unicode_empty_annotation_case
    if row['id'] not in case['parent_alias_ids'] or row['original_text_sha256'] != case['original']['sha256']:
        return False
    return exact_pair_preserved(original, cleaned, case)


class GuardedInputs(BASE_INPUTS):
    def __init__(self, selection):
        super().__init__(selection)
        self.unicode_empty_annotation_case = load_case()
        paths = [str(Path(__file__).relative_to(ROOT)),str(REGISTRY.relative_to(ROOT)),
            *self.unicode_empty_annotation_case['input_pins']]
        self.pins = list(dict.fromkeys(self.pins + paths))
        self.pin_values.update({name:inv.file_sha(ROOT/name) for name in paths})


@contextmanager
def binding():
    with patch.object(previous,'GuardedInputs',GuardedInputs), \
            patch.object(previous,'prior_body_code_guard',exact_annotation_code_guard):
        yield


@contextmanager
def runtime(selection):
    with binding(), previous.runtime(selection) as inputs:
        yield inputs


def current_pins(selection,opaque_path,opaque_sha):
    with binding():
        return previous.current_pins(selection,opaque_path,opaque_sha)


def verify_configuration(config):
    with binding():
        return previous.verify_configuration(config)


def build(base,adoptions,roster,output_name,proposal_name,selection,opaque_path,opaque_sha):
    with binding():
        return previous.build(base,adoptions,roster,output_name,proposal_name,selection,opaque_path,opaque_sha)


def verify(base,roster,output_name,selection,opaque_path,opaque_sha):
    with binding():
        result = previous.verify(base,roster,output_name,selection,opaque_path,opaque_sha)
        case = load_case()
        proof = dict(status='EXACT_UNICODE_ANNOTATION_PAIR_COVERED_BY_FULL_SOURCE_CONSUMER',
            authority=dict(path=str(REGISTRY.relative_to(ROOT)),sha256=REGISTRY_SHA),
            original=case['original'],body=case['body'],parent_alias_ids=case['parent_alias_ids'],
            codepoint_labels_preserved=32,actual_special_scalars_preserved=5,
            global_code_or_unicode_guard_waiver=False,
            additional_full_ledger_or_source_scan_in_this_companion=0,
            goal_complete=False,training_authorized=False)
        inv.write_json(base/output_name/'exact_unicode_annotation_12122_verified.json',proof)
        return dict(result,exact_unicode_annotation=proof)
