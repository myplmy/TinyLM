"""Producer-owned answer rendering; not a semantic judge or JSON type guesser.

Only an explicit code-authored contract can request a transform. UNKNOWN keeps
the answer verbatim and never receives a JSON structure PASS. The schema is a
small, fail-closed subset, not a claim of full JSON Schema implementation.
"""
from __future__ import annotations
import copy
import json
import re

VERSION = 'P106B_PRODUCER_OUTPUT_V1'
KINDS = ('ANSWER_ENVELOPE', 'STRUCTURED_JSON', 'UNKNOWN')
PRODUCERS = ('gemma_task_v2', 'gemma_structure_fixture_v1')
SCHEMA_KEYS = {'type', 'properties', 'required', 'additionalProperties',
               'items', 'minItems', 'maxItems', 'enum'}
TYPES = {'object', 'array', 'string', 'integer', 'number', 'boolean', 'null'}


def contract(kind, *, producer='gemma_task_v2', schema=None):
    result = dict(version=VERSION, kind=kind, authority='producer_code', producer=producer)
    if schema is not None:
        result['schema'] = copy.deepcopy(schema)
    validate_contract(result)
    return result


def validate_schema(schema, depth=0):
    if (not isinstance(schema, dict) or depth > 12 or set(schema) - SCHEMA_KEYS
            or schema.get('type') not in TYPES):
        raise ValueError('unsupported bounded structure schema')
    kind = schema['type']
    if 'enum' in schema and (not isinstance(schema['enum'], list) or not schema['enum']):
        raise ValueError('enum must be a nonempty list')
    if kind == 'object':
        props, required = schema.get('properties', {}), schema.get('required', [])
        if (not isinstance(props, dict) or not all(isinstance(k, str) for k in props)
                or not isinstance(required, list) or not all(isinstance(k, str) for k in required)
                or len(set(required)) != len(required) or set(required) - set(props)
                or not isinstance(schema.get('additionalProperties', False), bool)
                or set(schema) & {'items', 'minItems', 'maxItems'}):
            raise ValueError('object schema fields differ')
        for value in props.values():
            validate_schema(value, depth + 1)
    elif kind == 'array':
        if 'items' not in schema or set(schema) & {'properties', 'required', 'additionalProperties'}:
            raise ValueError('array schema requires items')
        validate_schema(schema['items'], depth + 1)
        for key in ('minItems', 'maxItems'):
            if key in schema and (type(schema[key]) is not int or schema[key] < 0):
                raise ValueError('array count must be a nonnegative integer')
        if schema.get('minItems', 0) > schema.get('maxItems', 2**31):
            raise ValueError('array count range differs')
    elif set(schema) - {'type', 'enum'}:
        raise ValueError('scalar schema has unsupported fields')


def validate_contract(spec):
    if (not isinstance(spec, dict) or set(spec) - {'version', 'kind', 'authority', 'producer', 'schema'}
            or spec.get('version') != VERSION or spec.get('kind') not in KINDS
            or spec.get('authority') != 'producer_code' or spec.get('producer') not in PRODUCERS):
        raise ValueError('explicit trusted producer contract required')
    if spec['kind'] == 'STRUCTURED_JSON':
        validate_schema(spec.get('schema'))
        if spec['schema']['type'] not in ('object', 'array'):
            raise ValueError('structured task must declare object or array')
    elif 'schema' in spec:
        raise ValueError('schema applies only to a structured task')


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _constant(value):
    raise ValueError('nonfinite JSON number: ' + value)


def load_json(text):
    return json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant)


def unfence(text):
    text = text.strip()
    if text.startswith('```'):
        match = re.fullmatch(r'```(?:json)?[ \t]*\n([\s\S]*?)\n```', text)
        if match is None:
            raise ValueError('not one complete JSON fence')
        return match.group(1).strip(), True
    return text, False


def validate_value(value, schema, path='$'):
    kind = schema['type']
    correct = {'object': isinstance(value, dict), 'array': isinstance(value, list),
               'string': isinstance(value, str), 'integer': type(value) is int,
               'number': type(value) in (int, float), 'boolean': type(value) is bool,
               'null': value is None}[kind]
    if not correct:
        raise ValueError(path + ' requires ' + kind)
    if 'enum' in schema and not any(type(value) is type(v) and value == v for v in schema['enum']):
        raise ValueError(path + ' is outside declared enum')
    if kind == 'object':
        props = schema.get('properties', {})
        if set(schema.get('required', [])) - set(value):
            raise ValueError(path + ' required fields absent')
        if not schema.get('additionalProperties', False) and set(value) - set(props):
            raise ValueError(path + ' undeclared fields present')
        for name in value.keys() & props.keys():
            validate_value(value[name], props[name], path + '.' + name)
    if kind == 'array':
        if not schema.get('minItems', 0) <= len(value) <= schema.get('maxItems', 2**31):
            raise ValueError(path + ' array size differs')
        for index, item in enumerate(value):
            validate_value(item, schema['items'], path + '[' + str(index) + ']')


def render(answer, spec):
    validate_contract(spec)
    if not isinstance(answer, str) or not answer.strip():
        raise ValueError('nonempty teacher answer required')
    trace = dict(output_contract=copy.deepcopy(spec), original_teacher_answer=answer,
                 semantic_truth='NOT_REVIEWED', transform='NONE', structure_status='NOT_ASSESSED')
    if spec['kind'] == 'UNKNOWN':
        return answer, trace
    body, fenced = unfence(answer)
    if spec['kind'] == 'STRUCTURED_JSON':
        obj = load_json(body)
        validate_value(obj, spec['schema'])
        trace.update(transform='UNFENCE_JSON' if fenced else 'NORMALIZE_JSON', structure_status='DECLARED_STRUCTURE_PASS')
    else:
        try:
            value = load_json(body)
        except json.JSONDecodeError:
            # An attempted object/array/fenced JSON is never hidden inside a string.
            if fenced or body.startswith(('{', '[')):
                raise ValueError('malformed structured answer under simple contract')
            value = body
        if isinstance(value, dict):
            if set(value) != {'answer'} or isinstance(value['answer'], (dict, list)):
                raise ValueError('simple contract requires only scalar answer field')
            obj = value
            trace['transform'] = 'UNFENCE_ANSWER' if fenced else 'NORMALIZE_ANSWER'
        elif isinstance(value, list):
            raise ValueError('array answer is not a scalar answer envelope')
        else:
            obj = {'answer': value}
            trace['transform'] = 'RENDER_ANSWER_ENVELOPE'
        trace['structure_status'] = 'CODE_RENDERED_ENVELOPE'
    rendered = json.dumps(obj, ensure_ascii=False, allow_nan=False)
    trace['rendered_student_answer'] = rendered
    return rendered, trace
