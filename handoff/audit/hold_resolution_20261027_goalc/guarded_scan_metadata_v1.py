"""Project metadata without decoding a restricted row's original text field."""
import json
import re

IDENT = re.compile(rb'(?<!\\)"id"[ \t]*:[ \t]*"((?:expanded_train|historical_train|validation):[0-9]+)"')
SOURCE_SHA = re.compile(rb'(?<!\\)"original_text_sha256"[ \t]*:[ \t]*"([A-Fa-f0-9]{64})"')
FIELDS = {'id','ordinal','source','split','source_ids','source_ids_sha256','original_text_sha256',
          'input_ids','complete_eos','valid_utf8','original_signals','language_proxy','language_bucket',
          'candidate_text_sha256'}
IDENTITY_FIELDS = ('id','source','split','source_ids','source_ids_sha256','original_text_sha256','input_ids')


def require(value, message):
    if not value:
        raise ValueError(message)


def whitespace(data, index):
    while index < len(data) and data[index] in b' \t\r\n':
        index += 1
    return index


def string_end(data, index):
    require(index < len(data) and data[index] == 34, 'JSON string expected')
    index += 1
    while index < len(data):
        char = data[index]
        if char == 34:
            return index + 1
        if char == 92:
            index += 2
        else:
            index += 1
    raise ValueError('unterminated opaque JSON string')


def value_end(data, index):
    require(index < len(data), 'missing JSON value')
    if data[index] == 34:
        return string_end(data, index)
    if data[index] in (91,123):
        stack = [data[index]]
        index += 1
        while index < len(data):
            char = data[index]
            if char == 34:
                index = string_end(data, index)
                continue
            if char in (91,123):
                stack.append(char)
            elif char in (93,125):
                require(stack and ((stack[-1],char) in ((91,93),(123,125))), 'mismatched JSON metadata brackets')
                stack.pop()
                if not stack:
                    return index + 1
            index += 1
        raise ValueError('unterminated opaque JSON object or array')
    start = index
    while index < len(data) and data[index] not in b',}\r\n\t ':
        index += 1
    require(index > start, 'empty JSON scalar')
    return index


def project_metadata(data):
    """Read whitelisted top-level values; skip other values as opaque bytes."""
    require(isinstance(data,bytes), 'byte input is required before body decoding')
    index = whitespace(data,0)
    require(index < len(data) and data[index] == 123, 'top-level JSON object expected')
    index = whitespace(data,index+1)
    output, seen = {}, set()
    while index < len(data) and data[index] != 125:
        end = string_end(data,index)
        key = json.loads(data[index:end])
        require(isinstance(key,str) and key not in seen, 'duplicate metadata key')
        seen.add(key)
        index = whitespace(data,end)
        require(index < len(data) and data[index] == 58, 'metadata key has no colon')
        start = whitespace(data,index+1)
        end = value_end(data,start)
        if key in FIELDS:
            output[key] = json.loads(data[start:end])
        index = whitespace(data,end)
        require(index < len(data), 'unterminated metadata object')
        if data[index] == 125:
            break
        require(data[index] == 44, 'metadata fields need a comma')
        index = whitespace(data,index+1)
        require(index < len(data) and data[index] != 125, 'trailing metadata comma')
    require(index < len(data) and data[index] == 125
            and whitespace(data,index+1) == len(data), 'metadata object has a suffix or missing end')
    return output


def guarded_row(data, *, restricted_ids, restricted_hashes, trusted_metadata):
    """Return a regular row or an explicit metadata-only restricted projection.

    Restricted hashes include aliases at other EOS positions. Their metadata
    must be supplied from the frozen text-free source ledger before this call.
    No unrecognized restricted row falls back to whole-row JSON decoding.
    """
    require(isinstance(data,bytes), 'guard must run before UTF-8 or JSON body decoding')
    ids = IDENT.findall(data)
    require(len(ids) == 1, 'exactly one source ID is required before decoding')
    ident = ids[0].decode('ascii')
    hashes = SOURCE_SHA.findall(data)
    require(len(hashes) <= 1, 'multiple original source hashes')
    source_sha = hashes[0].decode('ascii').upper() if hashes else None
    blocked = ident in restricted_ids or source_sha in restricted_hashes
    if not blocked:
        row = json.loads(data)
        require(row['id'] == ident, 'byte guard ID differs from decoded ordinary row')
        return row
    require(source_sha is not None and ident in trusted_metadata, 'restricted source lacks frozen metadata')
    row = project_metadata(data)
    expected = trusted_metadata[ident]
    require(source_sha == row.get('original_text_sha256','').upper(), 'restricted source hash changed')
    for key in IDENTITY_FIELDS:
        require(key in row and key in expected and row[key] == expected[key],
                'restricted frozen source identity differs: ' + key)
    require(row.get('ordinal') == int(ident.rsplit(':',1)[1]), 'restricted ordinal differs')
    require(isinstance(row.get('complete_eos'),bool) and isinstance(row.get('valid_utf8'),bool),
            'restricted boundary metadata is missing')
    for key in ['original_signals','language_proxy']:
        value = row.get(key)
        require(isinstance(value,dict) and all(isinstance(name,str) and type(count) is int and count >= 0
                for name,count in value.items()), 'restricted signal metadata is missing or not numeric')
    # This is an explicit absent body, not a claim that the original was empty.
    # The cache adapter must prohibit KEEP/SOURCE_SLICE for this projection.
    row.update(text='',restricted_parent_body_not_decoded=True,
               original_text_sha256_is_frozen_metadata=True)
    return row
