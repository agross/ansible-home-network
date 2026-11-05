# Intended GitHub workflow

1. A human labels an existing issue `ready-for-agent`. The developer verifies
   the issue and its current designation, implements the requested work, runs
   relevant checks, and opens a pull request linked to the issue.
2. The reviewer sets `in-review` on the pull request and its identifiable
   original issue, reviews the current head, and submits a GitHub pull request
   review comment containing a result for that head. The developer does not
   set `in-review` when opening the PR.
3. If the review is clean, the reviewer removes `in-review` from the pull
   request and its identifiable original issue, and sets `needs-human` on the
   PR. The developer assigns the PR to the original issue author for human
   follow-up.
4. If the review comment has findings, hand the pull request back to the
   developer. The developer addresses the findings, pushes an updated head,
   and the reviewer reviews it again. Repeat until the result is clean.

The GitHub Apps must be installed on the repository, and their webhooks must
reach the developer and reviewer routes. The developer receives issue-label,
issue-comment, and submitted-review events; the reviewer receives pull request events. Each route
accepts only configured installation IDs.

When an issue still has `ready-for-agent`, a new comment by a human with
repository write or admin access can resume work without removing and readding
the label. The developer re-fetches the issue and comment, checks the comment's
author against the event sender, and verifies the author's current repository
permission before acting. Bot comments and PR conversation comments do not
trigger this issue-comment path. Enable the GitHub App's Issue comment event
subscription for delivery.

## Verification

The configured routes and profile instructions cover issue selection, PR
creation, review submission, findings handoff, and clean handoff. New
pull requests carry a marker identifying the original issue; the developer
fetches its author, assigns that user to the PR, and verifies the assignment.
If the original issue or author cannot be identified or assigned, the PR stays
`needs-human` and the incomplete handoff is reported.

Reviewer findings are handed back by the submitted review event. The reviewer
does not add `ready-for-agent` to developer-origin PRs, avoiding a second
handoff event. Live webhook delivery and agent behavior remain unverified.

## Handing an existing PR to the developer

1. Put the requested corrections in a GitHub pull request review or review
   comments, then apply `ready-for-agent` to the PR. The label is the explicit
   developer handoff for a PR without a developer-origin marker. If it is
   already present, applying it again does not create a new label event; submit
   a PR review to trigger the feedback route, or remove and reapply the label.
2. The developer re-fetches the PR, confirms the designation remains present,
   reads submitted reviews, issue comments, and open review threads. The
   reviewer owns the `in-review` transition. Concrete human review comments can define the repair
   scope. The developer stops on genuine ambiguity or conflicting instructions.
3. The developer checks out the current PR head, applies the corrections, runs
   relevant checks, and pushes to the existing head branch without force-pushing
   or replacing the PR. The GitHub App needs write access to that head branch;
   fork or branch restrictions can prevent the push.
4. A new head triggers review. A clean reviewer result leads to `needs-human`;
   the developer attempts to assign the original issue author if the original
   issue can be identified. If no linked issue exists or assignment fails, the
   handoff remains incomplete and is reported.

A submitted review produces a `pull_request_review` event; an ordinary PR
conversation comment alone does not match the developer route. Apply the label
after posting such a comment to initiate the handoff. Current instructions
explicitly start a repair round for a `changes-requested` marker or unresolved
review comment, but do not clearly guarantee a round for findings expressed
only in the body of a human-submitted general review. Live delivery, execution,
and this general-review case have not been verified.
