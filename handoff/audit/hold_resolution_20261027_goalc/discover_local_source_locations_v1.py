"""User-requested, read-only metadata survey of exact pretraining source caches."""
from pathlib import Path
import datetime
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
locations = [
    'HF/datasets--wikimedia--wikipedia',
    'HF/datasets--HuggingFaceFW--fineweb-edu',
    'HF/hub/datasets--wikimedia--wikipedia',
    'HF/hub/datasets--HuggingFaceFW--fineweb-edu',
]
rows, surveys = [], []
for name in locations:
    base = ROOT / name
    if not base.is_dir() or base.is_symlink():
        surveys.append(dict(path=name, surveyed=False, reason='ABSENT_OR_ROOT_SYMLINK_NOT_FOLLOWED'))
        continue
    count = 0
    for parent, directories, files in os.walk(base, followlinks=False):
        directories[:] = sorted(value for value in directories if not (Path(parent) / value).is_symlink())
        for filename in sorted(files):
            path = Path(parent) / filename
            if filename.endswith('.lock'):
                continue
            record = dict(path=str(path.relative_to(ROOT)), symlink=path.is_symlink())
            resolved = path.resolve()
            if not resolved.is_relative_to(base.resolve()):
                record.update(status='EXTERNAL_SYMLINK_NOT_ACCESSED', bytes=None)
            elif not path.exists():
                record.update(status='BROKEN_LINK_NOT_READ', bytes=None)
            else:
                record.update(status='FILE_METADATA_ONLY', bytes=path.stat().st_size)
            record['potential_body_file'] = (record.get('bytes') or 0) >= 1000000 or path.suffix in {'.parquet', '.arrow', '.jsonl', '.xml', '.gz', '.bz2', '.zst'}
            rows.append(record)
            count += 1
    surveys.append(dict(path=name, surveyed=True, metadata_files=count, file_contents_read=False))
loader = ROOT / 'tinylm/data/prepare.py'
result = dict(status='BOUNDED_LOCAL_SOURCE_LOCATION_SURVEY_NOT_TEXT_RESTORE',
    user_direction='직접 작업경로 내 폴더 탐색해보기 바람',
    observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(), surveys=surveys, rows=rows,
    source_prepare_code=dict(path=str(loader.relative_to(ROOT)), sha256=hashlib.sha256(loader.read_bytes()).hexdigest().upper()),
    observed_prepare_contract=dict(streaming_line=178, encode_lines=[316, 727], stored_arrays_lines=[350, 351, 770, 771],
        text_key='text', raw_text_saved_by_observed_array_write_sites=False),
    protected_TinyDataset_accessed=False, model_weights_opened=False, evaluation_examples_opened=False,
    downloads=0, originals_changed=False, cache_admitted=0, goal_complete=False, training_authorized=False)
payload = json.dumps(result, ensure_ascii=False, indent=2) + chr(10)
assert len(payload.encode()) < 20000000
path = AUDIT / 'LOCAL_SOURCE_LOCATION_SURVEY_V1.json'
with path.open('x', encoding='utf-8') as stream:
    stream.write(payload)
print(json.dumps(dict(surveys=surveys, potential_body_files=[row for row in rows if row['potential_body_file']],
    metadata_files=len(rows), protected_TinyDataset_accessed=False, downloads=0), ensure_ascii=False))
