"""Distinguish top-level source metadata from nested proof metadata."""
from pathlib import Path

AUDIT=Path(__file__).resolve().parent
source=(AUDIT/'prepare_full_resolution_join_plan_v2.py').read_text(encoding='utf-8')
before='''                inv.require(len(hashes) == 1, 'draft needs exactly one source SHA')
                key = hashes[0].decode('ascii').upper()'''
after='''                inv.require(hashes, 'draft source SHA is absent')
                # Proof objects can repeat this field. Only top-level metadata
                # identifies the row; source/candidate strings remain opaque.
                if len(hashes) == 1:
                    key = hashes[0].decode('ascii').upper()
                else:
                    key = metadata.project_metadata(line)['original_text_sha256']
                inv.require(isinstance(key,str) and len(key)==64,'draft source SHA is invalid')'''
assert source.count(before)==1
source=source.replace(before,after,1)
with (AUDIT/'materialize_full_resolution_join_plan_v3.py').open('x',encoding='utf-8') as stream:
    stream.write(source)
print('TOP_LEVEL_SOURCE_SHA_JOIN_PREPARED_FAILURE_V2_PRESERVED')
