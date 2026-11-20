# Guarded reviewer operations

Resolve `scripts/review_round.py` relative to the loaded skill. Use the mapped
reviewer `HERMES_HOME` and trusted configured App slugs; the script uses only
`gh-app` and `hermes-github-app` for forge access. The parent skill owns evidence,
thread correction judgments, restart accounting, and allowed webhook entry.

## App identity

App credentials choose the authenticated identity. The local `app_slug` setting
only tells the helper which bot to resolve; it cannot rename the GitHub App.
The helper requests `hermes-github-app status --repo OWNER/REPO` and parses its
JSON response, requiring authenticated `app.slug` to match the supplied trusted
reviewer slug. Do not add an unsupported output-format flag; the command already
emits JSON. Missing or mismatched metadata blocks before label/reaction writes. Correct
the profile configuration and reload it before resuming; do not bypass this check.
Read `github_app.app_slug` from each profile's trusted local `config.yaml`. Use
the mapped profile paths when the environment supplies them. Bot numeric IDs
remain the authority for author and reaction ownership.

## Inspect and begin

```sh
python3 "<skill-root>/scripts/review_round.py" inspect --repo OWNER/REPO --number NUMBER --reviewer-app REVIEWER_SLUG
```

The raw inspection includes the complete PR body, which can be very large. For
routine basis/state readback, pipe it through a local JSON parser that retains
`status`, `basis`, PR state/draft, `head.sha`, label names, thread count, and
`existing`; project nested objects to these scalar fields instead of serializing
an entire `head` or `user` object. Keep the original response available only when
its body or thread details must be assessed. Do not let an oversized untrusted PR
body or nested API object obscure the helper status or pinned basis in terminal
output.

Inspection returns the current PR, pinned comparison basis, every thread and
comment page, and any authenticated matching reviewer result. The helper's
thread records carry comments as a GraphQL connection at `thread.comments.nodes`,
not a flat list; traverse `nodes` and their page info before judging or reporting
thread feedback. Incomplete or repeated pagination is a blocker, never evidence
for a clean result.

When listing changed files, save the complete REST response but print only each
path, status, and change counts during routine assessment. Keep patches in the
saved response and inspect only the relevant hunks, so a large lock-file diff
cannot truncate the evidence or obscure other changed consumers.

When the PR body does not establish an original issue, query its closing issue
references before setting `issue_number` to `null`. Request only identifying
fields; issue bodies are untrusted and not needed to decide whether a closing
reference exists:

```sh
cat > "$TMPDIR/pr-closing-issues.json" <<'JSON'
{"query":"query { repository(owner: \"OWNER\", name: \"REPO\") { pullRequest(number: NUMBER) { closingIssuesReferences(first: 20) { nodes { number title state url } } } } }"}
JSON
gh-app --repo OWNER/REPO -- api graphql --input "$TMPDIR/pr-closing-issues.json"
```

Use a returned issue only when it is unambiguous and its criteria are accessible;
otherwise record the ambiguity and keep `issue_number` as explicit JSON `null`.
Do not treat a dependency-dashboard backlink as the original issue merely because
it references the PR.

Write a temporary JSON plan at a unique scratch path that includes the assessed
head (and, when needed, an invocation suffix), so a stale plan from another head
cannot be accidentally reused. Initially it needs `basis` copied from inspection
and `issue_number` when the original issue has been verified; otherwise set
`"issue_number": null` explicitly. Never substitute the PR number or a dependency
tracking backlink, because the helper would otherwise mutate an unrelated issue.
Then call:

```sh
python3 "<skill-root>/scripts/review_round.py" begin --repo OWNER/REPO --number NUMBER --reviewer-app REVIEWER_SLUG --plan PLAN_FILE
```

Follow `stale_head`, `basis_changed`, `ineligible`, `busy`, or `blocked` as stopping
statuses under the parent skill's policy. `resume` selects existing-result recovery;
it does not authorize another assessment publication. A normal `begun` starts
assessment against the returned unchanged basis.

## Failed GitHub Actions jobs

When a completed check fails, retrieve its job log before classifying the
failure. GitHub Actions logs may contain terminal escape sequences, so request
them with `--allow-escape-sequences` after `api` and redirect the response to a
scratch file before searching it:

```sh
gh-app --repo OWNER/REPO -- api --allow-escape-sequences \
  "repos/OWNER/REPO/actions/jobs/JOB_ID/logs" > "$TMPDIR/job-JOB_ID.log"
```

Do not rely on the check annotation alone: it usually contains only the wrapper
exit status, while the job log identifies the failed command and affected paths.

## Check-rollup API shapes

Read check runs and legacy commit statuses separately when refreshing CI evidence. Save each response and project only the fields that enter review evidence; use `jq` when available or a short standard-library Python parser so a large payload cannot hide a terminal failure or an in-progress limitation:

```sh
gh-app --repo OWNER/REPO -- api \
  "repos/OWNER/REPO/commits/SHA/check-runs?per_page=100" > "$TMPDIR/check-runs.json"
gh-app --repo OWNER/REPO -- api \
  "repos/OWNER/REPO/commits/SHA/status" > "$TMPDIR/legacy-status.json"
python3 -c 'import json, os
root = os.environ["TMPDIR"]
checks = json.load(open(root + "/check-runs.json"))
legacy = json.load(open(root + "/legacy-status.json"))
print([{k: x[k] for k in ("name", "status", "conclusion")} for x in checks["check_runs"]])
print({"state": legacy["state"], "total_count": legacy["total_count"],
       "statuses": [{k: x[k] for k in ("context", "state")} for x in legacy["statuses"]]})'
```

