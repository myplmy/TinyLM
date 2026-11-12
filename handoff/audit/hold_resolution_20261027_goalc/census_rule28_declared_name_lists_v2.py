"""Reverify the failed census and reuse its identical metadata shards read-only.

The first run finished source verification and wrote candidate metadata, then
failed at an obsolete914-outside-queue assumption. Nine later counter sources
were outside those old queues. Coverage is now checked against all pinned queue
identities. Every source/proposal is regenerated; every metadata row must equal
the existing failed-run row. No old row, original, body or shard is overwritten.
"""
from pathlib import Path
import hashlib
import json
import sys
from unittest.mock import patch

AUDIT=Path(__file__).resolve().parent;ROOT=AUDIT.parents[2]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

adapter=AUDIT/'census_rule28_declared_name_lists_v1.py';raw=adapter.read_bytes()
source=raw.decode('utf-8');anchor="exec(compile(code,str(frozen),'exec'),dict("
assert source.count(anchor)==1
scope=dict(__name__='prepare_rule28_existing_shard_replay',__file__=str(Path(__file__)))
exec(compile(source.split(anchor)[0],str(adapter),'exec'),scope)
code=scope['code']
before="assert not out.exists()"
assert code.count(before)==1
code=code.replace(before,"assert out.is_dir(), 'only reuse exact failed-run candidate metadata'")
before='seen, source_digests = set(), hashlib.sha256()'
assert code.count(before)==1
code=code.replace(before,before+chr(10)+'queued_source_hashes = set()')
before="            source_hash = row['original_text_sha256']"
assert code.count(before)==1
code=code.replace(before,before+chr(10)+'            queued_source_hashes.add(source_hash)')
before='assert len(seen)==len(hold_hashes)-914 and len(hold_hashes-seen)==914'
assert code.count(before)==1
code=code.replace(before,'assert seen == hold_hashes & queued_source_hashes')
before="automatic_root_admissions=0,cache_admitted=0,goal_complete=False,training_authorized=False)"
assert code.count(before)==1
code=code.replace(before,"existing_candidate_metadata_shards_reused_read_only=True,metadata_rows_recomputed_and_compared=True,"+before)
before='started = time.monotonic()'
assert code.count(before)==1
code=code.replace(before,"pins[str(REPLAY_ADAPTER.relative_to(ROOT))]=inv.file_sha(REPLAY_ADAPTER)"+chr(10)+before)


class ReadOnlyReplayWriter:
    def __init__(self,directory,prefix,limit):
        self.directory=Path(directory)
        assert self.directory.resolve()==(inv.BASE/'rule28_declared_name_list_census_v1').resolve()
        assert prefix=='candidate_metadata' and limit==3_999_999
        self.limit=limit;self.shards=[];self.rows=[];total=hashlib.sha256();self.size=0
        paths=sorted(self.directory.glob(prefix+'_*.jsonl'))
        assert paths and all(p.is_file() and not p.is_symlink() for p in paths)
        for index,path in enumerate(paths):
            assert path.name==prefix+'_'+str(index).zfill(6)+'.jsonl'
            payload=path.read_bytes();assert 0<len(payload)<=limit
            group=[json.loads(line) for line in payload.splitlines()]
            self.rows.extend(group);self.size+=len(payload);total.update(payload)
            self.shards.append(dict(path=path.name,bytes=len(payload),rows=len(group),
                sha256=hashlib.sha256(payload).hexdigest().upper()))
        self.concat=total.hexdigest().upper();self.cursor=0

    def append(self,row):
        assert self.cursor<len(self.rows),'unexpected extra regenerated row'
        assert row==self.rows[self.cursor],('failed-run row differs from regenerated source proof',row.get('id'))
        self.cursor+=1

    def close(self,lineage):
        assert self.cursor==len(self.rows),'failed-run shard contains unmatched rows'
        # Verify the read-only shard bytes once more before issuing the manifest.
        for shard in self.shards:
            path=self.directory/shard['path']
            assert inv.file_sha(path)==shard['sha256'] and path.stat().st_size==shard['bytes']
        return dict(schema='P106B_WRITE_ONCE_SHARDS_V1',limit_bytes=self.limit,rows=self.cursor,
            bytes=self.size,concat_sha256=self.concat,lineage=lineage,shards=self.shards)


with patch.object(inv.cache,'ShardWriter',ReadOnlyReplayWriter):
    exec(compile(code,str(scope['frozen']),'exec'),dict(__name__='rule28_reverified_existing_metadata_census',
        __file__=str(Path(__file__)),PRIOR_CENSUS=scope['prior'],PRIOR_CENSUS_PATH=scope['prior_path'],
        FROZEN_CENSUS_PATH=scope['frozen'],REPLAY_ADAPTER=adapter))
