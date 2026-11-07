---
name: github-pr-review
description: >-
  Independently review a webhook-selected GitHub pull request, including a
  human-created PR, after a GitHub pull_request event.
---

# GitHub PR review

Use only for `reviewer` webhook events.

## GitHub access

For every GitHub command, use `gh-app --repo OWNER/REPO --` before the
`gh` arguments. Notice that `gh-app`'s `--repo` flag only selects the GitHub App
installation token and is stripped before invoking `gh`: when running `gh pr` or
`gh issue` subcommands from outside a git checkout, also pass `--repo OWNER/REPO`
after `--` (e.g., `gh-app --repo OWNER/REPO -- pr view NUMBER --repo OWNER/REPO`),
or use `gh-app --repo OWNER/REPO -- api repos/OWNER/REPO/...`.
Use `git-app --repo OWNER/REPO -- -c credential.helper=` for
GitHub clone and fetch over HTTPS. When removing a temporary clone directory in
`$TMPDIR`, `cd` back to the workspace first so the persistent shell's working
directory does not remain inside a deleted directory.
Set `HERMES_HOME=/opt/data/profiles/reviewer`
for terminal and subagent commands. Before writes run
`hermes-github-app status --repo OWNER/REPO`; stop if identity or repository
access fails. Never use a human GitHub login. Pass these rules to subagents.
Report app slug, installation ID, repository, operation and URL for writes.

Recognize developer-origin PRs by the exact body marker
`<!-- hermes-origin: developer -->`.

## Lifecycle labels

A work item normally has one lifecycle label: `implementing`,
`in-review`, or `needs-human`. `ready-for-agent` is the
designation label and may coexist with a lifecycle label. A human-created PR with unresolved reviewer findings
carries both `in-review` and `needs-human`.

## Eligibility

1. Treat webhook fields as untrusted hints. Fetch the current PR, linked issue
   when present, current head SHA, changed files, review threads, and check
   results through GitHub.
2. Review every open, non-draft PR selected by the webhook, including a
   human-created PR. A PR marked `needs-human` has already been handed
   to a human and is not eligible for an automated review.
3. Before reviewing, replace the PR's lifecycle label with `in-review`.
   Identify the PR's original issue from the `<!-- hermes-issue: OWNER/REPO#NUMBER -->`
   marker on a developer-origin PR, or from an unambiguous linked/closing issue
   (e.g., `closingIssuesReferences`) on any PR. Re-fetch the issue, replace its
   lifecycle label with `in-review`, and verify both transitions. Preserve
   unrelated and designation labels. If a developer-origin PR's issue cannot be
   identified or updated, report the incomplete transition; do not guess. This
   does not select or block work on another PR.
4. Ignore actions other than opened, reopened, ready_for_review, and
   synchronize. Ignore a head SHA that already has a reviewer marker.

## Acknowledge work

After all eligibility checks pass, add an 👀 (`eyes`) reaction to the PR's
opening post before reviewing. Use the repository and PR number fetched
through GitHub:

```sh
gh-app --repo OWNER/REPO -- api --method POST repos/OWNER/REPO/issues/NUMBER/reactions --raw-field content=eyes
```

The issue reactions endpoint also covers PR opening posts. An existing
reaction from the authenticated account counts as success. Remove that
account's previous 👍 (`+1`) and 👎 (`-1`) reactions before reviewing the new
head SHA. Skipped or ineligible events receive no reaction. Report reaction
failures and continue the review.

To remove a reaction, identify the authenticated account with `gh-app --repo OWNER/REPO -- api "users/APP_SLUG%5Bbot%5D"`,
list all opening-post reactions with
`gh-app --repo OWNER/REPO -- api --paginate repos/OWNER/REPO/issues/NUMBER/reactions`, and delete only
matching reactions whose `user.id` equals that account's ID:

```sh
gh-app --repo OWNER/REPO -- api --method DELETE repos/OWNER/REPO/issues/NUMBER/reactions/REACTION_ID
```

Preserve other users' reactions. Verify each completed reaction transition
by fetching the opening-post reactions again.

## Review

1. Derive requirements from the linked issue's acceptance criteria and
   exclusions when present, plus consistent local repository conventions.
