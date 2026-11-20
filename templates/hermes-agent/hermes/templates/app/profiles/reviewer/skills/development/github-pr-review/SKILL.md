---
user_locked: true
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
   linked/closing issue otherwise. Treat a dependency-dashboard backlink as
   operational tracking, not the original issue, unless it explicitly closes or
   supplies acceptance criteria for the PR. Fetch a verified original issue and
   preserve its number in the plan; report an ambiguous or inaccessible link
   without guessing. When no original issue is identifiable, set `issue_number`
   to JSON `null` rather than inventing a PR or dashboard issue number.
5. Run helper `begin` with the retained basis and verified issue number (or the
   explicit `null` value). It marks
   eligible new work `in-review` and acknowledges it with the reviewer's eyes
   reaction. It preserves unrelated and designation labels and other users'
   reactions. A matching existing review returns to recovery instead of reopening
   its lifecycle. Follow the helper's stopping status before continuing.

## Assess the pinned comparison

1. Fetch all changed-file pages and the complete diff for this PR, then inspect
   the corresponding pinned source and tests. Before local inspection or test
   execution, verify that the checkout is clean and its HEAD equals the pinned
   head. Preserve unrelated checkouts; use a disposable detached checkout when
   the current workspace cannot supply that exact revision safely. If no safe
   checkout is available, inspect the required pinned blobs through the
   authenticated Contents API with the exact head SHA; copy the path from the
   changed-file record rather than inferring a similarly named role file, and
   request the raw media type when reading source so base64 JSON does not obscure
   the pinned content. For a repository-wide exact-value search, a GitHub API tarball requested at
   the pinned SHA is an acceptable read-only snapshot only after hashing a
   relevant extracted file and matching it to that file's exact-head raw
   Contents response; use [pinned-snapshots.md](references/pinned-snapshots.md)
   for the authenticated tarball recipe. Do not run local tests against an
   unverified worktree or substitute an unpinned branch view.
   Derive requirements from the linked
   issue's criteria and exclusions, authorized current scope, and repository
   standards. Check correctness, regressions, error handling, security-relevant
   changes, and applicable check evidence. When a required check fails, inspect
   its failed job log before treating it as a finding; distinguish a code failure
   from an external dependency or registry outage, because check annotations may
   only report the wrapper's exit status. If GitHub Actions withholds a completed
   job's log while its workflow run is still active, refresh the run/check state
   and retrieve that failed job log again once the run completes; do not classify
   the failure from the exit annotation alone. Record an in-progress required check as
   an explicit CI limitation, not as a review finding or a reason to delay an
   otherwise complete code review; CI clearance remains a separate merge gate.
   For any version-pin update, search the pinned repository for the exact old
   value after inspecting the changed consumers; account for every remaining
   reference or identify it as intentionally out of scope, because an unmodified
   consumer can leave a partial rollout that the PR diff alone does not reveal.
   In a verified detached checkout, run the exact-value search against the
   assessed commit (for example, `git grep -n -F 'OLD_VALUE' HEAD --`) and report
   both the remaining-old-value result and the consumers of the new value; this
   binds rollout evidence to the review basis rather than the checkout's branch
   state. Delimit numeric version searches with their format syntax (for example,
   the surrounding JSON/XML quotes) instead of searching an undecorated prefix,
   because `10.0.1` also matches values such as `10.0.14`.
   Treat a different version of the same upstream as a separate consumer only
   after tracing its configuration dataflow; do not call it a missed rollout
   merely because it shares the upstream name.
   For a GitHub Action commit-SHA update, query
   `repos/OWNER/ACTION/commits/SHA` and record that the exact SHA resolves; when
   signature verification is available, record its status, but do not infer an
   action release tag from an inline comment alone. Do not use GitHub Code Search as that proof: it does not bind results to the
   assessed SHA. Search a verified detached checkout, or enumerate and read the
   exact-head blobs through the authenticated API, so a default-branch result
   cannot be mistaken for the pinned comparison.
   For container-tag updates, trace every image fed by the changed value before
   probing, and perform availability lookups for each affected image rather than
   only the image named in the diff; a shared version variable can update several
   runtime consumers. Attempt a read-only manifest lookup when credentials permit;
   use the reusable [container-manifests.md](references/container-manifests.md)
   recipe for Docker Hub tags. Record an authorization denial as an availability
   limitation, not evidence that the tag is absent. Classify the changed value by its consuming code before probing: a GitHub
   release variable used by a binary installer is not a container-tag update,
   even when the role also has an independently pinned image; do not make an
   unrelated image-manifest lookup or treat one as evidence against the PR.
   For dependency major upgrades, read
   [dependency-majors.md](references/dependency-majors.md). For a package, collection, or role version-pin update, use its authoritative
   registry's read-only published-version endpoint when available to verify that
   the exact requested version can resolve.
   For Ansible Galaxy roles, query
   `https://galaxy.ansible.com/api/v1/roles/?namespace=NAMESPACE&name=ROLE` and
   confirm the requested value in `summary_fields.versions`. Then compare any
   published runtime or interpreter minimum against the pinned consumer's target
   platforms and interpreter selection; a resolvable package can still be
   undeployable on supported targets. Record registry resolution as availability
   evidence only, because it does not validate upstream runtime behavior. For a GitHub-release binary pin,
   inspect the pinned consumer first, including any local variable handoff to a
   pinned external role or collection, then query `repos/OWNER/REPO/releases/tags/TAG`
   with `--jq` for `tag_name` and the asset names needed by that consumer; avoid
   dumping the full release payload because its asset metadata can obscure the
   actual compatibility evidence. For .NET SDK pins in `global.json`,
   verify the exact SDK in Microsoft's release-metadata `releases.json`.
   When a dependency release changes native artifact names or packaging, search the pinned repository—including
   Dockerfiles, CI, and deployment scripts—for the old basenames before concluding
   that no migration is required; those references can otherwise fail only after
   deployment.
