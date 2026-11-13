"""Provision workflow labels from a signed, profile-scoped installation webhook."""

import os
from pathlib import Path
import re
import subprocess

import yaml


LABELS = {
    "implementing": {
        "color": "29e884",
        "description": "Agent implementation is in progress.",
    },
    "in-review": {
        "color": "ededed",
        "description": "Agent review and any required repairs are in progress.",
    },
    "needs-human": {
        "color": "bf3c05",
        "description": "Human input, a decision, or final approval is required.",
    },
    "ready-for-agent": {
        "color": "aa46ed",
        "description": "Authorized and ready for the developer agent to work on.",
    },
}


def gh_app(repo, *args):
    return subprocess.run(
        ["gh-app", "--repo", repo, "--", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout


def provision(payload):
    installation = payload.get("installation", {})
    created = payload.get("action") == "created" and "account" in installation
    added = payload.get("action") == "added" and "repositories_added" in payload
    if not (created or added):
        return None

    # The routed profile selects credentials; never accept credentials from the event.
    home = Path(os.environ["HERMES_HOME"])
    config = yaml.safe_load((home / "config.yaml").read_text())["github_app"]
    owner = installation["account"]["login"]
    configured = {
        name.casefold(): str(value)
        for name, value in config["installation_ids"].items()
    }
    if configured.get(owner.casefold()) != str(installation["id"]):
        raise ValueError("Installation does not match the profile's configured owner")

    repositories = payload.get("repositories" if created else "repositories_added")
    if created and (repositories is None or installation.get("repository_selection") == "all"):
        # Paginate all-repository installations instead of relying on the event's list.
        names = gh_app(
            f"{owner}/_", "api", "--paginate", "installation/repositories",
            "--jq", ".repositories[].full_name",
        ).splitlines()
    else:
        names = [repo["full_name"] for repo in repositories]

    # Validate the complete batch before performing writes.
    names = list(dict.fromkeys(names))
    for name in names:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", name):
            raise ValueError("Invalid repository name")
        if name.split("/", 1)[0].casefold() != owner.casefold():
            raise ValueError("Repository owner does not match installation")
    for name in names:
        for label, settings in LABELS.items():
            gh_app(
                name, "label", "create", label, "--repo", name,
                "--color", settings["color"],
                "--description", settings["description"], "--force",
            )

    # Installation maintenance never starts an agent session.
    return {"__hermes_ignore__": True}
