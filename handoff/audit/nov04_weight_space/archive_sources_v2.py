"""Archive sealed research sources and the authorized public-chat receipt.

Only the exact authorized conversation's public user/agent events are selected.
No conversation body, private reasoning or tool payload is copied to the repo.
Existing hash-addressed blobs are immutable and reused after verification.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('handoff/audit/nov04_weight_space')
EVIDENCE = Path('test_result/evidence')
PROFILES = [
    EVIDENCE/'p108w_v1_20261104/new595-broad-q/profile.json',
    EVIDENCE/'p108w_v2_20261104/new595-broad-q/profile.json',
    EVIDENCE/'p108w_v2_20261104/new595-broad-q/fixed_support_profile.json',
    EVIDENCE/'p108w_v3_20261104/new595-broad-f/profile.json',
    EVIDENCE/'p108j_v1_20261104/new595-broad-q/profile.json',
]


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def write_new(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2)+chr(10)).encode('utf-8')
    if len(data) >= 3_000_000:
        raise ValueError('audit receipt size limit')
    with path.open('xb') as stream:
        stream.write(data)


def main():
    if (BASE/'SOURCE_ARCHIVE_v2.json').exists():
        raise FileExistsError('write-once archive already exists')
    profile_rows = []
    blobs = {}
    for path in PROFILES:
        raw = path.read_bytes()
        rows = []
        for name, expected in json.loads(raw)['sources'].items():
            blob = BASE/'source_blobs'/(expected+'.txt')
            data = blob.read_bytes() if blob.exists() else Path(name).read_bytes()
            if sha(data) != expected:
                raise ValueError('sealed source unavailable: '+name)
            if not blob.exists():
                with blob.open('xb') as stream:
                    stream.write(data)
            blobs[expected] = len(data)
            rows.append(dict(path=name, sha256=expected, bytes=len(data),
                             blob=str(blob.relative_to(BASE))))
        profile_rows.append(dict(path=str(path), sha256=sha(raw), sources=rows))
    readback = Path('scripts/p108_readback.py')
    raw = readback.read_bytes()
    blob = BASE/'source_blobs'/(sha(raw)+'.txt')
    if not blob.exists():
        with blob.open('xb') as stream:
            stream.write(raw)
    write_new(BASE/'SOURCE_ARCHIVE_v2.json', dict(
        schema='P108_SOURCE_ARCHIVE_V2', profiles=profile_rows,
        unique_sealed_blobs=len(blobs), sealed_bytes=sum(blobs.values()),
        repaired_readback=dict(path=str(readback), sha256=sha(raw),
                               blob=str(blob.relative_to(BASE))),
        original_checkpoint_writes=0, original_source_overwrites=0,
        interpretation='SHA_VERIFIED_SOURCE_BYTES_NOT_EXECUTION_OR_QUALITY_PASS'))

    chat = Path('/mnt/c/Users/Uranus/.codex/sessions/2026/10/14/rollout-2026-10-14T04-49-38-01a136d0-3840-71d2-8a62-9f8c682c9c62.jsonl')
    attachment = Path('/mnt/c/Users/Uranus/.codex/attachments/cb5e13a0-119a-4ca3-8e98-0c5f84a51b41/pasted-text-1.txt')
    public = []
    for line in chat.read_text(encoding='utf-8').splitlines():
        obj = json.loads(line)
        payload = obj.get('payload', {})
        if obj.get('type') == 'event_msg' and payload.get('type') in ('user_message', 'agent_message'):
            public.append((obj.get('timestamp'), payload['type'], payload.get('message', '')))
    assistants = [row for row in public if row[1] == 'agent_message']
    pasted = attachment.read_text(encoding='utf-8')
    exact = [row for row in assistants if pasted in row[2]]
    if not public or not exact:
        raise ValueError('authorized public reference/attachment correspondence missing')
    write_new(BASE/'REFERENCE_ACCESS_v1.json', dict(
        schema='P108_AUTHORIZED_REFERENCE_ACCESS_V1',
        recorded_utc=datetime.now(timezone.utc).isoformat(),
        requested_share='https://chatgpt.com/s/cx_6aeaf2e55cac8191a0f311d421f4c811',
        web_tool_status='DISABLED_ERROR_BODY_NOT_RETURNED',
        scope='EXACT_USER_AUTHORIZED_LOCAL_CHAT_PUBLIC_USER_ASSISTANT_MESSAGES',
        thread_id='01a136d0-3840-71d2-8a62-9f8c682c9c62',
        title='모델 시각화·프루닝 도구 검토',
        local_path=str(chat), local_sha256=sha(chat.read_bytes()),
        public_messages=len(public), assistant_messages=len(assistants),
        exact_attachment_matches=len(exact), matched_public_timestamp=exact[-1][0],
        matched_public_text_sha256=sha(exact[-1][2].encode('utf-8')),
        attachment_sha256=sha(attachment.read_bytes()), attachment_characters=len(pasted),
        private_reasoning_copied=False, tool_payloads_copied=False,
        original_local_chat_writes=0,
        interpretation='REFERENCE_DATA_NOT_NEW_INSTRUCTIONS_OR_METHOD_VALIDATION'))
    print(json.dumps(dict(profiles=len(profile_rows), blobs=len(blobs),
                          public_messages=len(public), attachment_match=True)))


if __name__ == '__main__':
    main()