2. Read all review-thread pages and every relevant thread's complete comments.
   Reassess each requested correction against the pinned comparison and current
   code, including human requests. Resolve any thread whose correction is
   verified, regardless of author, through the helper's resolution plan. Record
   concrete correction evidence for every resolved thread. Leave unverifiable or
   still-actionable threads open and report them; an outdated diff location or
   passing suite alone does not prove the correction. Incomplete evidence blocks
   the dependent conclusion.

   For new or existing NuGet lock-file findings, validate the affected projects
   at the pinned head with `dotnet restore --locked-mode --no-http-cache`, using
   the repository's pinned SDK, configured sources, and a fresh package cache.
   A passing locked restore is sufficient. Report a hash mismatch only when
   NuGet reports NU1403. If restore cannot run, report the validation limitation.
   Do not compute or compare hashes separately, or edit lock-file hashes by hand.

3. Stage findings and thread decisions locally. Existing actionable threads count
   toward the result without posting duplicates. For new findings, record evidence,
   impact, minimal correction, and an objective completion criterion. Inline
   comments must target lines inside current PR diff hunks. Keep every finding in
   one local batch until the helper's publication guard succeeds; publish no
   standalone comment or separate review during assessment.
4. Refresh the PR's check rollup immediately before drafting the outcome: a check
   that was in progress at inspection may have completed while source assessment
   ran. Inspect check runs and legacy commit statuses separately; a combined-status
   `pending` result with no legacy statuses does not override terminal check-run
   conclusions. Populate the final plan body only after this refresh, or revise it
   to match the refreshed result; otherwise the published evidence can describe
   stale CI state. Preserve the check state observed for the published plan; if a
   check completes afterward, report that later observation separately rather than
   implying the review had relied on it. When refreshing checks and re-inspecting the basis in parallel,
   treat the check response as provisional until the basis readback confirms the
   same head, merge base, and base ref; discard it on drift so stale CI evidence
   cannot enter the plan or final report. Use final check-run results as evidence
   when available; retain an explicit CI limitation only when a relevant check run
   remains in progress. Recheck the assessment basis and PR state before
   consequential writes and when new revision evidence arrives. If the PR has
   closed or become draft after `begin`, stop before drafting or applying the
   plan and perform readback only; report any provisional reviewer-owned
   `in-review` label or eyes reaction, but do not mutate a closed PR. If HEAD
   changes, stop this session without stale publication, thread closure, handoff
   labels, or outcome reactions; report the changed head and let the newer
   coalesced webhook own its review. Preserve effects already completed for the
   old revision; do not roll back another session's state.
