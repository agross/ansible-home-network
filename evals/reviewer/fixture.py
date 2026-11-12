"""Finite reviewer GitHub fixture with revision races and real operation receipts."""

import json
import os
from pathlib import Path
import subprocess
import sys


BOT = {"id": 20, "login": "reviewer[bot]", "type": "Bot"}
DEVELOPER = {"id": 10, "login": "developer[bot]", "type": "Bot"}
URL = "https://github.com/example/project/pull/42"


def git(*args):
    result = subprocess.run(["git", *map(str, args)], text=True, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr)
    return result.stdout.strip()


def directory():
    if Path(__file__).parent.name == "fixture-tools":
        return Path(__file__).resolve().parents[1] / "fake-forge"
    return Path(git("rev-parse", "--git-common-dir")).resolve() / "fake-forge"


def load():
    return json.loads((directory() / "state.json").read_text())


def save(state):
    (directory() / "state.json").write_text(json.dumps(state, indent=2))


def record(state, operation, **details):
    with (directory() / "operations.jsonl").open("a") as file:
        file.write(json.dumps({"operation": operation, "head": state["head"],
                               "merge_base": state["merge_base"], **details}) + "\n")


def existing_review(state):
    return {"id": 100, "user": BOT, "commit_id": state["initial_head"], "state": "COMMENTED",
            "body": f"<!-- hermes-reviewer: reviewed-sha={state['initial_head']} state={state['verdict']} -->\n"
                    f"<!-- hermes-review-basis: base-ref=main merge-base={state['history'][0]} -->\n"
                    "<!-- hermes-review-receipt: key=existing -->\nVerified prior review.",
            "html_url": URL + "#pullrequestreview-100", "comments": []}


def setup(name):
    metadata = Path(git("rev-parse", "--git-common-dir")).resolve()
    (metadata / "fixture-tools").mkdir()
    (metadata / "fixture-tools/fixture.py").write_bytes(Path(__file__).read_bytes())
    root = metadata / "fake-forge"
    root.mkdir()
    history = git("rev-list", "--reverse", "HEAD").splitlines()
    state = {"name": name, "history": history, "head": history[-1], "initial_head": history[-1],
             "merge_base": history[0], "base_tip": history[0], "base_ref": "main", "scans": 0,
             "labels": ["ready-for-agent", "role:api"], "issue_labels": ["ready-for-agent", "role:api"],
             "reactions": [{"id": 1, "content": "heart", "user": {"id": 99, "login": "human"}}],
             "reviews": [], "threads": [], "failed_label": False, "publication_attempts": 0,
             "verdict": "changes-requested" if name in {"unfixed_human_thread_stays_actionable", "concurrent_result_prevents_duplicate_comments", "new_findings_publish_one_pinned_batch", "renovate_findings_publish_without_developer_delegation"} else "clean"}
    if name == "configured_app_identity_mismatch_blocks_before_writes":
        state["authenticated_app_slug"] = "agross-reviewer"
    if name.startswith("renovate_"):
        state["pr_author"] = {"id": 40, "login": "renovate[bot]", "type": "Bot"}
        state["pr_body"] = "Update dependency. Preserve the documented API contract."
        state["labels"] = ["role:api"]
    git("config", "user.name", "Fixture")
    git("config", "user.email", "fixture@example.invalid")
    state["target_advance"] = git("commit-tree", history[0] + "^{tree}", "-p", history[0], "-m", "Unrelated target advance")
    if name in {"verified_app_and_human_threads_are_resolved", "unfixed_human_thread_stays_actionable"}:
        authors = [("HUMAN_THREAD", "human")]
        if name == "verified_app_and_human_threads_are_resolved":
            authors.insert(0, ("APP_THREAD", "reviewer[bot]"))
        state["threads"] = [{"id": identifier, "isResolved": False, "comments": {
            "nodes": [{"id": identifier + "_COMMENT", "body": "Empty input must return HTTP 400 with a regression test.",
                       "path": "app.py", "author": {"login": author}}], "pageInfo": {"hasNextPage": False}}}
            for identifier, author in authors]
    if name in {"existing_marker_recovers_missing_finalization", "completed_marker_is_idempotent"}:
        state["reviews"] = [existing_review(state)]
        state["labels"] += ["in-review"]
        state["issue_labels"] += ["in-review"]
        state["reactions"].append({"id": 2, "content": "eyes", "user": BOT})
    if name == "completed_marker_is_idempotent":
        complete_state(state)
    save(state)
    (root / "operations.jsonl").write_text("")


def complete_state(state):
    state["labels"] = ["ready-for-agent", "role:api", "needs-human" if state["verdict"] == "clean" else "in-review"]
    state["issue_labels"] = ["ready-for-agent", "role:api"] + (["in-review"] if state["verdict"] != "clean" else [])
    state["reactions"] = [item for item in state["reactions"] if item["user"]["id"] != 20]
    state["reactions"].append({"id": 3, "content": "+1" if state["verdict"] == "clean" else "-1", "user": BOT})


