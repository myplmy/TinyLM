"""Resolve only a byte-pinned frozen parent HOLD ledger without copying it."""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

SCHEMA = 'REFERENCE_ONLY_PARENT_HOLD_CENSUS_V1'


def resolve_reference(root, parent, document, read, file_sha):
    parent = Path(parent).resolve()
    reference = document['metadata_reference']
    assert document['metadata_reference_schema'] == SCHEMA
    assert reference['path'] == str((parent/'hold').relative_to(root))
    assert not (parent/'hold').is_symlink()
    assert file_sha(parent/'built.json') == reference['parent_built_sha256']
    built = read(parent/'built.json')
    assert document['manifest'] == built['manifests']['hold']
    assert document['pin']['parent_built_sha256'] == reference['parent_built_sha256']
    assert document['counts'] == {'documents':460695, 'input_ids':462874291}
    assert document['unprocessed'] == 0 and document['body_fields_decoded'] == 0
    assert document['source_metadata_enumeration']['every_position_identity_and_input_ids_recounted'] is True
    return parent/'hold'


@contextmanager
def bind_reference(cache, root, parent, census_path, document, file_sha):
    source = resolve_reference(root, parent, document, cache.read, file_sha)
    target = census_path.parent/'ledger'
    assert not target.exists(), 'a reference census must not also contain a copied ledger'
    original_verify = cache.verify
    original_verify(source, document['manifest'])

    def verify(directory, manifest):
        if Path(directory).resolve() == target.resolve():
            assert manifest == document['manifest']
            assert resolve_reference(root, parent, document, cache.read, file_sha) == source
            return original_verify(source, manifest)
        return original_verify(directory, manifest)

    with patch.object(cache, 'verify', verify):
        yield
    assert resolve_reference(root, parent, document, cache.read, file_sha) == source
