"""Pick authoritative top-level metadata without decoding parent body fields."""
import guarded_scan_metadata_v1 as metadata


def matching_parent_metadata(line, hold_hashes):
    # A ledger may contain nested provenance hashes for unrelated dispositions.
    # Raw matches are only a prefilter; the byte projector owns top-level identity.
    matches = metadata.SOURCE_SHA.findall(line)
    if not any(value.decode('ascii').upper() in hold_hashes for value in matches):
        return None
    row = metadata.project_metadata(line)
    if row.get('original_text_sha256') not in hold_hashes:
        return None
    metadata.require(row.get('decision') == 'HOLD', 'HOLD hash also has a non-HOLD parent')
    return row
