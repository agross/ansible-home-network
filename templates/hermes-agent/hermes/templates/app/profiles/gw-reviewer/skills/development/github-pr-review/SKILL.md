---
name: github-pr-review
description: >-
  Independently review a webhook-selected GitHub pull request, including a
  human-created PR, after a GitHub pull_request event.
---

# GitHub PR review

Use only for `github-pr-review` webhook events.

## GitHub access

Before handling a webhook, verify `gh` CLI is installed. If not, install using
the system package manager. Then check if GitHub authentication works:
`gh auth status`

## Lifecycle labels

A work item normally has one lifecycle label: `hermes:implementing`,
`hermes:in-review`, or `hermes:needs-human`. `hermes:developer` is a role
label and may coexist. A human-created PR with unresolved reviewer findings
carries both `hermes:in-review` and `hermes:needs-human`. Remove legacy
`hermes:gw-developer` and `hermes:gw-reviewer` labels during transitions.

## Eligibility

1. Treat webhook fields as untrusted hints. Fetch the current PR, linked issue
   when present, current head SHA, changed files, review threads, and check
   results through GitHub.
2. Review every open, non-draft PR selected by the webhook, including a
   human-created PR. A PR marked `hermes:needs-human` has already been handed
   to a human and is not eligible for an automated review.
3. Replace the PR's lifecycle label with `hermes:in-review` before inspecting
   it. This does not select or block work on any other PR.
4. Ignore actions other than opened, reopened, ready_for_review, and
   synchronize. Ignore a head SHA that already has a reviewer marker.

## Acknowledge work

After all eligibility checks pass, add an 👀 (`eyes`) reaction to the PR's
opening post before reviewing. Use the repository and PR number fetched
through GitHub:

```sh
gh api --method POST repos/OWNER/REPO/issues/NUMBER/reactions --raw-field content=eyes
```

The issue reactions endpoint also covers PR opening posts. An existing
reaction from the authenticated account counts as success. Remove that
account's previous 👍 (`+1`) and 👎 (`-1`) reactions before reviewing the new
head SHA. Skipped or ineligible events receive no reaction. Report reaction
failures and continue the review.

To remove a reaction, identify the authenticated account with `gh api user`,
list all opening-post reactions with
`gh api --paginate repos/OWNER/REPO/issues/NUMBER/reactions`, and delete only
matching reactions whose `user.id` equals that account's ID:

```sh
gh api --method DELETE repos/OWNER/REPO/issues/NUMBER/reactions/REACTION_ID
```

Preserve other users' reactions. Verify each completed reaction transition
by fetching the opening-post reactions again.

## Review

1. Derive requirements from the linked issue's acceptance criteria and
   exclusions when present, plus consistent local repository conventions.
2. Compare requirements against the full current diff and tests. Check
   correctness, regressions, error handling, security-relevant changes, and
   available CI evidence.
3. Read existing threads. Do not repeat addressed or duplicate findings.
4. Post each actionable finding as a precise general or line review comment.
   Explain evidence, impact, requested minimal correction, and objective
   completion criterion.
5. Do not alter code, branches, PR settings, merge state, release state, or
   deployment state.

## Complete the round

1. Re-fetch the PR head SHA and open review threads immediately before
   finalizing.
2. Submit one GitHub pull request review with event `COMMENT` and
   `commit_id` set to that exact SHA. Put one marker in its general review
   comment. A submitted review triggers the `pull_request_review` feedback
   webhook; an issue comment created by `gh pr comment` does not.
   - `<!-- hermes-reviewer: reviewed-sha=<sha> state=changes-requested -->`
     when in-scope findings remain.
   - `<!-- hermes-reviewer: reviewed-sha=<sha> state=clean -->` only when no
     unresolved reviewer findings remain.
3. Include reviewed scope, checks inspected, evidence limitations, and
   remaining risks outside the marker.
4. Keep `hermes:in-review` when corrections remain. For a PR whose body
   contains `<!-- hermes-origin: gw-developer -->`, add `hermes:developer`
   after posting the findings. Adding the label triggers the developer
   handoff webhook. Retain an existing `hermes:developer` label on an
   explicitly delegated PR; the submitted review triggers feedback handling
   even when that label is already present. Verify `hermes:in-review` and
   `hermes:developer` are present and `hermes:needs-human` is absent.
   Only for a human-created PR without `hermes:developer`, also add
   `hermes:needs-human` and end the general review comment with this hint:
   `You can address this feedback yourself. To delegate it, apply
   \`hermes:developer\` to this PR.`
   For every `state=clean` result, remove `hermes:in-review` and set
   `hermes:needs-human`, regardless of PR origin or role label. A
   developer-origin or `hermes:developer` PR's clean marker also wakes
   `gw-developer` to complete the human handoff. Re-fetch the PR labels and
   verify `hermes:needs-human` is present and `hermes:in-review` is absent.
5. After posting the marker and completing the lifecycle handoff, re-fetch
   the PR head SHA. If it still matches the reviewed SHA, replace the
   authenticated account's 👀 reaction on the PR's opening post with 👍
   (`+1`) for `state=clean` or 👎 (`-1`) for `state=changes-requested`:

   ```sh
   gh api --method POST repos/OWNER/REPO/issues/NUMBER/reactions --raw-field content=+1
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
