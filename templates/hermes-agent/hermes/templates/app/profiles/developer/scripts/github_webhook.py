"""Dispatch GitHub webhooks to scripts, falling through to the route's skill."""

import json
import subprocess
import sys

from github_app_labels import provision


def reject_ineligible_pr_comment(payload):
    issue = payload.get("issue", {})
    if payload.get("action") != "created" or "comment" not in payload or "pull_request" not in issue:
        return None
    if issue.get("state") != "open" or not any(
        label["name"] == "ready-for-agent" for label in issue.get("labels", [])
    ):
        return {"__hermes_ignore__": True}
    return None


# Handlers return None when unhandled, or a Hermes payload when handled.
HANDLERS = (provision, reject_ineligible_pr_comment)


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