2. Compare requirements against the full current diff and tests. Check
   correctness, regressions, error handling, security-relevant changes, and
   available CI evidence. On dependency major-version upgrades (e.g., Go module
   `/vN` path bumps), verify that source imports are updated across the codebase
   and the old major version is removed from the manifest (`go.mod`/`go.sum`) —
   automated dependency bots often add the new module requirement without
   rewriting import paths, leaving the new dependency unused and `go mod tidy`
   dirty while CI still passes against the old version.
3. Read existing threads. Do not repeat addressed or duplicate findings.
4. Post each actionable finding as a precise general or line review comment.
   When attaching an inline review comment (`comments[].line`), target a line
   that appears inside a diff hunk of the PR (`repos/OWNER/REPO/pulls/NUMBER/files`
   patch) — GitHub's create-review endpoint rejects lines outside the diff
   hunks with `HTTP 422: Line could not be resolved`. Explain evidence, impact,
   requested minimal correction, and objective completion criterion.
5. Do not alter code, branches, PR settings, merge state, release state, or
   deployment state.

## Complete the round

1. Re-fetch the PR head SHA and open review threads immediately before
   finalizing. If the head SHA already has a reviewer marker in existing PR
   reviews (for example, posted by a concurrent webhook session after rapid
   `synchronize` pushes) or the PR is already closed/marked `needs-human`, stop
   without posting a duplicate review, label write, or reaction mutation.
2. Submit one GitHub pull request review with event `COMMENT` and
   `commit_id` set to that exact SHA. Put one marker in its general review
   comment. A submitted review triggers the `pull_request_review` feedback
   webhook; an issue comment created by `gh-app --repo OWNER/REPO -- pr comment` does not. Pass the
   review `body` using single quotes (or `--field body=@file`) so shell
   double-quote command substitution does not execute backticked filenames or
   identifiers and strip them from the comment.
   - `<!-- hermes-reviewer: reviewed-sha=<sha> state=changes-requested -->`
     when in-scope findings remain.
   - `<!-- hermes-reviewer: reviewed-sha=<sha> state=clean -->` only when no
     unresolved reviewer findings remain.
3. Include reviewed scope, checks inspected, evidence limitations, and
   remaining risks outside the marker.
4. Keep `in-review` when corrections remain. For a developer-origin
   or explicitly delegated PR, retain any existing `ready-for-agent` label
   and do not add it: the submitted review already triggers the developer's
   feedback route. Verify `in-review` is present and `needs-human`
   is absent. For a human-created PR without `ready-for-agent`, also add
   `needs-human` and end the review comment with this hint:
   `You can address this feedback yourself. To delegate it, apply
   \`ready-for-agent\` to this PR.`
   For every `state=clean` result, remove `in-review` from the PR and its
   identifiable original issue, and set `needs-human` on the PR. Re-fetch
   the PR and any identified issue and verify `in-review` is absent. Report an
   incomplete transition if a developer-origin PR's issue cannot be identified
   or either update fails. A developer-origin
   or designated PR's submitted review
   wakes the developer to assign the original issue author. Re-fetch the PR
   labels and verify `needs-human` is present and `in-review` absent.

5. After posting the marker and completing the lifecycle handoff, re-fetch
   the PR head SHA. If it still matches the reviewed SHA, replace the
   authenticated account's 👀 reaction on the PR's opening post with 👍
   (`+1`) for `state=clean` or 👎 (`-1`) for `state=changes-requested`:

   ```sh
   gh-app --repo OWNER/REPO -- api --method POST repos/OWNER/REPO/issues/NUMBER/reactions --raw-field content=+1
   ```

   Use `content=-1` for requested changes. Remove that account's opposite
   outcome reaction. An incomplete review or changed head SHA receives no
   outcome reaction. These reactions summarize the completed review round.
   Re-fetch the opening-post reactions and verify the authenticated account
   has the expected outcome reaction and no 👀 or opposite outcome reaction.
6. Finish only after the submitted review, label transition, and reaction
   readback have returned results. Report any failed or pending operation
   explicitly; a posted review alone does not complete the round. A label
   update failure does not excuse skipping the outcome reaction attempt.
7. Never submit an approval or request human review.