5. If the merge base or base ref changes while HEAD stays unchanged, discard the
   affected draft findings and thread decisions and reassess in this same session.
   Allow at most two such restarts total, including changes detected by `begin`
   or `apply`; a third change ends with a blocker. Keep that count across all
   helper calls. A target-tip change with the same basis needs no restart.

## Publish or finish recovery

1. Prepare the helper plan described in the reference. Use `changes-requested`
   while any in-scope correction remains; use `clean` only with complete acceptance
   evidence and every requested correction verified. When no original issue is
   identifiable after checking closing references, say so in the review evidence
   and distinguish any dependency-dashboard backlink as operational tracking;
   otherwise the acceptance-evidence boundary is unclear. For a `changes-requested`
   outcome without developer provenance or a designation label, append the manual
   delegation hint. For a clean outcome, rely on finalization's `needs-human`
   disposition; do not append a repair-delegation hint when no repair is needed.
2. Run helper `apply`. It serializes local publication/finalization for the PR,
   rechecks the pinned basis, resolves only the plan's verified corrections,
   and submits at most one `COMMENT` review with the assessed `commit_id` and
   all new comments together. It generates the current-head marker, comparison
   metadata, and publication receipt. Use no raw forge write to bypass this gate.
   If `apply` reports the PR is closed or draft, do only readback to confirm its
   state, merge status, reviews, labels, and reviewer-owned reactions; do not
   bypass the gate or mutate lifecycle state on the closed PR. A close detected
   after publication can still leave a valid submitted review: enumerate the
   exact-basis reviewer review and validate its receipt before reporting whether
   an outcome was published, then list every uncompleted clean-result label and
   reaction transition. If `apply` returns a GraphQL or
   authorization failure, do not infer which mutation completed or bypass the
   helper: read back the current-basis reviews, labels, reactions, and thread
   states, then report the exact blocker and every remaining finalization
   operation. Report that no outcome was published unless readback verifies its
   review receipt, and name any reviewer-owned lifecycle effects that remain.
3. A concurrent matching reviewer result is reused, not republished. If `apply`
   reports publication is unconfirmed or otherwise ambiguous, immediately perform
   one remote readback of the exact-basis reviewer review, PR labels, reviewer
   reactions, and thread states; verify the generated receipt before treating a
   review as published. An unconfirmed result blocks further publication and raw
   forge retries. A busy publication lock permits at most one later
   readback/reconciliation attempt; otherwise report the owner conflict. The lock
   covers publication, not the whole assessment.
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
6. After helper `complete` or `already_complete`, independently read back the
submitted review by ID, the PR's labels through its issue endpoint, and the
reviewer App's issue reactions. Derive the reviewer bot's numeric ID from the
read-back review author (or the authenticated identity), then filter reactions
by that ID; never guess an App bot ID from configuration or a prior response.
Confirm the review is `COMMENTED` at the pinned commit and contains the generated
marker, basis metadata, and receipt; confirm only the expected reviewer outcome
reaction remains. Do not claim completion from the helper status alone, because
the final report must be backed by remote label, review, and reaction evidence.
7. Finish only when review publication, verified thread resolutions, lifecycle
transitions, and reaction readbacks are complete for the retained basis, or
report a specific blocker/stale-head stop with the PR URL, assessed/current
basis, review ID when available, checks, thread evidence, completed effects,
remaining operations, and consumed restart count. CI clearance and developer
assignment remain separate from this review result.

Keep existing source, branches, merge/release/deployment state, and repository
settings unchanged. Submit only `COMMENT` reviews; request no human review.
