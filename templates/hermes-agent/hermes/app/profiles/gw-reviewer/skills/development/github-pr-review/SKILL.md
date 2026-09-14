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

A work item normally has one Hermes lifecycle label: `hermes:next`,
`hermes:implementing`, `hermes:in-review`, or `hermes:needs-human`. A
human-created PR with unresolved reviewer findings carries both
`hermes:in-review` and `hermes:needs-human`. Remove legacy
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
2. Post one general comment containing one marker for that exact SHA:
   - `<!-- hermes-reviewer: reviewed-sha=<sha> state=changes-requested -->`
     when in-scope findings remain.
   - `<!-- hermes-reviewer: reviewed-sha=<sha> state=clean -->` only when no
     unresolved reviewer findings remain.
3. Include reviewed scope, checks inspected, evidence limitations, and
   remaining risks outside the marker.
4. Keep `hermes:in-review` when corrections remain. If the PR body lacks
   `<!-- hermes-origin: gw-developer -->`, also add `hermes:needs-human` so
   the human author is notified. A developer-created PR's clean marker wakes
   `gw-developer` for handoff; otherwise replace the PR label with
   `hermes:needs-human`.
5. Never submit an approval or request human review.
