"""Bind the actual full-read negative to unchanged source and draft bytes."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'


def pin(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(data).hexdigest().upper(), bytes=len(data))


manifest_path = BASE / 'remaining_field_title_page_006_counter_v1/manifest.json'
contract_path = AUDIT / 'GUARDED_SOURCE_METADATA_CONTRACT_V1.json'
manifest, contract = [json.loads(path.read_bytes()) for path in (manifest_path, contract_path)]
source = next(row for row in manifest['rows'] if row['id'] == 'expanded_train:85646')
assert source['id'] not in contract['restricted_ids']
assert source['original']['sha256'] not in contract['restricted_hashes']
original_path = ROOT / source['original']['path']
assert pin(original_path)['sha256'] == source['original']['sha256']
original = original_path.read_text(encoding='utf-8')
directory = BASE / 'agents/context_hangul/remaining_field_title_page_006_counter_v1'
draft_path = directory / 'expanded_train_85646_task019_v1.txt'
draft_pin = pin(draft_path)
assert draft_pin['sha256'] == '490EFE1EAE61D6EC3D9A6AA677A7744D04ACA3268A0889B44BD3320140E89119'
draft = draft_path.read_text(encoding='utf-8')
assert len(original) == 52391 and len(draft) == 32157
assert 'having a side-lobe level ripple dB below that of the main-lobe peak' in original
assert 'with a side-lobe level set by the ripple parameter' in draft
assert 'where is the desired window length, and can be interpreted as half' in original
assert 'Here M is the desired window length, and alpha is half' in draft
assert '- Take an -point DFT' in original and '- Take the DFT of the window.' in draft
assert 'where is a nonnegative integer.' in original
assert 'nonnegative integer' not in draft
note = AUDIT / 'ROOT_85646_V1_REQUIRES_REVISION.md'
result = dict(status='ONE_ACTUAL_FULL_READ_DRAFT_REQUIRES_REVISION_NOT_ADMITTED', id=source['id'],
              original=source['original'], candidate=source['candidate'], draft=draft_pin,
              original_characters=52391, draft_characters=32157,
              original_read_spans=[dict(characters=[0, 8000], chunk='408eaf'),
                                   dict(characters=[8000, 24000], chunk='9b0ada'),
                                   dict(characters=[24000, 42000], chunk='cc43ed'),
                                   dict(characters=[42000, 52391], chunk='f6dec4')],
              draft_read_spans=[dict(characters=[0, 8000], chunk='8d6d17'),
                                dict(characters=[8000, 32157], chunk='408eaf')],
              sidecar_full_read_chunk='8d6d17', requested_correction_units=7,
              whole_document_hold_not_requested=True, v2_review_pending=True,
              field006_snapshot_v5_is_not_root_admission=True,
              note=pin(note), sidecar=pin(directory / 'hold_85646_task019_v1.md'),
              input_pins=[pin(path) for path in (manifest_path, contract_path, Path(__file__).resolve())],
              root_authored_corpus_bodies=0, root_or_cache_adoptions=0,
              protected_body_reads=0, code_or_model_execution=0,
              external_fact_verification=False, goal_complete=False, training_authorized=False)
target = AUDIT / 'ROOT_85646_V1_NONADMISSION_V1.json'
with target.open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(status=result['status'], original_characters=52391,
                     v2_pending=True, root_or_cache_adoptions=0), ensure_ascii=False))
