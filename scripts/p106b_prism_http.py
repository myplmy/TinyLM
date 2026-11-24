"""Bounded localhost-only Prism raw-probability admission; no server is started here."""
from __future__ import annotations

import json
import math
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler

ZERO_PROBABILITY_SENTINEL_CUTOFF = -1e30


class ProtocolHold(ValueError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ProtocolHold('owned localhost request must not redirect')


class PrismHTTP:
    def __init__(self, base, *, max_response_bytes=64_000_000, timeout=60):
        parsed = urlsplit(base)
        if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port
                or parsed.username or parsed.password or parsed.path not in ('','/')
                or parsed.query or parsed.fragment or type(max_response_bytes) is not int
                or not 1024 <= max_response_bytes <= 64_000_000 or not 0 < timeout <= 60):
            raise ProtocolHold('explicit bounded127.0.0.1 HTTP endpoint required')
        self.base = base.rstrip('/')
        self.limit = max_response_bytes
        self.timeout = timeout
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def request(self, route, payload=None):
        if route not in ('/health','/props','/tokenize','/detokenize','/completion'):
            raise ProtocolHold('unregistered local API route')
        data = None if payload is None else json.dumps(payload, allow_nan=False).encode('utf-8')
        if data is not None and len(data) > 1_000_000:
            raise ProtocolHold('owned request exceeds1MB')
        request = Request(self.base+route, data=data, headers={
            'Content-Type':'application/json', 'Accept-Encoding':'identity'})
        with self.opener.open(request, timeout=self.timeout) as response:
            body = response.read(self.limit+1)
        if len(body) > self.limit:
            raise ProtocolHold('owned response byte cap exceeded')
        def invalid(value):
            raise ProtocolHold('nonfinite JSON literal: '+value)
        return json.loads(body.decode('utf-8', errors='strict'), parse_constant=invalid)


def completion_request(prompt_ids, *, forced_token=None, n_probs=1):
    ids = list(prompt_ids)
    if (not ids or any(type(i) is not int or i < 0 for i in ids)
            or type(n_probs) is not int or n_probs < 1
            or forced_token is not None and (type(forced_token) is not int or forced_token < 0)):
        raise ProtocolHold('native nonnegative prompt/target IDs and positive raw-prob count required')
    result = dict(prompt=ids, n_predict=1, temperature=0., n_probs=n_probs,
        post_sampling_probs=False, cache_prompt=False, stream=False,
        top_k=0, top_p=1., min_p=0., typical_p=1., repeat_penalty=1.,
        frequency_penalty=0., presence_penalty=0., mirostat=0,
        dry_multiplier=0., xtc_probability=0., seed=1337)
    if forced_token is not None:
        result['logit_bias'] = [[forced_token,1_000_000.]]
    return result


def valid_logprob(value, *, allow_zero_sentinel=False):
    if (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value)
            or value > 0 or value <= ZERO_PROBABILITY_SENTINEL_CUTOFF and not allow_zero_sentinel):
        raise ProtocolHold('finite original raw logprob required; zero-probability sentinel is HOLD')
    return float(value)


def completion_probabilities(reply, *, vocab_size, expected_token=None, expected_top=1):
    entries = reply.get('completion_probabilities')
    if (reply.get('tokens_predicted') != 1 or reply.get('truncated') is not False
            or not isinstance(entries,list) or len(entries) != 1):
        raise ProtocolHold('one complete untruncated native next-token response required')
    main = entries[0]
    token = main.get('id')
    if type(token) is not int or not 0 <= token < vocab_size or expected_token is not None and token != expected_token:
        raise ProtocolHold('actual selected native token differs')
    logp = valid_logprob(main.get('logprob'))
    top = main.get('top_logprobs')
    if not isinstance(top,list) or len(top) != expected_top:
        raise ProtocolHold('exact raw top response count required')
    seen = set()
    for row in top:
        index = row.get('id')
        if type(index) is not int or not 0 <= index < vocab_size or index in seen:
            raise ProtocolHold('raw top native IDs are duplicate or outside vocabulary')
        seen.add(index)
        valid_logprob(row.get('logprob'),allow_zero_sentinel=True)
    return dict(token=token,logprob=logp,top=top)


def full_distribution(reply, *, vocab_size, mass_atol=5e-4):
    parsed = completion_probabilities(reply,vocab_size=vocab_size,expected_top=vocab_size)
    by_id = {row['id']:row['logprob'] for row in parsed['top']}
    if set(by_id) != set(range(vocab_size)):
        raise ProtocolHold('complete full-vocabulary denominator/ID coverage required')
    ordered = [row['logprob'] for row in parsed['top']]
    if any(left < right for left,right in zip(ordered,ordered[1:])):
        raise ProtocolHold('complete raw response must be sorted by original probability')
    if (not math.isclose(parsed['logprob'],by_id[parsed['token']],abs_tol=1e-5,rel_tol=1e-4)
            or not math.isclose(parsed['logprob'],max(by_id.values()),abs_tol=1e-5,rel_tol=1e-4)):
        raise ProtocolHold('unbiased selected token is not the original full-distribution greedy maximum')
    mass = math.fsum(math.exp(valid_logprob(value,allow_zero_sentinel=True)) for value in by_id.values())
    if abs(mass-1.) > mass_atol:
        raise ProtocolHold('original full-vocabulary probability mass differs')
    return dict(by_id=by_id,sorted_token_ids=[row['id'] for row in parsed['top']],mass=mass,
        zero_sentinel_count=sum(value <= ZERO_PROBABILITY_SENTINEL_CUTOFF for value in by_id.values()),
        greedy_token=parsed['token'],greedy_logprob=parsed['logprob'])


def compare_forced_to_full(forced, full, *, target, vocab_size, atol=1e-5, rtol=1e-4):
    response = completion_probabilities(forced,vocab_size=vocab_size,expected_token=target)
    original = valid_logprob(full['by_id'][target])
    passed = math.isclose(response['logprob'],original,abs_tol=atol,rel_tol=rtol)
    return dict(target=target,full_logprob=original,forced_logprob=response['logprob'],
        difference=abs(response['logprob']-original),atol=atol,rtol=rtol,passed=passed)
