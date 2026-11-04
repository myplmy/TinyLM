"""Reuse V4 cache/consumer with the cumulative opaque metadata contract V3."""
from contextlib import contextmanager
from pathlib import Path
import sys
from unittest.mock import patch

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import guarded_reviewed_cache_v4 as previous

ROOT,inv=previous.ROOT,previous.inv
first=previous.previous.first
BASE_RUNTIME=previous.runtime
CONTRACT=AUDIT/'GUARDED_SOURCE_METADATA_CONTRACT_V3.json'
EXPECTED='7CF0AA8B46DDAED415851EE5F356B78EFBE12F33530B8217F028F86904594306'


def checked_contract():
    inv.require(inv.file_sha(CONTRACT)==EXPECTED,'cumulative metadata contract changed')
    data=inv.cache.read(CONTRACT)
    inv.require(len(data['restricted_ids'])==8 and len(data['restricted_hashes'])==9
        and len(data['trusted_metadata'])==13,'cumulative protection count differs')
    inv.require(data['new_restricted_entry']['parent_alias_ids']==
        ['expanded_train:28876','historical_train:28876'],'new protected aliases differ')
    inv.require(all(data['trusted_metadata'][key]['parent_decision']=='HOLD'
        for key in data['new_restricted_entry']['parent_alias_ids']),
        'new source had an admitted parent; explicit mediation required')
    return data


@contextmanager
def runtime(selection):
    contract=checked_contract()
    with patch.object(first,'CONTRACT',CONTRACT):
        with BASE_RUNTIME(selection) as inputs:
            inv.require(inputs.contract_sha==EXPECTED and inputs.metadata==contract['trusted_metadata'],
                'runtime did not load cumulative metadata')
            paths=[Path(__file__),CONTRACT,AUDIT/'GUARDED_CACHE_V5_SCOPE_V1.md',
                AUDIT/'ROOT12_INDEPENDENT_COUNTER_INPUTS_VERIFIED_V1.json']
            names=[str(path.relative_to(ROOT)) for path in paths]
            inputs.pins=list(dict.fromkeys(inputs.pins+names))
            inputs.pin_values.update({name:inv.file_sha(ROOT/name) for name in names})
            yield inputs


def build(base,adoptions,roster,output_name,proposal_name,selection):
    with runtime(selection):
        return first.reviewed.build(base,adoptions,roster,output_name,proposal_name)


def verify(base,roster,output_name,selection):
    with patch.object(previous,'runtime',runtime):
        return previous.verify(base,roster,output_name,selection)


def main():
    with patch.object(first,'build',build),patch.object(first,'verify',verify):
        return first.main()


if __name__=='__main__':main()
