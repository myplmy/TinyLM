"""Source identities for reusing native features across calibration inventories."""


def reusable(new,old):
    required=('semantic_root_id','source_row_sha256','record_sha256','language')
    if any(k not in new or k not in old for k in required):raise ValueError('complete original source identity required')
    if new['semantic_root_id']!=old['semantic_root_id']:return False
    if any(new[k]!=old[k]for k in required):raise ValueError('same root has changed original source/record/language')
    if new['packed']['text']!=old['packed']['text']or new['teacher']['ids']!=old['teacher']['ids']:
        raise ValueError('same source must retain exact teacher input and original serialized text')
    if new['packed']['student']!=old['packed']['student']:
        raise ValueError('original student record/owner/one-shift metadata differs')
    return True
