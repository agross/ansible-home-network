"""Dispatch GitHub webhooks to scripts, falling through to the route's skill."""

import json
import subprocess
import sys

from github_app_labels import provision


# Handlers return None when unhandled, or a Hermes payload when handled.
HANDLERS = (provision,)


def dispatch(payload):
    for handler in HANDLERS:
        result = handler(payload)
        if result is not None:
            return result
    return payload


def main():
    try:
        print(json.dumps(dispatch(json.load(sys.stdin))))
    except (KeyError, ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"GitHub webhook handler failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
