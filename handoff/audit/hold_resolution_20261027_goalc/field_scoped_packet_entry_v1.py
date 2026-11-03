"""Metadata guards before the unchanged, bounded single-role packet reader."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pinned(root, item):
    path = root / item['path']
    require(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()),
            'pinned metadata left trusted root')
    data = path.read_bytes()
    require(0 < len(data) < 20_000_000 and
            hashlib.sha256(data).hexdigest().upper() == item['sha256'], 'pinned metadata bytes changed')
    return data


def read_assigned(root, config_pin, role, page, source_id, packet, piece, piece_reader):
    config = json.loads(pinned(root, config_pin))
    require(config['schema'] == 'FIELD_SCOPED_SHORT_ENTRY_V1', 'wrong field entry schema')
    contract = json.loads(pinned(root, config['contract']))
    # ID is checked before even resolving a registry; SHA before packet-reader IO.
    require(source_id not in contract['restricted_ids'], 'restricted source ID; no packet read')
    require(role in config['roles'], 'role has no field assignment')
    require(isinstance(page, int) and str(page) in config['roles'][role], 'page outside assigned field scope')
    registry_pin = config['roles'][role][str(page)]
    registry = json.loads(pinned(root, registry_pin))
    require(registry['role'] == role and registry['page'] == page, 'registry role/page changed')
    require(source_id in registry['sources'] and source_id in registry['source_metadata'],
            'source outside this exact role/page')
    metadata = registry['source_metadata'][source_id]
    require(metadata['role'] == role, 'source role changed')
    require(metadata['original_sha256'] not in contract['restricted_hashes'],
            'restricted original SHA; no packet read')
    return piece_reader(root / registry_pin['path'], registry_pin['sha256'], root,
                        source_id, packet, piece)


def cli(root, role, config_pin):
    parser = argparse.ArgumentParser()
    parser.add_argument('--page', type=int, required=True)
    parser.add_argument('--source-id', required=True)
    parser.add_argument('--packet', type=int, required=True)
    parser.add_argument('--piece', type=int, default=1)
    args = parser.parse_args()
    config = json.loads(pinned(root, config_pin))
    helper_pin = config['helper']
    pinned(root, helper_pin)
    spec = importlib.util.spec_from_file_location('existing_scoped_packet_reader', root / helper_pin['path'])
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    row = read_assigned(root, config_pin, role, args.page, args.source_id,
                        args.packet, args.piece, helper.read_piece)
    print('APPROVED_PACKET_PIECE ' + json.dumps({k: v for k, v in row.items() if k != 'text'}, ensure_ascii=False))
    print(row['text'], end='')
    print(chr(10) + 'END_APPROVED_PACKET_PIECE')
