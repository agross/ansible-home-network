#!/usr/bin/env python3
"""Generate MiniMax image-01 images using only the Python standard library."""
import argparse
import base64
import binascii
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
import uuid

ENDPOINT = "https://api.minimax.io/v1/image_generation"


class ApiError(ValueError):
    """A MiniMax response failure with safe diagnostics."""


class PartialResultError(ValueError):
    """A local output failure after one or more images were saved."""

    def __init__(self, message, paths, requested):
        super().__init__(message)
        self.paths = paths
        self.requested = requested


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    source = p.add_mutually_exclusive_group(required=True)
    source.add_argument("--prompt")
    source.add_argument("--prompt-file", type=Path)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--aspect-ratio", choices=["1:1", "16:9", "4:3", "3:2", "2:3", "3:4", "9:16", "21:9"])
    p.add_argument("--width", type=int)
    p.add_argument("--height", type=int)
    p.add_argument("--count", type=int, default=1)
    p.add_argument("--seed", type=int)
    p.add_argument("--prompt-optimizer", action="store_true")
    p.add_argument("--reference-url", help="Public HTTPS URL of one character reference")
    p.add_argument("--timeout", type=float, default=180)
    return p


def payload(args):
    prompt = args.prompt_file.read_text(encoding="utf-8") if args.prompt_file else args.prompt
    if not prompt.strip() or len(prompt) > 1500:
        raise ValueError("Prompt must contain 1–1500 characters.")
    if not 1 <= args.count <= 9:
        raise ValueError("Count must be between 1 and 9.")
    if not 0 < args.timeout <= 600:
        raise ValueError("Timeout must be positive and at most 600 seconds.")
    body = dict(model="image-01", prompt=prompt, n=args.count,
                response_format="base64", prompt_optimizer=args.prompt_optimizer)
    if args.width is not None or args.height is not None:
        if args.aspect_ratio or any(v is None or not 512 <= v <= 2048 or v % 8 for v in (args.width, args.height)):
            raise ValueError("Supply both dimensions, 512–2048 divisible by 8, without aspect ratio.")
        body.update(width=args.width, height=args.height)
    else:
        body["aspect_ratio"] = args.aspect_ratio or "1:1"
    if args.seed is not None:
        if not -(2**63) <= args.seed < 2**63:
            raise ValueError("Seed must fit a signed 64-bit integer.")
        body["seed"] = args.seed
    if args.reference_url:
        if not args.reference_url.startswith("https://"):
            raise ValueError("Reference URL must use HTTPS.")
        body["subject_reference"] = [{"type": "character", "image_file": args.reference_url}]
    return body


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def api_error(result):
    response = result.get("base_resp", {})
    status = response.get("status_code")
    message = response.get("status_msg", "")
    trace_id = result.get("id", "")
    detail = f"MiniMax API failure; status_code={status!r}"
    if message:
        detail += f"; status_msg={message!r}"
    if trace_id:
        detail += f"; trace_id={trace_id!r}"
    return ApiError(detail + ". No retry performed.")


def image_extension(raw):
    if raw.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        return ".webp"
    raise ValueError("Unrecognized image format.")


def generate(body, output_dir, key, timeout):
    request = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(), headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=timeout) as response:
        result = json.load(response)
    if result.get("base_resp", {}).get("status_code") != 0:
        raise api_error(result)
    images = result.get("data", {}).get("image_base64", [])
    if not isinstance(images, list) or not images:
        raise ValueError("MiniMax returned no base64 images. No retry performed.")
    failed_count = int(result.get("metadata", {}).get("failed_count", 0))
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    prefix = uuid.uuid4().hex
    for index, encoded in enumerate(images, 1):
        try:
            raw = base64.b64decode(encoded, validate=True)
            extension = image_extension(raw)
            path = (output_dir / f"minimax-{prefix}-{index}{extension}").resolve()
            with path.open("xb") as stream:
                stream.write(raw)
            paths.append(str(path))
        except (binascii.Error, OSError, ValueError) as exc:
            if paths:
                raise PartialResultError(str(exc), paths, body["n"]) from exc
            raise
    partial = len(paths) != body["n"] or failed_count > 0
    return dict(paths=paths, requested=body["n"], received=len(paths), partial=partial)


def redact(message):
    return message.replace(os.environ.get("MINIMAX_API_KEY") or "\0", "[REDACTED]")


def main():
    args = parser().parse_args()
    try:
        body = payload(args)
        key = os.environ.get("MINIMAX_API_KEY", "").strip()
        if not key:
            raise ValueError("Set MINIMAX_API_KEY in the execution environment.")
        result = generate(body, args.output_dir, key, args.timeout)
        print(json.dumps(result, indent=2))
        return 2 if result["partial"] else 0
    except PartialResultError as exc:
        result = dict(paths=exc.paths, requested=exc.requested, received=len(exc.paths),
                      partial=True, error=redact(str(exc)))
        print(json.dumps(result, indent=2))
        return 2
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}; no retry performed.", file=sys.stderr)
    except (urllib.error.URLError, TimeoutError):
        print("Transport failure; generation/charge status unknown. No retry performed.", file=sys.stderr)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(redact(str(exc)), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
