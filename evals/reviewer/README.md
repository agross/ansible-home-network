# Reviewer operation evals

Sevro **1.1.2** owns isolated host execution, trials, grading, and retained
artifacts. The exact npm dependency and lockfile pin that release. Python's
`run.py` selects scenarios and invokes the local Sevro executable.

## Install and run

Use Node.js 24.13.0 or newer, Python 3, Git, an authenticated Codex CLI with
file-based authentication, and Sevro's native isolation prerequisites
(macOS `sandbox-exec` or supported Linux `bubblewrap`).

```sh
npm --prefix evals/reviewer ci --ignore-scripts
python3 -m unittest discover --start-directory evals/reviewer --pattern 'test_*.py' --verbose
python3 evals/reviewer/run.py --dry --output-dir /tmp/reviewer-sevro-preparation-001
python3 evals/reviewer/run.py --output-dir /tmp/reviewer-sevro-run-001
```

Dry preparation returns `not_assessed`; it is not a behavior pass. Native trials
consume model quota. The default surrogate is Codex `gpt-6.1-sol` with `medium`
effort, independent of the live Hermes reviewer model. Override `--model`,
`--effort`, or `--codex-auth-file` when needed. Credentials remain in Sevro's
private host home, outside participant fixtures.

Repeat `--case NAME` to select cases; use `--trials 3` for fresh repetitions.
Every selected trial must pass. Always use a fresh output directory. Its
`index.json` links case results and evidence; failures remain nonzero exits.
Finish editing evaluator inputs before execution: Sevro invalidates trials
whose source closure changes during execution.

## Operations and assertions

Each case mounts the current reviewer skill, bundled Python helper, references,
and persona in a disposable Git repository. Local history contains an API
change and regression tests. Fake `gh-app` and `hermes-github-app` executables
serve finite synthetic GitHub state. Fake `git-app` rejects transport: reviewer
fixtures already contain the exact checkout and history. No real GitHub write
occurs. Unsupported commands fail explicitly.

The reviewer executes the packaged helper. Evaluator-owned assertions inspect
ordered operations, published commit IDs, full comparison markers, batch
findings, resolved thread IDs, labels, reactions, and preserved source history.
Expected outcomes stay outside participant-visible fixture files. Synthetic
races change provider state after diff reads or publication. A two-turn case
checks recovery by a later webhook after label finalization fails.

| Case | Required behavior |
| --- | --- |
| `renovate_pr_without_designation_is_reviewed` | Review a clean Renovate PR without developer provenance, a linked issue, or designation. |
| `renovate_findings_publish_without_developer_delegation` | Publish Renovate findings and hand off to a human without granting developer delegation. |
| `configured_app_identity_mismatch_blocks_before_writes` | Reject mismatched authenticated/configured App slugs before mutations, even when the configured slug resolves to a real unrelated bot. |
| `head_change_stops_stale_session` | Stop stale assessment without publication. |
| `head_change_after_publication_stops_handoff` | Stop after a racing HEAD change; no stale clean handoff. |
| `target_tip_advance_keeps_same_comparison` | Continue without restart when merge base and HEAD remain stable. |
| `merge_base_change_reassesses_once` | Reassess changed comparison before publication. |
| `merge_base_churn_stops_after_two_restarts` | Stop after initial assessment plus two restarts, without publication. |
| `verified_app_and_human_threads_are_resolved` | Verify and resolve repaired threads from either author. |
| `unfixed_human_thread_stays_actionable` | Retain unresolved correction and publish changes requested. |
| `existing_marker_recovers_missing_finalization` | Reuse existing assessment and finish missing workflow effects. |
| `completed_marker_is_idempotent` | Completed assessment causes no duplicate mutation. |
| `concurrent_result_prevents_duplicate_comments` | Another completed result prevents duplicate findings or finalization. |
| `new_findings_publish_one_pinned_batch` | Publish concrete findings in one COMMENT review on assessed commit. |
| `accepted_but_ambiguous_publication_is_reconciled` | Read back accepted receipt without retrying publication. |
| `published_marker_recovers_after_label_failure` | Later webhook completes finalization without reposting review. |

Local tests also exercise missing correction evidence, comment pagination,
publication locking, unconfirmed publication, legacy comparison markers, and
counterfeit markers by another actor. These fixtures check behavior, not a
security boundary against deliberate evidence forgery.

These are **Codex surrogate** evals. They do not establish live Hermes tool
compatibility, reviewer-model reliability, GitHub App authentication, or webhook
coalescing/delivery. One trial per scenario is a regression check. Real Hermes
integration remains separate validation.