def pr(state):
    return {"number": 42, "state": "open", "draft": False, "user": state.get("pr_author", dict(DEVELOPER, login=state.get("developer_app_slug", "developer") + "[bot]")),
            "body": state.get("pr_body", "<!-- hermes-origin: developer -->\n<!-- hermes-issue: example/project#7 -->"),
            "html_url": URL, "url": URL, "author": state.get("pr_author", DEVELOPER),
            "headRefOid": state["head"], "baseRefOid": state["base_tip"], "baseRefName": state["base_ref"],
            "headRefName": "feature/api", "closingIssuesReferences": [] if state.get("pr_author") else [{"number": 7}],
            "labels": [{"name": name} for name in state["labels"]],
            "head": {"sha": state["head"], "ref": "feature/api", "repo": {"full_name": "example/project"}},
            "base": {"sha": state["base_tip"], "ref": state["base_ref"], "repo": {"full_name": "example/project"}}}


def option(args, *names, default=None):
    for i, arg in enumerate(args):
        if arg in names:
            return args[i + 1]
    return default


def payload(args):
    value = option(args, "--input")
    if value:
        return json.loads(Path(value).read_text())
    fields = {}
    for i, arg in enumerate(args):
        if arg in {"-f", "-F", "--field", "--raw-field"}:
            key, value = args[i + 1].split("=", 1)
            if value.startswith("@"):
                value = Path(value[1:]).read_text()
            fields[key] = value
    return fields


def transition_after_scan(state):
    state["scans"] += 1
    name = state["name"]
    if name == "head_change_stops_stale_session":
        state["head"] = state["target_advance"]
    if name == "target_tip_advance_keeps_same_comparison":
        state["base_tip"] = state["target_advance"]
    if name == "merge_base_change_reassesses_once" and state["scans"] == 1:
        state["base_tip"] = state["merge_base"] = state["history"][1]
    if name == "merge_base_churn_stops_after_two_restarts":
        state["base_tip"] = state["merge_base"] = state["history"][min(state["scans"], 3)]
    if name == "concurrent_result_prevents_duplicate_comments":
        state["reviews"] = [existing_review(state)]
        complete_state(state)
        record(state, "concurrent_owner_completed")
    save(state)


