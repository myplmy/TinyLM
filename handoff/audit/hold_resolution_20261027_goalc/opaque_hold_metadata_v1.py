"""Project unadopted HOLD bodies without classifying them as restricted."""
from guarded_scan_metadata_v1 import IDENT, SOURCE_SHA, IDENTITY_FIELDS, guarded_row, require


def guarded_or_opaque_row(data, *, restricted_ids, restricted_hashes,
                          restricted_metadata, hold_metadata, hold_hashes):
    require(isinstance(data, bytes), 'byte guard must precede body decode')
    ids = IDENT.findall(data)
    hashes = SOURCE_SHA.findall(data)
    require(len(ids) == 1 and len(hashes) <= 1, 'ambiguous predecode identity')
    ident = ids[0].decode('ascii')
    source_sha = hashes[0].decode('ascii').upper() if hashes else None
    restricted = ident in restricted_ids or source_sha in restricted_hashes
    opaque = ident in hold_metadata or source_sha in hold_hashes
    if not opaque:
        return guarded_row(data, restricted_ids=restricted_ids,
            restricted_hashes=restricted_hashes, trusted_metadata=restricted_metadata)
    require(ident in hold_metadata, 'unknown alias of an opaque HOLD source')
    expected = hold_metadata[ident]
    require(expected['parent_decision'] == 'HOLD' and
        source_sha == expected['original_text_sha256'], 'opaque HOLD identity changed')
    # The frozen parser skips text as bytes and validates the complete metadata
    # identity. Remove its restricted label when this is an ordinary HOLD.
    row = guarded_row(data, restricted_ids={ident}, restricted_hashes={source_sha},
                      trusted_metadata={ident: expected})
    if restricted:
        require(ident in restricted_metadata, 'restricted alias has no trusted metadata')
        for key in IDENTITY_FIELDS:
            require(expected[key] == restricted_metadata[ident][key],
                    'restricted and ordinary HOLD identities disagree')
    else:
        row.pop('restricted_parent_body_not_decoded')
    row['unadopted_hold_body_not_decoded'] = True
    return row


def validate_hold_outcome(row, state, proposal, value=None):
    if row.get('unadopted_hold_body_not_decoded') is not True:
        return
    require(state == 3 and row['text'] == '', 'opaque HOLD replaced an admitted parent')
    require(proposal['decision'] == 'HOLD' and not proposal.get('text') and
        not proposal.get('clean_text_sha256'), 'opaque body cannot be adopted')
    if value is not None:
        require(value[0] == 'HOLD' and value[1] == '', 'opaque HOLD outcome changed')