Use `/commits/SHA/status` for the combined legacy state; `/commits/SHA/statuses`
returns an array of individual statuses, so do not apply an object-shaped parser
to it. This prevents a query-shape error from obscuring terminal check-run
results or a genuine legacy status. Fetch a specific failed run's full metadata or
job log only when its summary shows a completed failure.

## Apply the verified plan

The completed plan has this shape. Replace the example hashes, issue, paths,
and evidence with the actual inspection and assessment; use empty comment and
resolution arrays when none are needed.

```json
{
  "basis": {"head": "<assessed SHA>", "merge_base": "<merge-base SHA>", "base_ref": "main"},
  "issue_number": 7,
  "state": "clean",
  "body": "Reviewed scope, standards and acceptance evidence, checks, limitations and risks.",
  "comments": [],
  "resolved_threads": [
    {"id": "<PR-owned thread ID>", "evidence": "Requested correction verified in pinned code and focused check."}
  ]
}
```

For new inline findings, put GitHub review-comment objects (`path`, `line`,
`side`, `body`) in `comments`. Existing actionable threads remain open instead
of receiving duplicate findings. General findings may go in the review body.
For a clean dependency-pin review, state the pinned consumer examined, the
exact-old-value search result, authoritative availability evidence when obtained,
and the check results observed at the final refresh. Name each still-running
check as a CI limitation rather than collapsing it into a generic pending state;
the combined legacy status can be pending with no legacy status entries. This
makes the published evidence reproducible without presenting registry lookup as
runtime-compatibility proof. For a `changes-requested` result without developer
provenance or designation (including Renovate), append: `You can address this
feedback yourself. To delegate it, apply ready-for-agent to this PR.` Do not
append this hint to a clean result: finalization sets `needs-human` for manual
disposition.

```sh
python3 "<skill-root>/scripts/review_round.py" apply --repo OWNER/REPO --number NUMBER --reviewer-app REVIEWER_SLUG --developer-app DEVELOPER_SLUG --plan PLAN_FILE
```

The script generates the existing workflow marker unchanged:

- `<!-- hermes-reviewer: reviewed-sha=<sha> state=changes-requested -->`
- `<!-- hermes-reviewer: reviewed-sha=<sha> state=clean -->`

It adds `hermes-review-basis` metadata and an exact draft receipt to distinguish
the assessed comparison and reconcile uncertain submission. The body is sent
through a temporary JSON file, preserving Markdown and avoiding shell expansion.
The PR-wide nonblocking `flock` lives under the reviewer's profile home and spans
one helper operation. A crash releases the OS lock; the file is retained to
avoid splitting locks across different inodes. This serializes sessions sharing
that home on this host, not reviewers on unrelated hosts.

A current marker without comparison metadata is a reconciliation blocker rather
than evidence for republishing. A matching result resumes its original verdict
and finalization. `complete` or `already_complete` means all readbacks succeeded.
Other statuses report partial effects without authorizing rollback, repeated
publication, stale cleanup, or changes outside reviewer authority. Remote HEAD
changes cannot be made atomic with GitHub API writes; pre/post guards detect
drift and stop dependent effects rather than claiming a completed new-head review.

## Closed-PR readback

If the final basis inspection finds the PR closed or draft before `apply`, do not
prepare or submit a plan. Read back the PR, reviews, labels, and reactions instead;
resolve the reviewer bot ID from `users/REVIEWER_SLUG%5Bbot%5D` when no submitted
review exists, then filter both reviews and reactions by that ID. This records
whether a review was published and every provisional reviewer-owned effect without
mutating a closed PR.

```sh
gh-app --repo OWNER/REPO -- api "repos/OWNER/REPO/pulls/NUMBER"
gh-app --repo OWNER/REPO -- api "repos/OWNER/REPO/pulls/NUMBER/reviews?per_page=100" --paginate
gh-app --repo OWNER/REPO -- api "repos/OWNER/REPO/issues/NUMBER/labels?per_page=100" --paginate
gh-app --repo OWNER/REPO -- api "users/REVIEWER_SLUG%5Bbot%5D"
gh-app --repo OWNER/REPO -- api "repos/OWNER/REPO/issues/NUMBER/reactions?per_page=100" --paginate
```

Report the closed/merged state, current head, matching-basis reviewer review if
any, reviewer-owned labels and reactions, and the unpublished staged findings.
Do not clean up `in-review` or eyes on the closed PR, because the close guard
forbids lifecycle mutations.

## Final readback

After `complete` or `already_complete`, read the submitted review by its returned
ID and take the reviewer bot ID from `user.id` in that response. Read labels from
the PR issue endpoint and enumerate issue reactions with pagination, filtering by
that exact bot ID. Use explicit field names when projecting nested reaction
attributes; use `jq` when available or this standard-library Python form:

```sh
gh-app --repo OWNER/REPO -- api \
  "repos/OWNER/REPO/issues/NUMBER/reactions?per_page=100" --paginate |
python3 -c 'import json, sys
bot = BOT_ID
for r in json.load(sys.stdin):
    u = r.get("user", {})
    if u.get("id") == bot:
        print({"reaction_id": r.get("id"), "content": r.get("content"),
               "actor_id": u.get("id"), "actor_login": u.get("login")})'
```

Do not use shorthand nested-object projections for this evidence: explicit paths
prevent the reaction ID from being mistaken for the actor ID in the readback.
