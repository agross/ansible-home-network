# Developer skill operation evals

Sevro **1.1.2** owns host isolation, trials, grading, and retained evidence. The
exact npm dependency and package lock pin that release. `run.py` only selects
scenarios and invokes the local Sevro executable; it no longer launches Codex
or grades action plans itself. The eight original scenario IDs, input evidence,
and permitted outcomes remain in `cases.json`.

## Install and check fixtures

Use Node.js 24.13.0 or newer, Python 3, Git, and the native isolation prerequisites
for Sevro's Codex host (macOS `sandbox-exec` or supported Linux `bubblewrap`).
Install from the lockfile and run the local fixture/grader tests:

```sh
npm --prefix evals/developer ci --ignore-scripts
python3 -m unittest discover --start-directory evals/developer --pattern 'test_*.py' --verbose
```

Prepare all eight cases without model calls:

```sh
python3 evals/developer/run.py --dry --output-dir /tmp/developer-sevro-preparation-001
```

Successful dry preparation is `not_assessed`, not a behavior pass.

## Execute the scenarios

An authenticated Codex CLI with file-based authentication is required. Sevro
uses a private host home; credentials are not copied into the candidate fixture.
The default model/effort is `gpt-6.1-sol`/`medium`, matching the developer profile.
Override `--model`, `--effort`, or `--codex-auth-file` explicitly when needed.
Each native trial consumes the account's model quota.

```sh
python3 evals/developer/run.py --output-dir /tmp/developer-sevro-run-001
```

Use `--case NAME` repeatedly to select scenarios and `--trials 3` for repeated
fresh trials. Threshold is `1`: every selected trial must pass. Use a fresh
output directory each time. The top-level `index.json` links each case's Sevro
`result.json` and retained evidence. Nonzero exit codes remain failures or
unavailable execution; no trial is silently skipped. Finish editing evaluator
inputs before execution: Sevro refuses assessments when its source inputs change
while a trial is running.

## What executes and what is checked

The extension prepares a disposable Git repository with a small API function,
existing tests, synthetic event data, and local bare repositories for the base
and PR head. It mounts the exact current developer skill and its references
through Sevro's explicit repository-skill invocation. Production profile paths
are mapped to `.fixture/profiles` solely inside this test repository.

Fixture executables precede host tools on `PATH`:

- `gh-app` serves synthetic PRs, reviews, author permissions, bot identities,
  reactions, labels, assignments, and CI state. Mutations update the fake forge
  and append ordered operation records.
- `git-app` resolves synthetic HTTPS repository URLs to disposable local Git
  remotes, then executes real Git fetch, clone, push, and ref-query commands.
  Wrong installation/repository pairings, force pushes, unknown destinations,
  and unsupported operations fail explicitly. No real GitHub request occurs.
- `hermes-github-app status` returns the fixture App identity and permissions.
  Git hooks record commits and checkout changes in the same operation journal.

Evaluator-owned shell assertions check the journal, actual labels and reactions,
local history, published remote refs, and the published API behavior. They require
identity/permission reads before mutations, remove `needs-human` before repair,
retain designation, preserve reviewer label ownership, publish exactly once to
the intended head repository/branch, and withhold assignment while CI is pending.
Sevro's Git HEAD grader independently checks fixture history. Its output-schema
grader preserves the original outcome and `ci_clearance: false` assertions.
Expected assertions stay outside participant-visible files.

The small fake forge implements the commands required by these cases, not all
of GitHub. Unsupported operations invalidate a trial rather than returning a
success-shaped placeholder. Unit tests exercise both successful operations and
counterexamples such as unauthorized writes, wrong-fork pushes, label takeover,
and stale-CI assignment. Fake tools and journals are test fixtures, not a hardened
security boundary against a candidate deliberately forging its own evidence.

## Scope and scenarios

These are executed **Codex surrogate** evaluations of a Hermes skill. They do
not prove Hermes tool compatibility, real GitHub App authentication, or live
webhook delivery. One trial per case is a regression check, not a reliability
claim. Real Hermes integration remains a separate validation step.

| Case | Required behavior |
| --- | --- |
| `unauthorized_review_leaves_state_untouched` | Unauthorized triggering review causes no mutation, even with older authorized feedback. |
| `copied_origin_marker_requires_designation` | A human-created PR with a copied marker receives no developer work without designation. |
| `maintainer_general_review_repairs_existing_fork` | A concrete general review triggers scoped repair; push goes to the fork, retaining designation and reviewer ownership. |
| `developer_origin_repair_resumes_after_human_handoff` | Authorized repair removes `needs-human` without requiring designation and leaves the new head review-eligible. |
| `designated_repair_resumes_after_human_handoff` | Designated human PR resumes repair, clears `needs-human`, and retains designation. |
| `informational_review_leaves_handoff_untouched` | Informational review changes no state. |
| `already_satisfied_request_creates_no_duplicate_repair` | Already-implemented feedback produces no duplicate edit or push. |
| `stale_ci_does_not_complete_human_handoff` | Earlier passing CI does not authorize assignment while current-head CI is pending. |

The pending-CI case permits a blocked route or an incomplete clean-handoff route;
both must withhold CI clearance, assignment, and publication. Classification
wording alone is not evidence of completed handoff.

Sevro contracts: [installation](https://github.com/BjRo/sevro/blob/main/docs/installing.md),
[extensions](https://github.com/BjRo/sevro/blob/main/docs/extension-protocol-v1.md),
[built-in graders](https://github.com/BjRo/sevro/blob/main/docs/builtin-graders-v1.md).