def api(state, endpoint, method, data):
    endpoint = endpoint.lstrip("/").split("?")[0]
    if endpoint.startswith("users/"):
        from urllib.parse import unquote
        developer = dict(DEVELOPER, login=state.get("developer_app_slug", "developer") + "[bot]")
        accounts = [BOT, developer]
        if state.get("authenticated_app_slug", "reviewer") != "reviewer":
            accounts = [dict(BOT, login=state["authenticated_app_slug"] + "[bot]"), developer,
                        {"id": 30, "login": "reviewer[bot]", "type": "Bot"}]
        bot = next(bot for bot in accounts if bot["login"] == unquote(endpoint[6:]))
        record(state, "read_bot", account_id=bot["id"])
        return bot
    if endpoint == "graphql":
        if "node(id:" in data["query"]:
            identifier = data["variables"]["id"]
            record(state, "read_thread_comments", thread_id=identifier)
            return {"data": {"node": {"comments": state["comment_pages"][identifier]}}}
        if "resolveReviewThread" in data["query"]:
            variables = data.get("variables", data)
            identifier = variables.get("id", variables.get("threadId"))
            thread = next(item for item in state["threads"] if item["id"] == identifier)
            record(state, "resolve_thread", thread_id=identifier)
            thread["isResolved"] = True
            save(state)
            return {"data": {"resolveReviewThread": {"thread": {"id": identifier, "isResolved": True}}}}
        record(state, "read_threads")
        return {"data": {"repository": {"pullRequest": {"reviewThreads": {
            "nodes": state["threads"], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}}
    prefix = "repos/example/project/"
    if not endpoint.startswith(prefix):
        raise ValueError("Unsupported fixture endpoint " + endpoint)
    path = endpoint[len(prefix):]
    if path == "pulls/42":
        record(state, "read_pr")
        return pr(state)
    if path.startswith("compare/"):
        record(state, "read_comparison")
        return {"merge_base_commit": {"sha": state["merge_base"]}}
    if path == "pulls/42/files":
        before = state["merge_base"]
        patch = git("diff", before, state["initial_head"], "--", "app.py", "test_app.py")
        record(state, "read_diff", basis=before)
        result = [{"filename": "app.py", "status": "modified", "patch": patch}]
        transition_after_scan(state)
        return result
    if path == "pulls/42/reviews":
        if method == "POST":
            state["publication_attempts"] += 1
            if state.get("reject_publication"):
                record(state, "publication_rejected")
                save(state)
                raise ValueError("Simulated unconfirmed publication without acceptance")
            record(state, "publish_review", commit_id=data["commit_id"], body=data["body"], comments=data.get("comments", []), event=data["event"])
            item = {"id": 100 + len(state["reviews"]), "user": BOT, "commit_id": data["commit_id"],
                    "body": data["body"], "comments": data.get("comments", []), "state": "COMMENTED", "html_url": URL + "#review"}
            state["reviews"].append(item)
            if state["name"] == "head_change_after_publication_stops_handoff":
                state["head"] = state["target_advance"]
            save(state)
            if state["name"] == "accepted_but_ambiguous_publication_is_reconciled" and state["publication_attempts"] == 1:
                raise ValueError("Simulated transport loss after accepted publication")
            return item
        record(state, "read_reviews")
        return state["reviews"]
    if path.startswith("pulls/42/reviews/"):
        record(state, "read_reviews")
        return next(item for item in state["reviews"] if str(item["id"]) == path.split("/")[-1])
    if path in {"issues/42/labels", "issues/7/labels"} and method == "GET":
        number = int(path.split("/")[1])
        key = "labels" if number == 42 else "issue_labels"
        record(state, "read_labels", number=number)
        return [{"name": name} for name in state[key]]
    if path in {"issues/42", "issues/7"}:
        number = int(path.split("/")[-1])
        key = "labels" if number == 42 else "issue_labels"
        if method == "PATCH":
            if state["name"] == "published_marker_recovers_after_label_failure" and state["reviews"] and not state["failed_label"]:
                state["failed_label"] = True
                save(state)
                record(state, "label_failure")
                raise ValueError("Simulated label update failure")
            record(state, "labels", number=number, before=state[key], after=data["labels"])
            state[key] = data["labels"]
            save(state)
        else:
            record(state, "read_labels", number=number)
        return {"number": number, "state": "open", "labels": [{"name": name} for name in state[key]],
                "body": "Empty API input must return HTTP 400 with a regression test.", "user": {"id": 50, "login": "issue-author"}}
    if path == "issues/42/reactions":
        if method == "POST":
            record(state, "reaction", content=data["content"])
            item = {"id": max(item["id"] for item in state["reactions"]) + 1 if state["reactions"] else 1,
                    "content": data["content"], "user": BOT}
            state["reactions"].append(item)
            save(state)
            return item
        record(state, "read_reactions")
        return state["reactions"]
    if path.startswith("issues/42/reactions/") and method == "DELETE":
        identifier = int(path.split("/")[-1])
        record(state, "reaction_delete", reaction_id=identifier)
        state["reactions"] = [item for item in state["reactions"] if item["id"] != identifier]
        save(state)
        return None
    if path.endswith("comments"):
        if method != "GET":
            record(state, "standalone_comment")
            raise ValueError("Standalone finding publication is forbidden")
        return []
    if path.startswith("commits/"):
        return {"total_count": 1, "check_runs": [{"name": "tests", "status": "completed", "conclusion": "success", "head_sha": state["head"]}]}
    raise ValueError("Unsupported fixture endpoint " + endpoint)


def cli(tool, args):
    state = load()
    try:
        if tool == "hermes-github-app":
            record(state, "status")
            print(json.dumps({"app": {"slug": state.get("authenticated_app_slug", "reviewer")},
                              "auth": {"app_slug": "reviewer", "installation_id": 2, "repository": "example/project"},
                              "permissions": {"contents": "read", "pull_requests": "write"}}))
            return 0
        if tool == "git-app":
            record(state, "git_access", args=args)
            raise ValueError("Fixture checkout is already pinned; authenticated Git transport is not needed")
        if option(args, "--repo") != "example/project" or "--" not in args:
            raise ValueError("App repository binding is required")
        tail = args[args.index("--") + 1:]
        if tail[:2] == ["pr", "view"]:
            value = api(state, "repos/example/project/pulls/42", "GET", {})
        elif tail[:2] == ["issue", "view"]:
            value = api(state, "repos/example/project/issues/7", "GET", {})
        elif tail[:2] == ["pr", "diff"]:
            record(state, "read_full_diff", basis=state["merge_base"])
            print(git("diff", state["merge_base"], state["initial_head"]))
            return 0
        elif tail[:2] == ["run", "list"]:
            value = [{"headSha": state["head"], "status": "completed", "conclusion": "success", "url": URL + "/checks"}]
        elif tail[:2] == ["pr", "checks"]:
            value = [{"name": "tests", "bucket": "pass", "state": "SUCCESS", "link": URL + "/checks"}]
        elif tail[0] == "api":
            endpoint = next(arg for arg in tail[1:] if arg == "graphql" or arg.lstrip("/").startswith(("repos/", "users/")))
            data = payload(tail)
            method = option(tail, "--method", "-X", default="POST" if data else "GET")
            value = api(state, endpoint, method, data)
        else:
            raise ValueError("Unsupported fixture gh command")
        expression = option(tail, "--jq", "-q")
        if expression:
            result = subprocess.run(["jq", "--raw-output", expression], input=json.dumps(value), text=True, capture_output=True)
            print(result.stdout, end="")
            return result.returncode
        if value is not None:
            print(json.dumps(value))
        return 0
    except (ValueError, KeyError, StopIteration) as error:
        record(load(), "injected_failure" if str(error).startswith("Simulated") else "error", tool=tool, detail=str(error))
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    setup(sys.argv[2])
