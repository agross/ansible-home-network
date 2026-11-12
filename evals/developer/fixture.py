"""Synthetic GitHub App commands backed by disposable Git repositories."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote


def git(*args, cwd=None):
    result = subprocess.run(["git", *map(str, args)], cwd=cwd, text=True, capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.strip())
    return result.stdout.strip()


def directory():
    if Path(__file__).parent.name == "fixture-tools":
        return Path(__file__).resolve().parents[1] / "fake-forge"
    return Path(git("rev-parse", "--git-common-dir")).resolve() / "fake-forge"


def read_state():
    return json.loads((directory() / "state.json").read_text())


def write_state(state):
    (directory() / "state.json").write_text(json.dumps(state, indent=2) + "\n")


def record(operation, **details):
    details.setdefault("labels", read_state()["labels"])
    details["dirty"] = bool(git("status", "--porcelain"))
    with (directory() / "operations.jsonl").open("a") as stream:
        stream.write(json.dumps({"operation": operation, **details}) + "\n")


def remote(repository):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid fixture repository")
    return directory() / "remotes" / (repository + ".git")


def setup():
    root = Path.cwd()
    evidence = json.loads((root / "event.json").read_text())
    state = {"evidence": evidence, "labels": evidence["pr"]["labels"],
             "reactions": [], "assignees": [], "body": evidence["pr"]["body"]}
    git("config", "user.name", "developer[bot]")
    git("config", "user.email", "10+developer[bot]@users.noreply.github.com")
    sha = git("rev-parse", "HEAD")
    state["initial_sha"] = state["head_sha"] = sha
    state["initial_branch"] = evidence["pr"]["head_branch"]
    metadata = Path(git("rev-parse", "--git-common-dir")).resolve()
    tools = metadata / "fixture-tools"
    tools.mkdir()
    (tools / "fixture.py").write_bytes(Path(__file__).read_bytes())
    (metadata / "fake-forge").mkdir()
    for repository in {evidence["pr"]["base_repository"], evidence["pr"]["head_repository"]}:
        path = remote(repository)
        path.parent.mkdir(parents=True, exist_ok=True)
        git("init", "--bare", path)
        git("push", path, "HEAD:refs/heads/main")
        git("--git-dir", path, "symbolic-ref", "HEAD", "refs/heads/main")
    git("push", remote(evidence["pr"]["head_repository"]), "HEAD:refs/heads/" + evidence["pr"]["head_branch"])
    git("remote", "add", "origin", "https://github.com/" + evidence["pr"]["base_repository"] + ".git")
    write_state(state)
    git("switch", "--create", state["initial_branch"])
    (directory() / "operations.jsonl").write_text("")


def option(args, *names, default=None):
    for index, arg in enumerate(args):
        if arg in names:
            return args[index + 1]
        for name in names:
            if arg.startswith(name + "="):
                return arg[len(name) + 1:]
    return default


def fields(args):
    values = {}
    for index, arg in enumerate(args):
        if arg in {"-f", "-F", "--field", "--raw-field"}:
            key, value = args[index + 1].split("=", 1)
            if value.startswith("@"):
                value = Path(value[1:]).read_text()
            if key.endswith("[]"):
                values.setdefault(key[:-2], []).append(value)
            else:
                values[key] = value
    path = option(args, "--input")
    if path:
        values.update(json.loads(Path(path).read_text()))
    return values


def pr(state):
    item = state["evidence"]["pr"]
    base = item["base_repository"]
    head = item["head_repository"]
    return {"number": 42, "state": "open", "body": state["body"], "user": item["creator"],
            "author": item["creator"], "url": f"https://github.com/{base}/pull/42",
            "html_url": f"https://github.com/{base}/pull/42", "isDraft": False,
            "labels": [{"name": label} for label in state["labels"]], "assignees": state["assignees"],
            "headRefOid": state["head_sha"], "headRefName": item["head_branch"],
            "baseRefName": "main", "baseRefOid": state["initial_sha"],
            "headRepository": {"nameWithOwner": head, "name": head.split("/")[1]},
            "headRepositoryOwner": {"login": head.split("/")[0]},
            "head": {"sha": state["head_sha"], "ref": item["head_branch"],
                     "repo": {"full_name": head, "clone_url": f"https://github.com/{head}.git"}},
            "base": {"sha": state["initial_sha"], "ref": "main", "repo": {"full_name": base}},
            "closingIssuesReferences": [{"number": 7, "url": f"https://github.com/{base}/issues/7"}]}


def reviews(state):
    evidence = state["evidence"]
    result = []
    for item in [*evidence["other_feedback"], evidence["review"]]:
        value = dict(item)
        value["user"] = value.pop("author")
        value["commit_id"] = state["initial_sha"] if value.get("commit_id", "a" * 40) == "a" * 40 else "b" * 40
        value["body"] = value["body"].replace("a" * 40, state["initial_sha"])
        value["html_url"] = pr(state)["url"] + "#pullrequestreview-" + str(value["id"])
        result.append(value)
    return result


def labels(state, after):
    if not isinstance(after, list) or not all(isinstance(label, str) for label in after):
        raise ValueError("labels must be an array")
    record("labels", before=state["labels"], after=after)
    state["labels"] = list(dict.fromkeys(after))
    write_state(state)


def api(state, args):
    endpoint = next((arg for arg in args[1:] if arg == "graphql" or arg.lstrip("/").startswith(("repos/", "users/"))), "")
    endpoint = unquote(endpoint).split("?")[0].lstrip("/")
    method = option(args, "--method", "-X", default="GET").upper()
    data = fields(args)
    if method == "GET" and data and endpoint != "graphql":
        method = "POST"
    if endpoint == "graphql":
        record("read_threads")
        return {"data": {"repository": {"pullRequest": {"reviewThreads": {
            "nodes": [], "pageInfo": {"hasNextPage": False, "endCursor": None}}}}}}
    if endpoint.startswith("users/"):
        login = endpoint.removeprefix("users/")
        account = next(bot for bot in state["evidence"]["trusted_profile_bot_accounts"].values() if bot["login"] == login)
        record("read_bot", account_id=account["id"])
        return account
    match = re.fullmatch(r"repos/([^/]+/[^/]+)(?:/(.*))?", endpoint)
    if not match:
        raise ValueError("Unsupported API endpoint: " + endpoint)
    repository, path = match.group(1), match.group(2) or ""
    allowed = {state["evidence"]["pr"]["base_repository"], state["evidence"]["pr"]["head_repository"]}
    if repository not in allowed:
        raise ValueError("Repository outside fixture")
    if not path:
        record("read_repository", repository=repository)
        return {"full_name": repository, "permissions": {"push": True, "pull": True},
                "default_branch": "main", "owner": {"login": repository.split("/")[0]}}
    if path.startswith("collaborators/") and path.endswith("/permission"):
        login = path.split("/")[1]
        author = next(review for review in [*state["evidence"]["other_feedback"], state["evidence"]["review"]]
                      if review["author"]["login"] == login)
        record("read_permission", account_id=author["author"]["id"], permission=author["author_permission_on_base"])
        return {"permission": author["author_permission_on_base"], "user": author["author"]}
    if path == "pulls/42":
        record("read_pr", creator_id=state["evidence"]["pr"]["creator"]["id"])
        return pr(state)
    if path == "pulls/42/reviews" or path.startswith("pulls/42/reviews/"):
        values = reviews(state)
        if path != "pulls/42/reviews":
            values = [value for value in values if value["id"] == int(path.split("/")[-1])]
        for value in values:
            record("read_review", review_id=value["id"], account_id=value["user"]["id"])
        return values if path == "pulls/42/reviews" else values[0]
    if path == "pulls/42/comments" or path.endswith("/comments"):
        record("read_comments")
        return []
    if path == "issues/7":
        record("read_issue")
        return {"number": 7, "state": "open", "title": "Handle empty API input", "body": state["evidence"]["scope"],
                "user": {"login": "issue-author", "id": 50}, "labels": [{"name": "in-review"}]}
    if path == "issues/42" and method == "GET":
        record("read_pr", creator_id=state["evidence"]["pr"]["creator"]["id"])
        return pr(state)
    if path in {"issues/42", "issues/42/labels"} and method in {"PATCH", "PUT", "POST"}:
        labels(state, data["labels"])
        return pr(state)
    if path.startswith("issues/42/labels/") and method == "DELETE":
        labels(state, [label for label in state["labels"] if label != path.split("/")[-1]])
        return []
    if path == "issues/42/reactions":
        if method == "POST":
            reaction = {"id": 1000 + len(state["reactions"]), "content": data["content"],
                        "user": state["evidence"]["trusted_profile_bot_accounts"]["developer"]}
            record("reaction", content=data["content"])
            state["reactions"].append(reaction)
            write_state(state)
            return reaction
        record("read_reactions")
        return state["reactions"]
    if path.startswith("issues/42/reactions/") and method == "DELETE":
        record("reaction_delete", reaction_id=int(path.split("/")[-1]))
        state["reactions"] = [r for r in state["reactions"] if r["id"] != int(path.split("/")[-1])]
        write_state(state)
        return {}
    if path == "rulesets":
        record("read_required_checks")
        return []
    if path.startswith("rules/branches/"):
        record("read_required_checks")
        return [{"type": "required_status_checks", "parameters": {
            "required_status_checks": [{"context": "tests", "integration_id": 1}]}}]
    if path == "branches/main":
        record("read_base")
        return {"name": "main", "commit": {"sha": state["initial_sha"]}, "protected": True}
    if "protection" in path:
        record("read_required_checks")
        required = {"contexts": ["tests"], "checks": [{"context": "tests", "app_id": 1}]}
        return required if path.endswith("required_status_checks") else {"required_status_checks": required}
    if path.startswith("commits/"):
        sha = path.split("/")[1]
        old = sha == "b" * 40
        record("read_ci", sha=sha, status="passed" if old else "pending")
        check = {"id": 901, "name": "tests", "head_sha": sha, "status": "completed" if old else "in_progress",
                 "conclusion": "success" if old else None, "details_url": pr(state)["url"] + "/checks"}
        if path.endswith("check-runs"):
            return {"total_count": 1, "check_runs": [check]}
        return {"state": "success" if old else "pending", "sha": sha,
                "statuses": [{"context": "tests", "state": "success" if old else "pending", "target_url": check["details_url"]}]}
    raise ValueError("Unsupported API operation: " + method + " " + path)


def gh(state, args):
    if args[0] == "api":
        return api(state, args), 0
    if args[:2] in (["pr", "view"], ["issue", "view"]):
        if args[0] == "issue" and "7" in args:
            return api(state, ["api", "repos/" + state["evidence"]["pr"]["base_repository"] + "/issues/7"]), 0
        record("read_pr", creator_id=state["evidence"]["pr"]["creator"]["id"])
        return pr(state), 0
    if args[:2] in (["pr", "edit"], ["issue", "edit"]):
        after = list(state["labels"])
        for index, arg in enumerate(args):
            if arg == "--remove-label":
                after = [label for label in after if label not in args[index + 1].split(",")]
            if arg == "--add-label":
                after.extend(args[index + 1].split(","))
        if any(arg in args for arg in ("--remove-label", "--add-label")):
            labels(state, after)
        if "--add-assignee" in args:
            record("assign", login=option(args, "--add-assignee"))
            state["assignees"].append({"login": option(args, "--add-assignee")})
        if "--body-file" in args:
            record("pr_body")
            state["body"] = Path(option(args, "--body-file")).read_text()
        write_state(state)
        return pr(state), 0
    if args[:2] == ["pr", "checks"]:
        record("read_ci", sha=state["head_sha"], status="pending")
        return [{"name": "tests", "state": "IN_PROGRESS", "bucket": "pending", "link": pr(state)["url"] + "/checks"}], 8
    if args[:2] == ["run", "list"]:
        sha = option(args, "--commit", default=state["head_sha"])
        old = sha == "b" * 40
        record("read_ci", sha=sha, status="passed" if old else "pending")
        return [{"databaseId": 901, "headSha": sha, "status": "completed" if old else "in_progress",
                 "conclusion": "success" if old else "", "url": pr(state)["url"] + "/checks"}], 0
    if args[:2] == ["run", "watch"]:
        record("read_ci", sha=state["head_sha"], status="pending")
        return {"status": "in_progress", "note": "Fixture CI stays pending; report the blocker."}, 8
    raise ValueError("Unsupported gh command: " + " ".join(args))


def git_app(state, repository, args):
    while args and args[0] == "-c":
        if args[1] != "credential.helper=":
            raise ValueError("Unsupported Git configuration")
        args = args[2:]
    command = args[0]
    if command not in {"fetch", "push", "clone", "ls-remote"}:
        raise ValueError("Unsupported authenticated Git operation")
    if any(arg.startswith(("--force", "+")) or arg == "-f" for arg in args):
        raise ValueError("Force push is forbidden")
    index = next(i for i in range(1, len(args)) if not args[i].startswith("-"))
    url = args[index]
    if url == "origin":
        url = git("remote", "get-url", "--push", "origin")
    match = re.fullmatch(r"https://github.com/([\w.-]+/[\w.-]+?)(?:\.git)?", url)
    if not match or not remote(match[1]).is_dir() or repository != match[1]:
        raise ValueError("Unbound fixture Git destination or App repository")
    args = list(args)
    args[index] = str(remote(match[1]))
    before = git("rev-parse", "HEAD")
    record(command, repository=repository, url=url, refspec=args[-1], sha=before,
           labels=state["labels"])
    output = git(*args)
    if command == "clone":
        git("remote", "set-url", "origin", url, cwd=args[-1])
    if command == "push":
        state["head_sha"] = git("--git-dir", remote(state["evidence"]["pr"]["head_repository"]),
                                "rev-parse", "refs/heads/" + state["evidence"]["pr"]["head_branch"])
        write_state(state)
    return output


def cli(tool, args):
    try:
        state = read_state()
        if tool in {"fixture-commit", "fixture-checkout"}:
            record("commit" if tool == "fixture-commit" else "checkout")
            return 0
        repository = option(args, "--repo")
        if tool == "hermes-github-app":
            if args[0] != "status":
                raise ValueError("Only App status is supported")
            record("status", repository=repository)
            output, status = {"app_slug": "developer", "installation_id": 1, "repository": repository,
                              "identity": "developer[bot]", "permissions": {"contents": "write"}}, 0
        else:
            if not repository or "--" not in args:
                raise ValueError("App wrapper requires --repo and --")
            tail = args[args.index("--") + 1:]
            if tool == "git-app":
                print(git_app(state, repository, tail))
                return 0
            output, status = gh(state, tail)
            jq = option(tail, "--jq", "-q")
            if jq:
                result = subprocess.run(["jq", "--raw-output", jq], input=json.dumps(output), text=True, capture_output=True)
                if result.returncode:
                    raise ValueError(result.stderr)
                print(result.stdout, end="")
                return status
        print(json.dumps(output))
        return status
    except (ValueError, KeyError, StopIteration, IndexError, OSError) as error:
        record("error", tool=tool, arguments=args, message=str(error))
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    if sys.argv[1:] == ["setup"]:
        setup()
    else:
        raise SystemExit(cli(Path(sys.argv[0]).name, sys.argv[1:]))
