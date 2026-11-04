"""Record only authorized visible conversation metadata; copy no chat bodies."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('handoff/audit/nov04_weight_space')


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def main():
    target = BASE/'REFERENCE_ACCESS_v1.json'
    if target.exists():
        raise FileExistsError(target)
    chat = Path('/mnt/c/Users/Uranus/.codex/sessions/2026/10/14/rollout-2026-10-14T04-49-38-01a136d0-3840-71d2-8a62-9f8c682c9c62.jsonl')
    attachment = Path('/mnt/c/Users/Uranus/.codex/attachments/cb5e13a0-119a-4ca3-8e98-0c5f84a51b41/pasted-text-1.txt')
    raw_chat, raw_attachment = chat.read_bytes(), attachment.read_bytes()
    pasted = attachment.read_text(encoding='utf-8')
    public = []
    for line in raw_chat.decode('utf-8').splitlines():
        obj = json.loads(line)
        msg = obj.get('payload', {})
        if obj.get('type') != 'response_item' or msg.get('type') != 'message':
            continue
        if msg.get('role') not in ('user', 'assistant'):
            continue
        if msg.get('channel') not in (None, 'final', 'commentary'):
            continue
        text = ''.join(c.get('text', '') for c in msg.get('content', [])
                       if c.get('type') in ('input_text', 'output_text'))
        public.append((obj.get('timestamp'), msg['role'], text))
    exact = [row for row in public if row[1] == 'assistant' and pasted in row[2]]
    if not exact:
        raise ValueError('public attachment correspondence missing')
    receipt = dict(schema='P108_AUTHORIZED_REFERENCE_ACCESS_V1',
        recorded_utc=datetime.now(timezone.utc).isoformat(),
        requested_share='https://chatgpt.com/s/cx_6aeaf2e55cac8191a0f311d421f4c811',
        web_tool_status='DISABLED_ERROR_BODY_NOT_RETURNED',
        scope='EXACT_USER_AUTHORIZED_LOCAL_CHAT_VISIBLE_MESSAGE_RECORDS',
        thread_id='01a136d0-3840-71d2-8a62-9f8c682c9c62',
        title='모델 시각화·프루닝 도구 검토', local_path=str(chat),
        local_sha256=sha(raw_chat), public_messages=len(public),
        assistant_messages=sum(row[1] == 'assistant' for row in public),
        exact_attachment_matches=len(exact), matched_public_timestamp=exact[-1][0],
        matched_public_text_sha256=sha(exact[-1][2].encode('utf-8')),
        attachment_sha256=sha(raw_attachment), attachment_characters=len(pasted),
        attachment_comparison='UNIVERSAL_NEWLINE_ONLY_RAW_BYTES_SEPARATELY_HASHED',
        private_reasoning_copied=False, tool_payloads_copied=False,
        original_local_chat_writes=0,
        interpretation='REFERENCE_DATA_NOT_NEW_INSTRUCTIONS_OR_METHOD_VALIDATION')
    data = (json.dumps(receipt, ensure_ascii=False, indent=2)+chr(10)).encode('utf-8')
    with target.open('xb') as stream:
        stream.write(data)
    print(json.dumps({k: receipt[k] for k in ('public_messages', 'assistant_messages', 'exact_attachment_matches', 'matched_public_timestamp')}))


if __name__ == '__main__':
    main()
