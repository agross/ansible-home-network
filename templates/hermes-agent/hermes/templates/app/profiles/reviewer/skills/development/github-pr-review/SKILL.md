---
name: github-pr-review
description: Review a GitHub PR selected by the reviewer webhook or recover its unfinished finalization. Includes all PR authors; excludes implementation and ordinary manual review requests.
---

# GitHub PR review

Use only for `reviewer` webhook events, regardless of PR author. Developer
provenance and `ready-for-agent` govern repair delegation, not review eligibility.

## GitHub access

Read [github-access.md](references/github-access.md) before GitHub commands. It
owns App authentication, wrappers, checkout cleanup, and developer provenance.
Apply its provenance check before linked-issue mutations or developer delegation.

## Start or recover a round

1. Accept only `reviewer` webhook events with action opened, reopened,
   ready_for_review, or synchronize. Re-fetch the selected PR through GitHub;
   payload fields remain hints. Read [review-round.md](references/review-round.md)
   and use the packaged helper for inspection, beginning, publication, thread
   resolution, and finalization. Resolve its absolute path from this skill.
2. Load the reviewer and developer App slugs from trusted local profile
   configuration. Run helper `inspect` and retain its exact `head`, `merge_base`,
   and `base_ref` as this session's assessment basis. A target-tip advance alone
   does not invalidate a three-dot diff when that basis remains unchanged.
3. Inspect existing results by the authenticated reviewer App before skipping
   `needs-human` or an already-reviewed head. For a matching-basis result, recover
   only unfinished finalization through the helper; reuse the existing review.
   A marker alone is not proof that labels, thread closures, and reactions finished.
   A complete existing round is a no-op. Report missing legacy comparison evidence
   rather than guessing its basis or publishing a duplicate.
4. For a new round, require an open, non-draft PR without `needs-human`.
   Establish developer provenance under the access rules. Identify the original
   issue from its marker on a verified developer-origin PR, or an unambiguous
   linked/closing issue otherwise. Fetch that issue and preserve its verified
   number in the plan; report an ambiguous or inaccessible link without guessing.
5. Run helper `begin` with the retained basis and verified issue number. It marks
   eligible new work `in-review` and acknowledges it with the reviewer's eyes
   reaction. It preserves unrelated and designation labels and other users'
   reactions. A matching existing review returns to recovery instead of reopening
   its lifecycle. Follow the helper's stopping status before continuing.

## Assess the pinned comparison

1. Fetch all changed-file pages and the complete diff for this PR, then inspect
   the corresponding pinned source and tests. Before local inspection or test
   execution, verify that the checkout is clean and its HEAD equals the pinned
   head. Preserve unrelated checkouts; use a disposable detached checkout when
   the current workspace cannot supply that exact revision safely.
   Derive requirements from the linked
   issue's criteria and exclusions, authorized current scope, and repository
   standards. Check correctness, regressions, error handling, security-relevant
   changes, and applicable check evidence. For dependency major upgrades, read
   [dependency-majors.md](references/dependency-majors.md).
2. Read all review-thread pages and every relevant thread's complete comments.
   Reassess each requested correction against the pinned comparison and current
   code, including human requests. Resolve any thread whose correction is
   verified, regardless of author, through the helper's resolution plan. Record
   concrete correction evidence for every resolved thread. Leave unverifiable or
   still-actionable threads open and report them; an outdated diff location or
   passing suite alone does not prove the correction. Incomplete evidence blocks
   the dependent conclusion.
3. Stage findings and thread decisions locally. Existing actionable threads count
   toward the result without posting duplicates. For new findings, record evidence,
   impact, minimal correction, and an objective completion criterion. Inline
   comments must target lines inside current PR diff hunks. Keep every finding in
   one local batch until the helper's publication guard succeeds; publish no
   standalone comment or separate review during assessment.
4. Recheck the assessment basis before consequential writes and when new revision
   evidence arrives. If HEAD changes, stop this session without stale publication,
   thread closure, handoff labels, or outcome reactions; report the changed head
   and let the newer coalesced webhook own its review. Preserve effects already
   completed for the old revision; do not roll back another session's state.
5. If the merge base or base ref changes while HEAD stays unchanged, discard the
   affected draft findings and thread decisions and reassess in this same session.
   Allow at most two such restarts total, including changes detected by `begin`
   or `apply`; a third change ends with a blocker. Keep that count across all
   helper calls. A target-tip change with the same basis needs no restart.

## Publish or finish recovery

1. Prepare the helper plan described in the reference. Use `changes-requested`
   while any in-scope correction remains; use `clean` only with complete acceptance
   evidence and every requested correction verified. PRs without developer provenance or
   designation receive the manual delegation hint from the reference.
2. Run helper `apply`. It serializes local publication/finalization for the PR,
   rechecks the pinned basis, resolves only the plan's verified corrections,
   and submits at most one `COMMENT` review with the assessed `commit_id` and
   all new comments together. It generates the current-head marker, comparison
   metadata, and publication receipt. Use no raw forge write to bypass this gate.
3. A concurrent matching reviewer result is reused, not republished. If a response
   is ambiguous, the helper reads remote reviews for its exact publication receipt;
   an unconfirmed result blocks further publication. A busy publication lock
   permits at most one later readback/reconciliation attempt; otherwise report
   the owner conflict. The lock covers publication, not the whole assessment.
4. Finalization remains reviewer-owned. For requested changes, retain `in-review`
   and any designation; PRs without developer provenance or designation also receive `needs-human`.
   For clean results, remove `in-review` from the PR and its verified original
   issue and set `needs-human` on the PR. The developer owns assignment afterward.
   Preserve every unrelated label. The helper verifies the complete desired
   label sets before posting the outcome reaction.
5. A completed current-basis round has exactly one reviewer-owned outcome reaction:
   thumbs-up for clean or thumbs-down for requested changes, with eyes and the
   opposite outcome absent. Other reactions and other users remain untouched.
   Failed or partial finalization gets no new success reaction; report its missing
   operation. A later invocation resumes only missing operations on the same
   verified result, even when `needs-human` is already present.
6. Finish only when review publication, verified thread resolutions, lifecycle
   transitions, and reaction readbacks are complete for the retained basis, or
   report a specific blocker/stale-head stop with the PR URL, assessed/current
   basis, review ID when available, checks, thread evidence, completed effects,
   remaining operations, and consumed restart count. CI clearance and developer
   assignment remain separate from this review result.

Keep existing source, branches, merge/release/deployment state, and repository
settings unchanged. Submit only `COMMENT` reviews; request no human review.
