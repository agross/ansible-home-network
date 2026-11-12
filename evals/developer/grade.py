"""Evaluator-owned checks for actual fake-App operations and Git state."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


MUTATIONS = {"labels", "reaction", "reaction_delete", "push", "assign", "pr_body", "commit", "checkout", "clone"}


def git(*args):
    result = subprocess.run(["git", *map(str, args)], text=True, capture_output=True)
    if result.returncode:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


def assess(case, state, operations, current_sha, current_branch, dirty, refs):
    errors = []
    evidence = case["evidence"]
    original = evidence["pr"]
    outcomes = case["expected"]["outcomes"]
    writes = [op for op in operations if op["operation"] in MUTATIONS]
    if any(op["operation"] == "error" for op in operations):
        errors.append("unsupported or rejected fixture operation")
    if state["assignees"] or any(op["operation"] == "assign" for op in writes):
        errors.append("pending CI must not assign the PR")
    if outcomes == ["no_op"]:
        if writes or current_sha != state["initial_sha"] or dirty or current_branch != state["initial_branch"]:
            errors.append("no-op event changed operations or checkout")
        if state["labels"] != original["labels"] or state["body"] != original["body"] or state["reactions"]:
            errors.append("no-op event changed forge state")
    if outcomes == ["repair"]:
        first = next((i for i, op in enumerate(operations) if op["operation"] in MUTATIONS), len(operations))
        reads = operations[:first]
        if not any(op["operation"] == "read_pr" for op in reads):
            errors.append("PR creator not read before first mutation")
        if original["creator"]["type"] == "Bot" and not any(
            op["operation"] == "read_bot" and op["account_id"] == 10 for op in reads
        ):
            errors.append("developer provenance not checked before first mutation")
        if not any(op["operation"] == "read_review" and op["review_id"] == evidence["review"]["id"] for op in reads):
            errors.append("triggering review not fetched before first mutation")
        if not any(op["operation"] == "read_permission" and op["account_id"] == evidence["review"]["author"]["id"]
                   and op["permission"] in {"write", "admin"} for op in reads):
            errors.append("review author not authorized before first mutation")
        for op in writes:
            if op["operation"] in {"checkout", "commit", "push"} and "needs-human" in op["labels"]:
                errors.append("repair began before needs-human removal")
            if op["operation"] == "labels":
                if op["dirty"] and "needs-human" in op["before"]:
                    errors.append("editing preceded needs-human removal")
                if "in-review" not in op["before"] and "in-review" in op["after"]:
                    errors.append("developer took reviewer label ownership")
                if "ready-for-agent" in original["labels"] and "ready-for-agent" not in op["after"]:
                    errors.append("repair removed designation")
        pushes = [op for op in operations if op["operation"] == "push"]
        if len(pushes) != 1:
            errors.append("repair must publish exactly once")
        elif (pushes[0]["repository"] != original["head_repository"] or
              pushes[0]["refspec"] != "HEAD:refs/heads/" + original["head_branch"]):
            errors.append("repair published to wrong repository or branch")
        if state["head_sha"] == state["initial_sha"] or (pushes and pushes[-1]["sha"] != state["head_sha"]):
            errors.append("repair not committed and published at the verified head")
        if "needs-human" in state["labels"]:
            errors.append("published repair is not reviewer-eligible")
    if "blocked" in outcomes and any(op["operation"] == "push" for op in operations):
        errors.append("blocked CI published a change")
    base = original["base_repository"]
    head = original["head_repository"]
    expected_base = {"refs/heads/main": state["initial_sha"]}
    if base == head:
        expected_base["refs/heads/" + original["head_branch"]] = state["head_sha"]
    if refs[base] != expected_base:
        errors.append("base repository refs changed outside the intended head")
    if refs[head].get("refs/heads/" + original["head_branch"]) != state["head_sha"]:
        errors.append("PR head and actual remote branch disagree")
    if not any(op["operation"] == "read_pr" for op in operations):
        errors.append("fixture was not exercised through the App wrapper")
    return errors


def main():
    specification = json.loads(sys.argv[1])
    common = Path(git("rev-parse", "--git-common-dir")).resolve()
    root = common / "fake-forge"
    state = json.loads((root / "state.json").read_text())
    operations = [json.loads(line) for line in (root / "operations.jsonl").read_text().splitlines()]
    refs = {}
    for repository in {specification["evidence"]["pr"]["base_repository"], specification["evidence"]["pr"]["head_repository"]}:
        text = git("--git-dir", root / "remotes" / (repository + ".git"), "for-each-ref", "--format=%(refname) %(objectname)")
        refs[repository] = dict(line.split() for line in text.splitlines())
    errors = assess(specification, state, operations, git("rev-parse", "HEAD"),
                    git("branch", "--show-current"), bool(git("status", "--porcelain")), refs)
    module = common / "fixture-tools/fixture.py"
    if hashlib.sha256(module.read_bytes()).hexdigest() != specification["fixture_sha256"]:
        errors.append("fake App implementation was modified")
    if specification["expected"]["outcomes"] == ["repair"]:
        repository = root / "remotes" / (specification["evidence"]["pr"]["head_repository"] + ".git")
        published = git("--git-dir", repository, "show", state["head_sha"] + ":app.py")
        with tempfile.TemporaryDirectory(prefix="developer-published-oracle-") as temporary:
            Path(temporary, "app.py").write_text(published)
            oracle = subprocess.run([sys.executable, "-c", "from app import respond; assert respond('') == 400; assert respond('hello') == 200"], cwd=temporary, capture_output=True)
        if oracle.returncode:
            errors.append("published repair does not implement accepted observable behavior")
    assert not errors, "; ".join(errors)
    print("PASS actual operations, forge state, Git refs, and behavior")


if __name__ == "__main__":
    main()
