"""Read a bounded packet from a root-pinned, single-role registry."""
from pathlib import Path
import hashlib
import json

SLICE_CHARACTERS = 2000


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def read_piece(registry_path, registry_sha256, root, source_id, packet_number, piece_number):
    if registry_path.is_symlink() or not registry_path.resolve().is_relative_to(root.resolve()):
        raise ValueError('registry left the trusted root')
    registry_bytes = registry_path.read_bytes()
    if sha(registry_bytes) != registry_sha256:
        raise ValueError('root-pinned registry changed')
    registry = json.loads(registry_bytes)
    if source_id not in registry['sources']:
        raise ValueError('source is outside this role assignment')
    parts = registry['sources'][source_id]
    if not isinstance(packet_number, int) or not 1 <= packet_number <= len(parts):
        raise ValueError('packet number is outside the assigned sequence')
    if not isinstance(piece_number, int) or piece_number < 1:
        raise ValueError('invalid piece number')
    pin = parts[packet_number-1]
    path = root / pin['path']
    allowed = root / registry['allowed_packet_directory']
    if allowed.is_symlink() or not allowed.resolve().is_relative_to(root.resolve()):
        raise ValueError('packet directory left the trusted root')
    if path.is_symlink() or not path.resolve().is_relative_to(allowed.resolve()):
        raise ValueError('packet left the exact assigned directory')
    payload = path.read_bytes()
    if sha(payload) != pin['sha256']:
        raise ValueError('assigned packet bytes changed')
    text = payload.decode('utf-8')
    pieces = max(1, (len(text)+SLICE_CHARACTERS-1)//SLICE_CHARACTERS)
    if piece_number > pieces:
        raise ValueError('piece number is outside this packet')
    begin = (piece_number-1)*SLICE_CHARACTERS
    end = min(begin+SLICE_CHARACTERS, len(text))
    return dict(source_id=source_id, packet=packet_number, packets=len(parts),
        piece=piece_number, pieces=pieces, characters=[begin,end], total_characters=len(text),
        path=pin['path'], sha256=pin['sha256'], text=text[begin:end],
        packet_complete=piece_number==pieces,
        source_packet_sequence_complete=packet_number==len(parts) and piece_number==pieces)
