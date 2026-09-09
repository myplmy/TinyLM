"""Loopback-only completions transport for the official BFCL OSS handler."""
from __future__ import annotations

import argparse
import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

from .artifacts import digest, fresh_dir, json_write, json_text, source_tree
from .harness_run import model_arguments, make_engine


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    model_arguments(parser)
    parser.add_argument("--port", type=int, default=1053)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("Use a non-privileged localhost port.")
    out = fresh_dir(args.output)
    engine = make_engine(args)
    # Metadata for upstream token counting ONLY; these are not converted model weights.
    from transformers import GPT2Config, PreTrainedTokenizerFast
    metadata_dir = out / "tokenizer"
    metadata_dir.mkdir()
    hf_tokenizer = PreTrainedTokenizerFast(
        tokenizer_object=engine.tokenizer, eos_token="<eos>",
        model_max_length=engine.max_length, clean_up_tokenization_spaces=False)
    hf_tokenizer.save_pretrained(metadata_dir)
    GPT2Config(vocab_size=engine.cfg.vocab_size, n_positions=engine.max_length,
               n_embd=8, n_layer=1, n_head=1,
               bos_token_id=engine.eos_id, eos_token_id=engine.eos_id).save_pretrained(metadata_dir)
    metadata_hash = source_tree(metadata_dir)["sha256"]
    identity = {"model": engine.identity, "tokenizer_metadata": str(metadata_dir.resolve()),
                "tokenizer_metadata_sha256": metadata_hash,
                "port": args.port, "endpoint": f"http://127.0.0.1:{args.port}/v1",
                "weights_exported": False, "transport": "non-streaming single completion"}
    identity["identity_digest"] = digest(identity)
    json_write(out / "server.json", identity)
    counters = {"successful_requests": 0, "failed_requests": 0}
    log = (out / "requests.jsonl").open("x", encoding="utf-8")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *arguments):
            pass

        def reply(self, status, body):
            payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == "/v1/models":
                self.reply(200, {"object": "list", "data": [
                    {"id": str(metadata_dir.resolve()), "object": "model", "owned_by": "local"}]})
            elif self.path == "/a16/identity":
                self.reply(200, {**identity, "counters": counters, "engine_stats": engine.stats})
            elif self.path == "/health":
                self.reply(200, {"status": "ok"})
            else:
                self.reply(404, {"error": "Unknown route"})

        def do_POST(self):
            if self.path != "/v1/completions":
                self.reply(404, {"error": "Only /v1/completions is supported."})
                return
            request_id = "a16-" + uuid.uuid4().hex
            request = None
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16 * 1024 * 1024:
                    raise ValueError("Invalid request body size.")
                request = json.loads(self.rfile.read(length))
                allowed = {"model", "prompt", "temperature", "max_tokens", "stop", "top_p",
                           "n", "stream", "echo", "logprobs", "seed",
                           "frequency_penalty", "presence_penalty"}
                if set(request) - allowed:
                    raise ValueError(f"Unsupported request fields: {sorted(set(request) - allowed)}")
                for name, expected in {"n": 1, "stream": False, "echo": False,
                                       "logprobs": None, "frequency_penalty": 0,
                                       "presence_penalty": 0}.items():
                    if request.get(name, expected) != expected:
                        raise ValueError(f"Unsupported {name}.")
                if "seed" in request and request["seed"] != engine.seed:
                    raise ValueError("Per-request seed overrides are not supported.")
                if not isinstance(request.get("prompt"), str):
                    raise ValueError("One string prompt is required.")
                if request.get("model") not in {"A16-TinyLM", str(metadata_dir.resolve())}:
                    raise ValueError("Request model differs from the recorded TinyLM endpoint.")
                info = engine.generate(
                    request["prompt"], request["max_tokens"], request.get("stop") or [],
                    float(request.get("temperature", 0)), float(request.get("top_p", 1)))
                counters["successful_requests"] += 1
                log.write(json_text({"id": request_id, "request": request, "response": info}) + "\n")
                log.flush()
                self.reply(200, {"id": request_id, "object": "text_completion",
                                "created": int(time.time()), "model": request["model"],
                                "choices": [{"index": 0, "text": info["text"], "logprobs": None,
                                             "finish_reason": "length" if info["finish_reason"] == "length"
                                                              else "stop"}],
                                "usage": {"prompt_tokens": info["prompt_tokens"],
                                          "completion_tokens": info["completion_tokens"],
                                          "total_tokens": info["prompt_tokens"] + info["completion_tokens"]}})
            except Exception as error:
                counters["failed_requests"] += 1
                log.write(json_text({"id": request_id, "request": request, "error": str(error)}) + "\n")
                log.flush()
                self.reply(400, {"error": {"message": str(error), "type": type(error).__name__}})

    server = HTTPServer(("127.0.0.1", args.port), Handler)
    print(f"A16 TinyLM endpoint: {identity['endpoint']} (stop with Ctrl+C)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        log.close()
        json_write(out / "stopped.json", {**counters, "engine_stats": engine.stats})
